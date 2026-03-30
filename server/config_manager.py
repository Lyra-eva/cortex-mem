"""
配置管理器 - 从 LanceDB 共享配置表加载和管理配置

功能：
- 启动时从 LanceDB 加载配置
- 支持热更新（5 分钟自动重载）
- 版本管理
- 支持 per-agent 配置覆盖
"""

import json
import logging
import time
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 默认配置（LanceDB 不可用时使用）
DEFAULT_CONFIGS = {
    'feel:emotion_keywords': {
        'joy': {'keywords': ['开心', '快乐', '兴奋', '爽', '棒', '高兴', '愉快'], 'weight': 1.0},
        'sadness': {'keywords': ['伤心', '难过', '郁闷', '烦', '累', '悲伤', '沮丧'], 'weight': 1.0},
        'anger': {'keywords': ['愤怒', '气', '恼火', '不爽', '生气', '怒'], 'weight': 1.0},
        'fear': {'keywords': ['害怕', '恐惧', '担心', '紧张', '怕'], 'weight': 1.0},
        'disgust': {'keywords': ['讨厌', '恶心', '烦人', '厌恶'], 'weight': 1.0},
        'surprise': {'keywords': ['惊讶', '意外', '没想到', '吃惊'], 'weight': 1.0}
    },
    'perceive:priority_keywords': {
        'urgent': ['紧急', '立即', '马上', '急', 'priority', 'urgent'],
        'important': ['重要', '关键', '优先', '重点'],
        'normal': []
    },
    'perceive:categories': {
        'schedule': ['会议', '日程', '安排', '预约'],
        'communication': ['邮件', '消息', '通知', '电话'],
        'task': ['任务', '工作', '项目', '待办'],
        'urgent': ['紧急', '立即', '马上', '急'],
        'system': ['系统', '更新', '警告', '错误'],
        'general': []
    },
    'global:cache_ttl': {
        'think': 3600,      # 1h → 1h (不变)
        'learn': 7200,      # 2h → 2h (增加)
        'feel': 600,        # 5m → 10m (增加)
        'execute': 0,
        'perceive': 1800,   # 10m → 30m (增加)
        'monitor': 0,
        'search': 7200,     # 新增：搜索缓存 2h
        'memory_inject': 3600  # 新增：记忆注入缓存 1h
    },
    'think:thresholds': {
        'min_confidence': 0.7,
        'default_confidence': 0.8
    },
    'execute:steps_template': {
        'default': ['分析任务', '制定计划', '执行', '验证'],
        'complex': ['理解需求', '分解任务', '资源分配', '执行', '测试', '交付'],
        'simple': ['执行', '验证']
    },
    'learn:learning_strategy': {
        'auto_save': True,
        'extract_keywords': True,
        'generate_summary': True,
        'link_related': True,
        'max_keywords': 10,
        'summary_max_length': 200
    },
    'learn:domain_keywords': []
}


class ConfigManager:
    """配置管理器 - v5.5 支持 Redis 常驻缓存 + 自动进化"""
    
    def __init__(self, lancedb_path: str = None, redis_client = None):
        self.configs: Dict[str, Any] = {}
        self.last_load: float = 0
        self.reload_interval: int = 300  # 5 分钟
        self.lancedb_path = lancedb_path or '/Users/lx/.openclaw/evolution/data/lancedb/_shared'
        self.db = None
        self.config_table = None
        self._initialized = False
        self.redis_client = redis_client
        self.redis_cache_ttl = 7200  # Redis 缓存 2h (增加)
        self.search_cache_ttl = 7200  # 搜索缓存 2h
        self.memory_cache_ttl = 3600  # 记忆缓存 1h
    
    async def initialize(self, redis_client = None):
        """初始化配置管理器"""
        if self._initialized:
            return
        
        self.redis_client = redis_client
        
        # 1. 尝试从 Redis 缓存加载（最快）
        if self.redis_client:
            try:
                cached = await self._load_from_redis()
                if cached:
                    logger.info(f"ConfigManager loaded {len(cached)} configs from Redis cache")
                    self._initialized = True
                    return
            except Exception as e:
                logger.debug(f"Redis cache load failed: {e}")
        
        # 2. 加载默认配置
        self.configs = DEFAULT_CONFIGS.copy()
        
        # 3. 尝试从 LanceDB 加载
        try:
            await self._load_from_lancedb()
            logger.info(f"ConfigManager initialized with {len(self.configs)} configs from LanceDB")
            
            # 写入 Redis 缓存
            if self.redis_client:
                await self._save_to_redis()
        except Exception as e:
            logger.warning(f"LanceDB config load failed: {e}, using defaults")
        
        self.last_load = time.time()
        self._initialized = True
    
    async def _load_from_redis(self) -> Dict[str, Any]:
        """从 Redis 缓存加载配置"""
        if not self.redis_client:
            return {}
        
        try:
            cached = self.redis_client.get('config:all')
            if cached:
                self.configs = json.loads(cached)
                return self.configs
        except Exception as e:
            logger.debug(f"Redis cache read failed: {e}")
        
        return {}
    
    async def _save_to_redis(self):
        """保存配置到 Redis 缓存"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex('config:all', self.redis_cache_ttl, json.dumps(self.configs, ensure_ascii=False))
            logger.debug(f"Config saved to Redis cache (TTL: {self.redis_cache_ttl}s)")
        except Exception as e:
            logger.debug(f"Redis cache write failed: {e}")
    
    async def _load_from_lancedb(self):
        """从 LanceDB 加载配置"""
        import lancedb
        
        try:
            db = lancedb.connect(self.lancedb_path)
            
            # 尝试打开配置表
            try:
                table = db.open_table('evolution_config')
                self.config_table = table
                
                # 读取所有配置
                all_configs = table.to_arrow().to_pylist()
                
                for config in all_configs:
                    key = f"{config['module']}:{config['config_key']}"
                    self.configs[key] = config['config_value']
                    logger.debug(f"Loaded config: {key}")
                
                logger.info(f"Loaded {len(all_configs)} configs from LanceDB")
                
            except Exception as e:
                # 表不存在，创建
                logger.info(f"Config table not exists, creating: {e}")
                await self._create_config_table(db)
                
        except Exception as e:
            logger.error(f"LanceDB connection failed: {e}")
            raise
    
    async def _create_config_table(self, db):
        """创建配置表"""
        import lancedb
        
        # 准备默认数据
        schema_data = []
        for key, value in DEFAULT_CONFIGS.items():
            parts = key.split(':', 1)
            module = parts[0]
            config_key = parts[1] if len(parts) > 1 else 'default'
            
            schema_data.append({
                'id': f'config_{module}_{config_key}',
                'module': module,
                'config_key': config_key,
                'config_value': value,
                'version': '1.0.0',
                'updated_at': datetime.now().isoformat(),
                'updated_by': 'system',
                'metadata': json.dumps({'source': 'default', 'description': f'{module} module config'})
            })
        
        # 创建表
        table = db.create_table('evolution_config', schema_data)
        self.config_table = table
        logger.info(f"Created evolution_config table with {len(schema_data)} default configs")
    
    async def get(self, module: str, key: str, agent_id: str = None) -> Any:
        """
        获取配置
        
        Args:
            module: 模块名 (think/learn/feel/execute/perceive/monitor/global)
            key: 配置键
            agent_id: 可选的 agent ID（用于 per-agent 配置覆盖）
        
        Returns:
            配置值
        """
        # 检查自动重载
        if time.time() - self.last_load > self.reload_interval:
            await self.reload()
        
        # 优先检查 per-agent 配置
        if agent_id:
            agent_key = f'{module}:{key}:{agent_id}'
            if agent_key in self.configs:
                logger.debug(f"Config HIT (agent): {agent_key}")
                return self.configs[agent_key]
        
        # 检查通用配置
        cache_key = f'{module}:{key}'
        if cache_key in self.configs:
            logger.debug(f"Config HIT: {cache_key}")
            return self.configs[cache_key]
        
        # 返回默认值
        logger.debug(f"Config MISS: {cache_key}, using default")
        return DEFAULT_CONFIGS.get(cache_key)
    
    async def set(self, module: str, key: str, value: Any, updated_by: str = 'system', agent_id: str = None) -> bool:
        """
        更新配置
        
        Args:
            module: 模块名
            key: 配置键
            value: 配置值
            updated_by: 更新者
            agent_id: 可选的 agent ID（per-agent 配置）
        
        Returns:
            是否成功
        """
        try:
            if not self.config_table:
                logger.error("Config table not initialized")
                return False
            
            config_id = f'config_{module}_{key}' + (f'_{agent_id}' if agent_id else '')
            
            # 检查是否存在
            existing = self.config_table.search("").where(f"id = '{config_id}'").limit(1).to_list()
            
            if existing:
                # 更新
                self.config_table.update(
                    values={
                        'config_value': value,
                        'version': self._increment_version(existing[0].get('version', '1.0.0')),
                        'updated_at': datetime.now().isoformat(),
                        'updated_by': updated_by
                    },
                    where=f"id = '{config_id}'"
                )
            else:
                # 新增
                self.config_table.add([{
                    'id': config_id,
                    'module': module,
                    'config_key': key,
                    'config_value': value,
                    'version': '1.0.0',
                    'updated_at': datetime.now().isoformat(),
                    'updated_by': updated_by,
                    'metadata': json.dumps({'source': 'custom'})
                }])
            
            # 更新内存缓存
            cache_key = f'{module}:{key}' + (f':{agent_id}' if agent_id else '')
            self.configs[cache_key] = value
            
            logger.info(f"Config updated: {module}:{key} (by {updated_by})")
            return True
            
        except Exception as e:
            logger.error(f"Config set failed: {e}")
            return False
    
    async def reload(self):
        """重新加载所有配置"""
        try:
            await self._load_from_lancedb()
            self.last_load = time.time()
            logger.info(f"Config reloaded: {len(self.configs)} configs")
        except Exception as e:
            logger.error(f"Config reload failed: {e}")
    
    def _increment_version(self, version: str) -> str:
        """版本号递增"""
        try:
            parts = version.split('.')
            if len(parts) >= 2:
                parts[1] = str(int(parts[1]) + 1)
                return '.'.join(parts)
        except:
            pass
        return '1.0.1'
    
    async def list_configs(self, module: str = None) -> Dict[str, Any]:
        """列出所有配置"""
        if module:
            return {k: v for k, v in self.configs.items() if k.startswith(f'{module}:')}
        return self.configs.copy()
    
    async def reset(self, module: str, key: str) -> bool:
        """重置配置到默认值"""
        cache_key = f'{module}:{key}'
        if cache_key in DEFAULT_CONFIGS:
            self.configs[cache_key] = DEFAULT_CONFIGS[cache_key]
            logger.info(f"Config reset: {cache_key}")
            # 清除 Redis 缓存
            if self.redis_client:
                self.redis_client.delete('config:all')
            return True
        return False
    
    async def auto_learn_keywords(self, module: str, key: str, new_keywords: list, source: str = 'session') -> bool:
        """
        自动学习新关键词（从会话积累）
        
        Args:
            module: 模块名
            key: 配置键
            new_keywords: 新关键词列表
            source: 来源（session/consolidate/user_feedback）
        
        Returns:
            是否成功
        """
        cache_key = f'{module}:{key}'
        current_config = self.configs.get(cache_key)
        
        if not current_config:
            logger.warning(f"Config not found: {cache_key}")
            return False
        
        # 合并关键词
        updated = False
        if isinstance(current_config, dict):
            # 字典格式（如 emotion_keywords）
            for category, data in current_config.items():
                if isinstance(data, dict) and 'keywords' in data:
                    keywords = data['keywords']
                    for kw in new_keywords:
                        if kw not in keywords:
                            keywords.append(kw)
                            updated = True
                            logger.info(f"Auto-learned keyword: {kw} -> {category}")
        elif isinstance(current_config, list):
            # 列表格式
            for kw in new_keywords:
                if kw not in current_config:
                    current_config.append(kw)
                    updated = True
                    logger.info(f"Auto-learned keyword: {kw}")
        
        if updated:
            # 保存到 LanceDB
            parts = cache_key.split(':', 1)
            module_name = parts[0]
            config_key = parts[1] if len(parts) > 1 else 'default'
            await self.set(module_name, config_key, current_config, f'auto_learn_{source}')
            logger.info(f"Config auto-updated: {cache_key}")
            return True
        
        return False
    
    async def extract_keywords_from_session(self, content: str) -> list:
        """
        从会话内容中提取潜在关键词
        
        Args:
            content: 会话内容
        
        Returns:
            提取的关键词列表
        """
        # 使用 jieba 分词
        try:
            import jieba
            
            # 分词
            words = jieba.lcut(content)
            
            # 过滤：2-4 字，排除停用词
            stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
            keywords = [w for w in words if 2 <= len(w) <= 4 and w not in stopwords and w.isascii() == False]
            
            # 词频统计
            from collections import Counter
            freq = Counter(keywords)
            
            # 返回高频词（出现 2 次以上）
            return [word for word, count in freq.most_common(10) if count >= 2]
            
        except Exception as e:
            logger.debug(f"Keyword extraction failed: {e}")
            return []


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


async def init_config_manager() -> ConfigManager:
    """初始化全局配置管理器"""
    global _config_manager
    _config_manager = ConfigManager()
    await _config_manager.initialize()
    return _config_manager

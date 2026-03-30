"""
进化系统核心引擎

统一管理所有进化模块，提供共享资源：
- BGE 模型（512 维）
- Redis 缓存层
- 意图模式（从 LanceDB 加载）
- 话题热度追踪
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .cache import CacheLayer

logger = logging.getLogger(__name__)


class EvolutionSystem:
    """进化系统核心引擎"""
    
    def __init__(self):
        self.cache = CacheLayer()
        self.model = None
        self.patterns = {}
        self.patterns_loaded = False
        
        # 配置
        self.EVOLUTION_SERVICES = {
            'think': 'http://127.0.0.1:9722/reason',
            'learn': 'http://127.0.0.1:9723/learn',
            'feel': 'http://127.0.0.1:9724/feel',
            'monitor': 'http://127.0.0.1:9725/monitor',
            'execute': 'http://127.0.0.1:9726/execute',
            'perceive': 'http://127.0.0.1:9727/perceive'
        }
        
        # 缓存 TTL
        self.EVOLUTION_CACHE_TTL = 600  # 10 分钟
        
        # 话题热度配置
        self.TOPIC_HALF_LIFE = 600000  # 10 分钟
        self.TOPIC_WEIGHTS = {
            '架构': 1.5, '系统': 1.5, '优化': 1.3, '性能': 1.3, '缓存': 1.2,
            '经济': 1.4, '金融': 1.4, '市场': 1.3, '投资': 1.3,
            '记忆': 1.4, '学习': 1.3, '知识': 1.2, '模型': 1.2,
            '测试': 1.1, '验证': 1.1, '实现': 1.1, '功能': 1.0,
            '你好': 0.5, 'hello': 0.5, '谢谢': 0.5, '再见': 0.5
        }
    
    def initialize(self, redis_host='localhost', redis_port=6379) -> bool:
        """初始化系统"""
        # 连接 Redis
        if not self.cache.connect_redis(redis_host, redis_port):
            logger.warning("Redis not available, cache disabled")
        
        # 加载意图模式
        self._load_intention_patterns()
        
        logger.info("EvolutionSystem initialized")
        return True
    
    def _load_intention_patterns(self):
        """从 LanceDB 加载意图模式"""
        try:
            import urllib.request
            
            req = urllib.request.Request(
                'http://127.0.0.1:9721/patterns',
                data=json.dumps({'action': 'load'}).encode(),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data.get('status') == 'ok':
                    self.patterns = data.get('patterns', {})
                    self.patterns_loaded = True
                    logger.info(f"Loaded {data.get('total', 0)} intention patterns")
        except Exception as e:
            logger.warning(f"Load patterns failed: {e}, using defaults")
            self._load_default_patterns()
    
    def _load_default_patterns(self):
        """加载默认意图模式（向后兼容）"""
        self.patterns = {
            'reasoning': [{'patterns': ['影响', '为什么', '推理', '分析', '原因', '结果'], 'confidence': 0.9}],
            'learning': [{'patterns': ['学习', '记住', '文档', '知识', '笔记'], 'confidence': 0.85}],
            'emotional': [{'patterns': ['心情', '高兴', '难过', '情绪', '感觉'], 'confidence': 0.8}],
            'task': [{'patterns': ['帮我', '执行', '任务', '发送', '完成'], 'confidence': 0.85}],
            'perception': [{'patterns': ['分析这条', '优先级', '紧急', '重要'], 'confidence': 0.75}]
        }
        self.patterns_loaded = True
    
    def analyze_intent(self, content: str) -> Dict[str, Any]:
        """分析用户意图"""
        patterns = self.patterns if self.patterns_loaded else self._get_default_patterns()
        
        best_match = {'type': 'conversation', 'action': 'search', 'confidence': 0.5, 'pattern': ''}
        
        for ptype, configs in patterns.items():
            for cfg in configs:
                for pattern in cfg.get('patterns', []):
                    if pattern in content and cfg['confidence'] > best_match['confidence']:
                        best_match = {
                            'type': ptype,
                            'action': cfg.get('action', 'think'),
                            'confidence': cfg['confidence'],
                            'pattern': pattern
                        }
        
        return best_match
    
    def _get_default_patterns(self):
        """获取默认模式"""
        return {
            'reasoning': [{'patterns': ['影响', '为什么', '推理', '分析'], 'action': 'think', 'confidence': 0.9}],
            'learning': [{'patterns': ['学习', '记住', '文档'], 'action': 'learn', 'confidence': 0.85}],
            'emotional': [{'patterns': ['心情', '高兴', '难过'], 'action': 'feel', 'confidence': 0.8}],
            'task': [{'patterns': ['帮我', '执行', '任务'], 'action': 'execute', 'confidence': 0.85}],
            'perception': [{'patterns': ['分析这条', '优先级'], 'action': 'perceive', 'confidence': 0.75}]
        }
    
    async def think(self, content: str) -> Dict[str, Any]:
        """推理模块"""
        from .modules.think import think as think_module
        return await think_module(content, self.cache, self.model)
    
    async def learn(self, content: str, material: Dict[str, Any]) -> Dict[str, Any]:
        """学习模块"""
        from .modules.learn import learn as learn_module
        return await learn_module(content, material, self.cache, self.model)
    
    async def feel(self, event: str) -> Dict[str, Any]:
        """情感模块"""
        from .modules.feel import feel as feel_module
        return await feel_module(event, self.cache)
    
    async def execute(self, goal: str) -> Dict[str, Any]:
        """执行模块"""
        from .modules.execute import execute as execute_module
        return await execute_module(goal, self.cache)
    
    async def perceive(self, content: str, source: str = 'message') -> Dict[str, Any]:
        """感知模块"""
        from .modules.perceive import perceive as perceive_module
        return await perceive_module(content, source, self.cache)
    
    async def monitor(self, content: str) -> Dict[str, Any]:
        """元认知模块"""
        from .modules.monitor import monitor as monitor_module
        return await monitor_module(content, self.cache)
    
    async def update_topic_heat(self, agent_id: str, content: str) -> str:
        """更新话题热度"""
        topic_key = self._simple_hash(content[:100])
        redis_key = f'topic_heat:{agent_id}:{topic_key}'
        
        # 提取关键词
        keywords = [k for k in self.TOPIC_WEIGHTS.keys() if k in content]
        importance = sum(self.TOPIC_WEIGHTS[k] for k in keywords) / len(keywords) if keywords else 1.0
        
        # Redis Hash 更新
        await self.cache.hincrby(redis_key, 'count', 1)
        await self.cache.hset(redis_key, 'last_access', str(int(datetime.now().timestamp() * 1000)))
        await self.cache.hset(redis_key, 'importance', str(importance))
        await self.cache.expire(redis_key, 86400)  # 24 小时
        
        return topic_key
    
    def _simple_hash(self, s: str) -> str:
        """简单 hash"""
        h = 0
        for c in s:
            h = ((h << 5) - h + ord(c)) & 0xFFFFFFFF
        return format(h, '08x')

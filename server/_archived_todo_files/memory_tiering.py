#!/usr/bin/env python3
"""
记忆分级存储模块 — 热/温/冷分层存储

论文依据：Model Distillation, Quantization, MSA
核心洞察：不是所有记忆都需要同样的精度和访问速度
"""

import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class MemoryTiering:
    """记忆分级存储引擎"""
    
    # 存储层级配置
    TIER_CONFIG = {
        'L0': {
            'name': '热记忆',
            'storage': 'redis',
            'ttl_days': 7,           # 7 天内活跃
            'precision': 'full',     # 完整精度 512 维
            'access_speed': 'fast'   # 最快访问
        },
        'L1': {
            'name': '温记忆',
            'storage': 'lancedb',
            'ttl_days': 90,          # 90 天内活跃
            'precision': 'compressed', # 压缩精度 128 维
            'access_speed': 'medium'  # 中等访问
        },
        'L2': {
            'name': '冷记忆',
            'storage': 'filesystem',
            'ttl_days': 365,         # 365 天内活跃
            'precision': 'summary',  # 摘要文本
            'access_speed': 'slow'   # 慢速访问
        }
    }
    
    def __init__(self, memory_client, redis_client=None, base_path='/Users/lx/.openclaw/evolution/data/cold_storage'):
        self.memory = memory_client
        self.redis = redis_client
        self.base_path = base_path
        
        # 创建冷存储目录
        os.makedirs(base_path, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'L0_count': 0,
            'L1_count': 0,
            'L2_count': 0,
            'migrations': 0
        }
        
        logger.info("MemoryTiering initialized")
    
    def classify_memory(self, memory: Dict) -> Tuple[str, str]:
        """
        分类记忆到合适的层级
        
        Returns:
            (层级，原因)
        """
        # 获取记忆属性
        importance = memory.get('importance', 0.5)
        created_at = memory.get('created_at', '')
        last_accessed = memory.get('last_accessed', '')
        retrieval_count = memory.get('retrieval_count', 0)
        
        # 计算新鲜度
        try:
            if last_accessed:
                last = datetime.fromisoformat(last_accessed)
                age_days = (datetime.now() - last).days
            elif created_at:
                created = datetime.fromisoformat(created_at)
                age_days = (datetime.now() - created).days
            else:
                age_days = 365
        except:
            age_days = 365
        
        # 分类逻辑
        if age_days <= 7 and (importance > 0.7 or retrieval_count > 10):
            return 'L0', 'recent_and_important'
        elif age_days <= 90 and importance > 0.5:
            return 'L1', 'moderate_age_and_importance'
        else:
            return 'L2', 'old_or_low_importance'
    
    def migrate_to_tier(self, memory_id: str, target_tier: str):
        """迁移记忆到指定层级"""
        logger.info(f"Migrating {memory_id} to {target_tier}")
        
        # 获取记忆
        memory = self._get_memory(memory_id)
        if not memory:
            return False
        
        # 根据层级处理
        if target_tier == 'L0':
            # 热记忆：存储到 Redis
            self._store_hot(memory)
        elif target_tier == 'L1':
            # 温记忆：压缩后存储到 LanceDB
            self._store_warm(memory)
        else:  # L2
            # 冷记忆：摘要后存储到文件系统
            self._store_cold(memory)
        
        # 更新记忆元数据
        self._update_memory_tier(memory_id, target_tier)
        
        self.stats['migrations'] += 1
        logger.info(f"Migration complete: {memory_id} → {target_tier}")
        return True
    
    def _store_hot(self, memory: Dict):
        """存储热记忆到 Redis"""
        if self.redis:
            key = f"memory:hot:{memory['id']}"
            # 完整精度存储
            self.redis.setex(
                key,
                7 * 86400,  # 7 天 TTL
                json.dumps(memory, ensure_ascii=False)
            )
            self.stats['L0_count'] += 1
            logger.info(f"Stored hot memory: {memory['id']}")
    
    def _store_warm(self, memory: Dict):
        """存储温记忆到 LanceDB (压缩)"""
        # 向量压缩 (512→128 维)
        if 'embedding' in memory:
            embedding = memory['embedding']
            if len(embedding) == 512:
                # 简单降采样压缩
                compressed = [embedding[i*4] for i in range(128)]
                memory['embedding_compressed'] = compressed
                memory['compression'] = '512to128'
        
        # 更新到 LanceDB
        self.memory.save(
            content=memory.get('content', ''),
            type=memory.get('type', 'semantic'),
            metadata={
                **memory,
                'tier': 'L1',
                'compressed': True
            }
        )
        self.stats['L1_count'] += 1
        logger.info(f"Stored warm memory: {memory['id']}")
    
    def _store_cold(self, memory: Dict):
        """存储冷记忆到文件系统 (摘要)"""
        memory_id = memory.get('id', 'unknown')
        content = memory.get('content', '')
        
        # 生成摘要 (简化版：截取前 200 字)
        summary = content[:200] + '...' if len(content) > 200 else content
        
        # 存储到文件
        filepath = os.path.join(self.base_path, f"{memory_id}.json")
        cold_data = {
            'id': memory_id,
            'summary': summary,
            'type': memory.get('type', 'semantic'),
            'importance': memory.get('importance', 0.5),
            'created_at': memory.get('created_at', ''),
            'tier': 'L2'
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cold_data, f, ensure_ascii=False, indent=2)
        
        self.stats['L2_count'] += 1
        logger.info(f"Stored cold memory: {memory_id} → {filepath}")
    
    def auto_migrate(self):
        """自动迁移记忆到合适层级"""
        logger.info("Starting auto migration...")
        
        # 获取所有记忆
        memories = self._get_all_memories()
        
        migrated = 0
        for memory in memories:
            tier, reason = self.classify_memory(memory)
            current_tier = memory.get('tier', 'L1')
            
            if tier != current_tier:
                self.migrate_to_tier(memory['id'], tier)
                migrated += 1
        
        logger.info(f"Auto migration complete: {migrated} memories migrated")
        return migrated
    
    def search_across_tiers(self, query: str, limit: int = 10) -> List[Dict]:
        """跨层级检索"""
        results = []
        
        # L0: 热记忆检索 (Redis)
        if self.redis:
            # TODO: 实现 Redis 向量检索
            pass
        
        # L1: 温记忆检索 (LanceDB)
        l1_results = self.memory.search(query, limit=limit)
        results.extend(l1_results)
        
        # L2: 冷记忆检索 (文件系统)
        # TODO: 实现文件系统摘要检索
        
        return results[:limit]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'total_memories': self.stats['L0_count'] + self.stats['L1_count'] + self.stats['L2_count'],
            'tier_distribution': {
                'L0': f"{self.stats['L0_count']} (热)",
                'L1': f"{self.stats['L1_count']} (温)",
                'L2': f"{self.stats['L2_count']} (冷)"
            }
        }
    
    def _get_memory(self, memory_id: str) -> Optional[Dict]:
        """获取记忆"""
        # TODO: 实现
        return {'id': memory_id}
    
    def _get_all_memories(self) -> List[Dict]:
        """获取所有记忆"""
        # TODO: 实现
        return []
    
    def _update_memory_tier(self, memory_id: str, tier: str):
        """更新记忆层级元数据"""
        # TODO: 实现
        pass


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class TieringHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.command} {self.path}")
    
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        
        # TODO: 初始化 tiering
        tiering = None
        
        try:
            if self.path == '/classify':
                tier, reason = tiering.classify_memory(body.get('memory', {}))
                self._json_response({
                    'tier': tier,
                    'reason': reason
                })
            
            elif self.path == '/migrate':
                success = tiering.migrate_to_tier(
                    body.get('memory_id', ''),
                    body.get('tier', 'L1')
                )
                self._json_response({'status': 'ok' if success else 'failed'})
            
            elif self.path == '/auto_migrate':
                count = tiering.auto_migrate()
                self._json_response({
                    'status': 'ok',
                    'migrated': count
                })
            
            elif self.path == '/stats':
                self._json_response(tiering.get_stats())
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)
    
    def do_GET(self):
        if self.path == '/stats':
            tiering = MemoryTiering(None)
            self._json_response(tiering.get_stats())
        elif self.path == '/health':
            self._json_response({'status': 'ok'})
        else:
            self._json_response({'error': 'not found'}, 404)


if __name__ == '__main__':
    import socket
    PORT = 9733
    server = HTTPServer(('127.0.0.1', PORT), TieringHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"MemoryTiering Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

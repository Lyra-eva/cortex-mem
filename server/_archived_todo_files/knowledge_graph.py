#!/usr/bin/env python3
"""
知识图谱增强模块 — 将 links 从 ID 列表增强为关系图

关系类型：
- causes: 因果关系
- similar_to: 相似关系
- example_of: 示例关系
- part_of: 部分关系
- antonym: 反义关系
- related_to: 一般相关
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """知识图谱引擎"""
    
    # 关系类型定义
    RELATIONS = {
        'causes': '导致',
        'similar_to': '相似于',
        'example_of': '示例',
        'part_of': '部分',
        'antonym': '反义',
        'related_to': '相关'
    }
    
    def __init__(self, memory_client):
        self.memory = memory_client
        logger.info("KnowledgeGraph initialized")
    
    def add_relation(self, source_id: str, target_id: str, relation: str, strength: float = 0.8):
        """添加关系"""
        if relation not in self.RELATIONS:
            logger.warning(f"Unknown relation: {relation}")
            relation = 'related_to'
        
        # 获取源记忆
        source = self._get_memory(source_id)
        if not source:
            return False
        
        # 更新 links
        links = json.loads(source.get('links', '[]'))
        
        # 检查是否已存在
        for link in links:
            if isinstance(link, dict) and link.get('id') == target_id:
                link['strength'] = max(link.get('strength', 0), strength)
                link['updated_at'] = datetime.now().isoformat()
                return self._update_memory(source_id, {'links': json.dumps(links)})
        
        # 添加新关系
        links.append({
            'id': target_id,
            'relation': relation,
            'strength': strength,
            'created_at': datetime.now().isoformat()
        })
        
        return self._update_memory(source_id, {'links': json.dumps(links)})
    
    def multi_hop_search(self, query: str, hops: int = 2, limit: int = 10):
        """多跳检索"""
        # 第 1 跳：直接检索
        results = self.memory.search(query, limit=limit)
        
        if hops <= 1:
            return results
        
        # 第 2-N 跳：关联检索
        all_results = results.copy()
        for h in range(1, hops):
            hop_results = []
            for mem in all_results[-limit:]:
                links = json.loads(mem.get('links', '[]'))
                for link in links:
                    if isinstance(link, dict):
                        target_id = link.get('id')
                        relation = link.get('relation', 'related_to')
                        strength = link.get('strength', 0.5)
                        
                        # 获取目标记忆
                        target = self._get_memory(target_id)
                        if target and target not in hop_results:
                            target['_relation'] = relation
                            target['_hop'] = h + 1
                            target['_strength'] = strength
                            hop_results.append(target)
            
            all_results.extend(hop_results)
            if not hop_results:
                break
        
        # 去重
        seen = set()
        unique = []
        for r in all_results:
            if r['id'] not in seen:
                seen.add(r['id'])
                unique.append(r)
        
        return unique[:limit]
    
    def get_relations(self, memory_id: str) -> List[Dict]:
        """获取记忆的所有关系"""
        memory = self._get_memory(memory_id)
        if not memory:
            return []
        
        links = json.loads(memory.get('links', '[]'))
        relations = []
        
        for link in links:
            if isinstance(link, dict):
                relations.append({
                    'target_id': link.get('id'),
                    'relation': link.get('relation', 'related_to'),
                    'strength': link.get('strength', 0.5)
                })
        
        return relations
    
    def infer_relation(self, source_content: str, target_content: str) -> str:
        """推断关系类型"""
        # 简化版规则推断
        source_lower = source_content.lower()
        target_lower = target_content.lower()
        
        # 因果推断
        if any(w in source_lower for w in ['导致', '引起', 'cause', 'lead to']):
            return 'causes'
        
        # 相似推断
        if any(w in source_lower for w in ['类似', '相似', 'similar']):
            return 'similar_to'
        
        # 示例推断
        if any(w in source_lower for w in ['例如', '比如', 'example']):
            return 'example_of'
        
        # 部分推断
        if any(w in source_lower for w in ['部分', '组成', 'part of']):
            return 'part_of'
        
        # 反义推断
        if any(w in source_lower for w in ['相反', '反义', 'opposite']):
            return 'antonym'
        
        return 'related_to'
    
    def _get_memory(self, memory_id: str) -> Optional[Dict]:
        """获取记忆"""
        # TODO: 实现记忆获取
        return {'id': memory_id, 'links': '[]'}
    
    def _update_memory(self, memory_id: str, updates: Dict) -> bool:
        """更新记忆"""
        # TODO: 实现记忆更新
        return True


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class KGHandler(BaseHTTPRequestHandler):
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
        
        # TODO: 初始化 memory_client 和 kg
        kg = None
        
        try:
            if self.path == '/add_relation':
                # 添加关系
                result = kg.add_relation(
                    body.get('source_id'),
                    body.get('target_id'),
                    body.get('relation', 'related_to'),
                    body.get('strength', 0.8)
                )
                self._json_response({'status': 'ok' if result else 'failed'})
            
            elif self.path == '/multi_hop':
                # 多跳检索
                results = kg.multi_hop_search(
                    body.get('query', ''),
                    body.get('hops', 2),
                    body.get('limit', 10)
                )
                self._json_response({'results': results, 'count': len(results)})
            
            elif self.path == '/get_relations':
                # 获取关系
                relations = kg.get_relations(body.get('memory_id', ''))
                self._json_response({'relations': relations})
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)


if __name__ == '__main__':
    import socket
    PORT = 9728
    server = HTTPServer(('127.0.0.1', PORT), KGHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"KnowledgeGraph Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

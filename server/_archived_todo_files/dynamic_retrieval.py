#!/usr/bin/env python3
"""
动态稀疏检索模块 — 根据查询复杂度动态调整 k 值

核心洞察：Sparse Attention 论文 (80+ 篇)
> 不是所有 token 都同等重要，选择性关注是关键。
"""

import re
import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class DynamicRetrieval:
    """动态检索引擎"""
    
    # 查询复杂度关键词
    COMPLEX_PATTERNS = [
        '分析', '推理', '比较', '对比', '评估', '判断',
        '为什么', '如何', '怎么', 'what', 'how', 'why',
        '优缺点', '影响', '趋势', '预测', '关系'
    ]
    
    SIMPLE_PATTERNS = [
        '是什么', '定义', 'hello', '你好', '谢谢',
        '在吗', '早', '好', 'yes', 'no'
    ]
    
    def __init__(self, memory_client):
        self.memory = memory_client
        self.stats = {
            'simple_queries': 0,
            'medium_queries': 0,
            'complex_queries': 0
        }
        logger.info("DynamicRetrieval initialized")
    
    def classify_query(self, query: str) -> Tuple[str, float]:
        """
        查询复杂度分类
        
        Returns:
            (复杂度级别，置信度)
        """
        query_lower = query.lower()
        
        # 计算复杂度分数
        complexity_score = 0
        
        # 长度因素
        if len(query) > 50:
            complexity_score += 0.3
        elif len(query) > 20:
            complexity_score += 0.1
        
        # 关键词因素
        complex_count = sum(1 for p in self.COMPLEX_PATTERNS if p in query_lower)
        simple_count = sum(1 for p in self.SIMPLE_PATTERNS if p in query_lower)
        
        if complex_count >= 2:
            complexity_score += 0.5
        elif complex_count == 1:
            complexity_score += 0.2
        
        if simple_count >= 1:
            complexity_score -= 0.3
        
        # 问题类型因素
        if any(w in query_lower for w in ['为什么', '如何', '怎么', 'why', 'how']):
            complexity_score += 0.2
        
        # 分类
        if complexity_score >= 0.5:
            level = 'complex'
            self.stats['complex_queries'] += 1
        elif complexity_score >= 0.2:
            level = 'medium'
            self.stats['medium_queries'] += 1
        else:
            level = 'simple'
            self.stats['simple_queries'] += 1
        
        confidence = min(1.0, 0.5 + abs(complexity_score - 0.5))
        
        logger.info(f"Query classified: {level} (confidence={confidence:.2f}, score={complexity_score:.2f})")
        return level, confidence
    
    def get_optimal_k(self, query: str, base_k: int = 5) -> int:
        """获取最优 k 值"""
        level, confidence = self.classify_query(query)
        
        if level == 'simple':
            k = max(3, base_k - 2)
        elif level == 'medium':
            k = base_k
        else:  # complex
            k = min(15, base_k + 5)
        
        logger.info(f"Optimal k={k} for query: {query[:30]}...")
        return k
    
    def search(self, query: str, base_k: int = 5, **kwargs):
        """动态检索"""
        k = self.get_optimal_k(query, base_k)
        
        results = self.memory.search(query, limit=k, **kwargs)
        
        # 记录统计
        logger.info(f"Retrieved {len(results)} results with k={k}")
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = sum(self.stats.values())
        return {
            **self.stats,
            'total_queries': total,
            'simple_ratio': self.stats['simple_queries'] / total * 100 if total > 0 else 0,
            'complex_ratio': self.stats['complex_queries'] / total * 100 if total > 0 else 0
        }


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class DRHandler(BaseHTTPRequestHandler):
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
        
        # TODO: 初始化 memory_client 和 dr
        dr = None
        
        try:
            if self.path == '/classify':
                level, confidence = dr.classify_query(body.get('query', ''))
                self._json_response({
                    'level': level,
                    'confidence': confidence
                })
            
            elif self.path == '/search':
                results = dr.search(
                    body.get('query', ''),
                    body.get('base_k', 5)
                )
                self._json_response({
                    'results': results,
                    'count': len(results),
                    'stats': dr.get_stats()
                })
            
            elif self.path == '/stats':
                self._json_response(dr.get_stats())
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)


if __name__ == '__main__':
    import socket
    PORT = 9729
    server = HTTPServer(('127.0.0.1', PORT), DRHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"DynamicRetrieval Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

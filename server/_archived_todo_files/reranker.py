#!/usr/bin/env python3
"""
检索重排序模块 — 多因素加权重排序

论文依据：RAG Optimization (50+ 篇)
核心洞察：检索质量决定 RAG 上限
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class Reranker:
    """重排序引擎"""
    
    # 默认权重
    DEFAULT_WEIGHTS = {
        'similarity': 0.4,   # 向量相似度
        'importance': 0.3,   # 记忆重要性
        'recency': 0.2,      # 新鲜度
        'relevance': 0.1     # 查询相关性
    }
    
    def __init__(self, memory_client):
        self.memory = memory_client
        self.weights = self.DEFAULT_WEIGHTS.copy()
        logger.info("Reranker initialized")
    
    def update_weights(self, new_weights: Dict[str, float]):
        """更新权重"""
        # 验证权重和为 1
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0, normalizing...")
            new_weights = {k: v/total for k, v in new_weights.items()}
        
        self.weights.update(new_weights)
        logger.info(f"Weights updated: {self.weights}")
    
    def calculate_score(self, result: Dict, query: str) -> float:
        """计算综合得分"""
        scores = {}
        
        # 1. 向量相似度 (从 _distance 转换)
        distance = result.get('_distance', 1.0)
        scores['similarity'] = 1.0 - min(distance, 1.0)
        
        # 2. 记忆重要性
        importance = result.get('importance', 0.5)
        scores['importance'] = importance
        
        # 3. 新鲜度 (recency)
        created_at = result.get('created_at', '')
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                age_days = (datetime.now() - created).days
                # 指数衰减：新鲜度 = e^(-age/30)
                scores['recency'] = 2.718 ** (-min(age_days, 90) / 30)
            except:
                scores['recency'] = 0.5
        else:
            scores['recency'] = 0.5
        
        # 4. 查询相关性 (关键词匹配)
        content = result.get('content', '').lower()
        query_words = query.lower().split()
        match_count = sum(1 for w in query_words if w in content)
        scores['relevance'] = match_count / len(query_words) if query_words else 0
        
        # 加权求和
        final_score = sum(
            scores.get(k, 0) * w 
            for k, w in self.weights.items()
        )
        
        result['_rerank_score'] = final_score
        result['_scores'] = scores
        
        return final_score
    
    def rerank(self, results: List[Dict], query: str) -> List[Dict]:
        """重排序"""
        logger.info(f"Reranking {len(results)} results")
        
        # 计算得分
        for r in results:
            self.calculate_score(r, query)
        
        # 按综合得分排序
        reranked = sorted(
            results,
            key=lambda x: x.get('_rerank_score', 0),
            reverse=True
        )
        
        logger.info(f"Reranking complete. Top score: {reranked[0].get('_rerank_score', 0) if reranked else 0:.3f}")
        return reranked
    
    def explain_ranking(self, result: Dict) -> Dict:
        """解释排序原因"""
        return {
            'id': result.get('id'),
            'content': result.get('content', '')[:50],
            'final_score': result.get('_rerank_score', 0),
            'breakdown': result.get('_scores', {}),
            'weights': self.weights
        }
    
    def learn_from_feedback(self, query: str, results: List[Dict], selected_id: str):
        """从用户反馈学习权重"""
        # 找到用户选择的结果
        selected = next((r for r in results if r.get('id') == selected_id), None)
        if not selected:
            return
        
        # 分析为什么用户选择这个结果
        scores = selected.get('_scores', {})
        
        # 简单策略：高分因素增加权重，低分因素减少权重
        for factor, score in scores.items():
            if score > 0.7:
                self.weights[factor] = min(0.5, self.weights.get(factor, 0.25) * 1.1)
            elif score < 0.3:
                self.weights[factor] = max(0.05, self.weights.get(factor, 0.25) * 0.9)
        
        # 重新归一化
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
        
        logger.info(f"Learned from feedback. New weights: {self.weights}")


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class RerankHandler(BaseHTTPRequestHandler):
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
        
        # TODO: 初始化 memory_client 和 reranker
        reranker = None
        
        try:
            if self.path == '/rerank':
                results = reranker.rerank(
                    body.get('results', []),
                    body.get('query', '')
                )
                self._json_response({
                    'results': results,
                    'count': len(results)
                })
            
            elif self.path == '/update_weights':
                reranker.update_weights(body.get('weights', {}))
                self._json_response({'status': 'ok', 'weights': reranker.weights})
            
            elif self.path == '/explain':
                explanation = reranker.explain_ranking(body.get('result', {}))
                self._json_response(explanation)
            
            elif self.path == '/feedback':
                reranker.learn_from_feedback(
                    body.get('query', ''),
                    body.get('results', []),
                    body.get('selected_id', '')
                )
                self._json_response({'status': 'ok'})
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)


if __name__ == '__main__':
    import socket
    PORT = 9730
    server = HTTPServer(('127.0.0.1', PORT), RerankHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"Reranker Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

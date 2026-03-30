#!/usr/bin/env python3
"""
元认知反馈学习模块 — 从用户反馈中学习优化

论文依据：Reinforcement Learning (100+ 篇), PPO, Reward Modeling
核心洞察：从反馈中持续优化行为策略
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class FeedbackLearner:
    """反馈学习引擎"""
    
    def __init__(self, memory_client):
        self.memory = memory_client
        self.feedback_history = []
        self.policy = {
            'response_style': 'balanced',  # concise/detailed/balanced
            'memory_retrieval_k': 5,
            'use_emotion': True,
            'use_metacognition': True
        }
        logger.info("FeedbackLearner initialized")
    
    def collect_feedback(self, query: str, response: str, feedback: Dict):
        """收集用户反馈"""
        feedback_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': response[:200],
            'feedback': feedback,
            'reward': self._calculate_reward(feedback)
        }
        
        self.feedback_history.append(feedback_record)
        
        # 存储到记忆系统
        self.memory.save(
            content=f"用户反馈：{feedback.get('type', 'unknown')} - {query[:50]}",
            type='episodic',
            metadata={
                'category': 'user_feedback',
                'reward': feedback_record['reward'],
                'feedback': feedback
            }
        )
        
        logger.info(f"Feedback collected. Reward: {feedback_record['reward']}")
        return feedback_record['reward']
    
    def _calculate_reward(self, feedback: Dict) -> float:
        """计算奖励值"""
        reward = 0.5  # 基础奖励
        
        # 显式评分
        if 'rating' in feedback:
            rating = feedback['rating']
            if rating >= 4:
                reward += 0.4
            elif rating >= 3:
                reward += 0.2
            elif rating <= 2:
                reward -= 0.3
        
        # 情感分析
        if 'sentiment' in feedback:
            sentiment = feedback['sentiment']
            if sentiment == 'positive':
                reward += 0.3
            elif sentiment == 'negative':
                reward -= 0.3
        
        # 行为信号
        if feedback.get('helpful', False):
            reward += 0.2
        if feedback.get('continue_conversation', False):
            reward += 0.1
        
        return min(1.0, max(0.0, reward))
    
    def update_policy(self):
        """更新策略 (简化版 PPO)"""
        if len(self.feedback_history) < 10:
            logger.info("Not enough feedback for policy update")
            return
        
        # 分析高奖励和低奖励样本
        recent = self.feedback_history[-50:]
        high_reward = [f for f in recent if f['reward'] > 0.7]
        low_reward = [f for f in recent if f['reward'] < 0.3]
        
        # 学习高奖励模式
        if high_reward:
            # 分析共同特征
            concise_count = sum(1 for f in high_reward if len(f['response']) < 200)
            detailed_count = len(high_reward) - concise_count
            
            if concise_count > detailed_count:
                self.policy['response_style'] = 'concise'
            else:
                self.policy['response_style'] = 'detailed'
        
        # 避免低奖励模式
        if low_reward:
            # 分析负面模式
            negative_patterns = []
            for f in low_reward:
                if 'too long' in f['feedback'].get('comment', '').lower():
                    negative_patterns.append('length')
                if 'not helpful' in f['feedback'].get('comment', '').lower():
                    negative_patterns.append('relevance')
            
            # 调整策略
            if 'length' in negative_patterns:
                self.policy['response_style'] = 'concise'
        
        logger.info(f"Policy updated: {self.policy}")
        return self.policy
    
    def get_optimal_params(self, query: str) -> Dict:
        """获取最优参数"""
        # 基于查询类型调整
        if len(query) < 10:
            return {
                'k': 3,
                'style': 'concise',
                'use_emotion': True
            }
        elif any(w in query.lower() for w in ['分析', '推理', '复杂']):
            return {
                'k': 10,
                'style': 'detailed',
                'use_emotion': False,
                'use_metacognition': True
            }
        else:
            return {
                'k': self.policy['memory_retrieval_k'],
                'style': self.policy['response_style'],
                'use_emotion': self.policy['use_emotion'],
                'use_metacognition': self.policy['use_metacognition']
            }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.feedback_history:
            return {'total_feedback': 0}
        
        rewards = [f['reward'] for f in self.feedback_history]
        return {
            'total_feedback': len(self.feedback_history),
            'avg_reward': sum(rewards) / len(rewards),
            'high_reward_count': sum(1 for r in rewards if r > 0.7),
            'low_reward_count': sum(1 for r in rewards if r < 0.3),
            'current_policy': self.policy
        }


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class FeedbackHandler(BaseHTTPRequestHandler):
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
        
        # TODO: 初始化 memory_client 和 learner
        learner = None
        
        try:
            if self.path == '/feedback':
                reward = learner.collect_feedback(
                    body.get('query', ''),
                    body.get('response', ''),
                    body.get('feedback', {})
                )
                self._json_response({
                    'status': 'ok',
                    'reward': reward
                })
            
            elif self.path == '/update_policy':
                policy = learner.update_policy()
                self._json_response({
                    'status': 'ok',
                    'policy': policy
                })
            
            elif self.path == '/get_params':
                params = learner.get_optimal_params(body.get('query', ''))
                self._json_response(params)
            
            elif self.path == '/stats':
                self._json_response(learner.get_stats())
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)


if __name__ == '__main__':
    import socket
    PORT = 9731
    server = HTTPServer(('127.0.0.1', PORT), FeedbackHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"FeedbackLearner Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

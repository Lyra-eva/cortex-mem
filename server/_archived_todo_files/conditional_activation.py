#!/usr/bin/env python3
"""
条件系统激活模块 — MoE (Mixture of Experts) 架构

论文依据：Mixture of Experts, Sparse Attention
核心洞察：不是所有任务都需要激活所有系统，条件激活可提升效率
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class ConditionalActivation:
    """条件系统激活引擎"""
    
    # 系统定义
    SYSTEMS = {
        'perception': {'port': 9727, 'priority': 1},  # 总是激活
        'memory': {'port': 9721, 'priority': 1},      # 总是激活
        'emotion': {'port': 9724, 'priority': 2},     # 按需激活
        'thinking': {'port': 9722, 'priority': 2},    # 按需激活
        'learning': {'port': 9723, 'priority': 2},    # 按需激活
        'metacognition': {'port': 9725, 'priority': 3}, # 复杂任务激活
        'action': {'port': 9726, 'priority': 3}       # 执行任务时激活
    }
    
    # 查询类型到系统映射
    QUERY_TYPE_SYSTEMS = {
        'greeting': ['perception', 'memory'],
        'simple_query': ['perception', 'memory'],
        'knowledge_query': ['perception', 'memory', 'thinking'],
        'emotional_query': ['perception', 'memory', 'emotion'],
        'learning_task': ['perception', 'memory', 'learning'],
        'complex_reasoning': ['perception', 'memory', 'thinking', 'metacognition'],
        'action_task': ['perception', 'memory', 'thinking', 'action'],
        'full_analysis': ['perception', 'memory', 'thinking', 'emotion', 'metacognition', 'action']
    }
    
    def __init__(self):
        self.stats = {
            'total_queries': 0,
            'system_activations': {name: 0 for name in self.SYSTEMS}
        }
        logger.info("ConditionalActivation initialized")
    
    def classify_query_type(self, query: str) -> str:
        """查询类型分类"""
        query_lower = query.lower()
        
        # 问候
        if any(w in query_lower for w in ['你好', 'hello', 'hi', '早', '好']):
            return 'greeting'
        
        # 情感查询
        if any(w in query_lower for w in ['高兴', '生气', '伤心', '情绪', '感觉']):
            return 'emotional_query'
        
        # 学习任务
        if any(w in query_lower for w in ['学习', '记住', '记录', '保存']):
            return 'learning_task'
        
        # 复杂推理
        if any(w in query_lower for w in ['分析', '推理', '比较', '对比', '评估', '为什么', '如何']):
            if len(query) > 30:
                return 'complex_reasoning'
            else:
                return 'knowledge_query'
        
        # 行动任务
        if any(w in query_lower for w in ['执行', '做', '发送', '创建', '调用']):
            return 'action_task'
        
        # 知识查询
        if any(w in query_lower for w in ['是什么', '定义', '意思', '解释']):
            return 'knowledge_query'
        
        # 简单查询
        if len(query) < 20:
            return 'simple_query'
        
        # 默认：完整分析
        return 'full_analysis'
    
    def get_active_systems(self, query: str) -> List[str]:
        """获取需要激活的系统"""
        query_type = self.classify_query_type(query)
        systems = self.QUERY_TYPE_SYSTEMS.get(query_type, ['perception', 'memory'])
        
        # 更新统计
        self.stats['total_queries'] += 1
        for system in systems:
            self.stats['system_activations'][system] += 1
        
        logger.info(f"Query type: {query_type}, Active systems: {systems}")
        return systems
    
    def should_activate(self, system: str, query: str) -> bool:
        """判断是否激活特定系统"""
        active_systems = self.get_active_systems(query)
        return system in active_systems
    
    def get_activation_config(self, query: str) -> Dict:
        """获取激活配置"""
        active_systems = self.get_active_systems(query)
        
        config = {
            'timestamp': datetime.now().isoformat(),
            'query_type': self.classify_query_type(query),
            'active_systems': active_systems,
            'inactive_systems': [s for s in self.SYSTEMS if s not in active_systems],
            'estimated_latency': self._estimate_latency(active_systems),
            'resource_usage': self._estimate_resources(active_systems)
        }
        
        return config
    
    def _estimate_latency(self, systems: List[str]) -> str:
        """估算延迟"""
        if len(systems) <= 2:
            return '<50ms (fast)'
        elif len(systems) <= 4:
            return '50-200ms (medium)'
        else:
            return '200-500ms (slow)'
    
    def _estimate_resources(self, systems: List[str]) -> str:
        """估算资源使用"""
        if len(systems) <= 2:
            return 'low'
        elif len(systems) <= 4:
            return 'medium'
        else:
            return 'high'
    
    def optimize_activation(self, feedback: Dict):
        """根据反馈优化激活策略"""
        # TODO: 实现强化学习优化
        logger.info("Optimizing activation strategy based on feedback")
        pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.stats['total_queries']
        return {
            'total_queries': total,
            'system_activations': self.stats['system_activations'],
            'activation_ratios': {
                name: count / total * 100 if total > 0 else 0
                for name, count in self.stats['system_activations'].items()
            },
            'avg_active_systems': sum(self.stats['system_activations'].values()) / total if total > 0 else 0
        }


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class ActivationHandler(BaseHTTPRequestHandler):
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
        
        activator = ConditionalActivation()
        
        try:
            if self.path == '/classify':
                query_type = activator.classify_query_type(body.get('query', ''))
                self._json_response({'query_type': query_type})
            
            elif self.path == '/get_active_systems':
                systems = activator.get_active_systems(body.get('query', ''))
                self._json_response({
                    'active_systems': systems,
                    'count': len(systems)
                })
            
            elif self.path == '/get_config':
                config = activator.get_activation_config(body.get('query', ''))
                self._json_response(config)
            
            elif self.path == '/should_activate':
                should = activator.should_activate(
                    body.get('system', ''),
                    body.get('query', '')
                )
                self._json_response({'should_activate': should})
            
            elif self.path == '/stats':
                self._json_response(activator.get_stats())
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)
    
    def do_GET(self):
        if self.path == '/stats':
            activator = ConditionalActivation()
            self._json_response(activator.get_stats())
        elif self.path == '/health':
            self._json_response({'status': 'ok'})
        else:
            self._json_response({'error': 'not found'}, 404)


if __name__ == '__main__':
    import socket
    PORT = 9734
    server = HTTPServer(('127.0.0.1', PORT), ActivationHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"ConditionalActivation Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

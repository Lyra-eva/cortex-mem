"""
进化系统 HTTP 服务

提供 REST API 接口，兼容现有调用方式
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Dict, Any

from .core import EvolutionSystem

logger = logging.getLogger(__name__)

# 全局实例
evolution_system = None


class EvolutionHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        logger.info(f"{self.command} {self.path}")
    
    def _json_response(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_GET(self):
        if self.path == '/health':
            self._json_response({
                'status': 'ok',
                'service': 'evolution-system',
                'version': '1.0.0',
                'modules': ['think', 'learn', 'feel', 'execute', 'perceive', 'monitor'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            self._json_response({'error': 'not found'}, 404)
    
    def do_POST(self):
        global evolution_system
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length).decode()) if content_length > 0 else {}
        
        try:
            if self.path == '/evolve':
                # 统一进化接口
                action = body.get('action')
                if not action:
                    return self._json_response({'error': 'action required'}, 400)
                
                result = await _handle_action(action, body, evolution_system)
                self._json_response(result)
            
            elif self.path == '/think':
                content = body.get('content', '')
                result = await evolution_system.think(content)
                self._json_response(result)
            
            elif self.path == '/learn':
                content = body.get('content', '')
                material = body.get('material', {})
                result = await evolution_system.learn(content, material)
                self._json_response(result)
            
            elif self.path == '/feel':
                event = body.get('event', '')
                result = await evolution_system.feel(event)
                self._json_response(result)
            
            elif self.path == '/execute':
                goal = body.get('goal', '')
                result = await evolution_system.execute(goal)
                self._json_response(result)
            
            elif self.path == '/perceive':
                content = body.get('content', '')
                source = body.get('source', 'message')
                result = await evolution_system.perceive(content, source)
                self._json_response(result)
            
            elif self.path == '/monitor':
                content = body.get('content', '')
                result = await evolution_system.monitor(content)
                self._json_response(result)
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error handling {self.path}: {e}")
            self._json_response({'error': str(e)}, 500)


async def _handle_action(action: str, body: Dict, system: EvolutionSystem) -> Dict:
    """处理动作请求"""
    if action == 'think':
        return await system.think(body.get('content', ''))
    elif action == 'learn':
        return await system.learn(body.get('content', ''), body.get('material', {}))
    elif action == 'feel':
        return await system.feel(body.get('event', ''))
    elif action == 'execute':
        return await system.execute(body.get('goal', ''))
    elif action == 'perceive':
        return await system.perceive(body.get('content', ''), body.get('source', 'message'))
    elif action == 'monitor':
        return await system.monitor(body.get('content', ''))
    else:
        return {'error': f'unknown action: {action}'}


def run_server(host='127.0.0.1', port=9721):
    """运行 HTTP 服务"""
    global evolution_system
    
    # 初始化系统
    evolution_system = EvolutionSystem()
    evolution_system.initialize()
    
    # 启动服务器
    server = HTTPServer((host, port), EvolutionHandler)
    logger.info(f"Evolution System listening on http://{host}:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    run_server()

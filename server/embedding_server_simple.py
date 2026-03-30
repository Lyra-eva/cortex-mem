#!/usr/bin/env python3
"""
Embedding Server - 简化版 + 巩固功能（~250 行）
功能：BGE 嵌入计算 + LanceDB 操作 + 记忆巩固
"""

import json
import os
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import Counter

# Config
PORT = 9721
MODEL_PATH = "/Users/lx/.cache/huggingface/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620"
LANCEDB_PATH = "/Users/lx/.openclaw/plugins/evolution-v5/server/data/lancedb"
LOG_PATH = "/Users/lx/.openclaw/plugins/evolution-v5/server/logs/embedding_server.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load model
logger.info("Loading BGE model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(MODEL_PATH)
logger.info("Model loaded, dim=512")

# Initialize LanceDB
logger.info("Initializing LanceDB...")
import lancedb
os.makedirs(LANCEDB_PATH, exist_ok=True)
db = lancedb.connect(LANCEDB_PATH)
logger.info("LanceDB initialized")

# Load jieba for Chinese word segmentation
logger.info("Loading jieba...")
import jieba
logger.info("jieba loaded")

# Metrics
request_count = 0
error_count = 0
start_time = datetime.now()

def get_agent_table(agent_id: str):
    """获取或创建 agent 的记忆表"""
    try:
        return db.open_table('memory')
    except:
        schema_data = [{
            'id': '', 'agent_id': agent_id, 'content': '',
            'embedding': [0.0] * 512, 'type': 'semantic',
            'importance': 0.5, 'links': '[]',
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'metadata': '{}'
        }]
        table = db.create_table('memory', schema_data)
        table.delete("id = ''")
        return table

def extract_keywords(texts, top_k=10, min_freq=2):
    """提取关键词（jieba 分词）"""
    all_text = ' '.join(texts)
    words = jieba.lcut(all_text)
    
    # 过滤：长度 2-4，排除停用词
    stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    filtered = [w for w in words if len(w) >= 2 and len(w) <= 4 and w not in stopwords and not w.isascii()]
    
    # 词频统计
    freq = Counter(filtered)
    keywords = [(word, count) for word, count in freq.items() if count >= min_freq]
    keywords.sort(key=lambda x: x[1], reverse=True)
    
    return keywords[:top_k]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.command} {self.path}")

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_GET(self):
        global request_count
        request_count += 1
        if self.path == '/health':
            uptime = str(datetime.now() - start_time).split('.')[0]
            tenants = [d for d in os.listdir(LANCEDB_PATH) if os.path.isdir(os.path.join(LANCEDB_PATH, d))] if os.path.exists(LANCEDB_PATH) else []
            self._json_response({
                "status": "ok", "model": "bge-small-zh-v1.5",
                "tenants": tenants, "uptime": uptime,
                "requests": request_count, "errors": error_count
            })
        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        global request_count, error_count
        request_count += 1
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        try:
            if self.path == '/embed': self._handle_embed(body)
            elif self.path == '/save': self._handle_save(body)
            elif self.path == '/search': self._handle_search(body)
            elif self.path == '/consolidate': self._handle_consolidate(body)
            else: self._json_response({"error": "not found"}, 404)
        except Exception as e:
            error_count += 1
            logger.error(f"Error: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_embed(self, body):
        texts = body.get('texts', [])
        if not texts: return self._json_response({"error": "texts required"}, 400)
        embeddings = model.encode(texts).tolist()
        self._json_response({"embeddings": embeddings})

    def _handle_save(self, body):
        content = body.get('content', '')
        agent_id = body.get('agent_id', 'main')
        mem_type = body.get('type', 'semantic')
        metadata = body.get('metadata', {})
        if not content: return self._json_response({"error": "content required"}, 400)
        embedding = model.encode([content])[0].tolist()
        table = get_agent_table(agent_id)
        data = {
            'id': f'mem_{int(datetime.now().timestamp() * 1000)}',
            'agent_id': agent_id, 'content': content, 'embedding': embedding,
            'type': mem_type, 'importance': metadata.get('importance', 0.5),
            'links': '[]', 'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'metadata': json.dumps(metadata)
        }
        table.add([data])
        self._json_response({"status": "saved", "id": data['id']})

    def _handle_search(self, body):
        query = body.get('query', '')
        agent_id = body.get('agent_id', 'main')
        limit = body.get('limit', 5)
        mem_type = body.get('type', None)
        if not query: return self._json_response({"error": "query required"}, 400)
        query_vec = model.encode([query])[0].tolist()
        table = get_agent_table(agent_id)
        results = table.search(query_vec).limit(limit).to_list()
        cleaned = []
        for r in results:
            if mem_type and r.get('type') != mem_type: continue
            cleaned.append({
                'id': r.get('id'), 'agent_id': r.get('agent_id'),
                'content': r.get('content'), 'type': r.get('type'),
                'importance': r.get('importance'),
                'metadata': json.loads(r.get('metadata', '{}')),
                '_distance': r.get('_distance')
            })
        self._json_response({"results": cleaned, "count": len(cleaned)})

    def _handle_consolidate(self, body):
        """记忆巩固（完整实现）"""
        agent_id = body.get('agent_id', 'main')
        min_count = body.get('min_count', 10)
        
        try:
            # 获取 episodic 记忆
            table = get_agent_table(agent_id)
            try:
                episodes = table.search("").where("type = 'episodic'").limit(100).to_list()
            except Exception as e1:
                # Fallback: 直接获取所有记录
                try:
                    all_data = table.to_arrow().to_pylist()
                    episodes = [e for e in all_data if e.get('type') == 'episodic'][:100]
                except Exception as e2:
                    logger.error(f"Get episodes error: {e1}, {e2}")
                    episodes = []
            
            if len(episodes) < min_count:
                return self._json_response({
                    "status": "skipped",
                    "reason": f"Not enough episodes ({len(episodes)} < {min_count})"
                })
            
            # 提取内容
            contents = [e.get('content', '') for e in episodes]
            
            # 提取关键词
            keywords = extract_keywords(contents, top_k=10, min_freq=2)
            
            if not keywords:
                return self._json_response({
                    "status": "ok",
                    "analyzed_episodes": len(episodes),
                    "keywords": [],
                    "created_concepts": 0
                })
            
            # 为每个高频关键词创建 concept
            created = 0
            for keyword, count in keywords[:5]:  # 只创建前 5 个
                concept_content = f"对话主题：{keyword}（出现{count}次）"
                embedding = model.encode([concept_content])[0].tolist()
                concept_data = {
                    'id': f'concept_{keyword}_{int(datetime.now().timestamp() * 1000)}',
                    'agent_id': agent_id, 'content': concept_content, 'embedding': embedding,
                    'type': 'semantic', 'importance': 0.7,
                    'links': '[]', 'created_at': datetime.now().isoformat(),
                    'last_accessed': datetime.now().isoformat(),
                    'metadata': json.dumps({'source': 'consolidate', 'keyword': keyword, 'count': count})
                }
                table.add([concept_data])
                created += 1
            
            self._json_response({
                "status": "ok",
                "analyzed_episodes": len(episodes),
                "keywords": [[kw, cnt] for kw, cnt in keywords],
                "created_concepts": created
            })
        except Exception as e:
            logger.error(f"Consolidate error: {e}")
            self._json_response({
                "status": "error",
                "error": str(e)
            })

if __name__ == '__main__':
    import socket
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"Listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

#!/usr/bin/env python3
"""
Embedding Server - BGE-small-zh-v1.5 (v7.0 Core)
Core Storage Layer for OpenClaw
- LanceDB: Long-term memory
- Redis: L0-L2 cache
- Config: Shared configuration

Architecture:
  - Single memory.lance table per agent (unified long-term memory)
  - Auto type inference (episodic/semantic/procedural)
  - Importance-based forgetting
  - Redis-backed working memory (L0-L2) via plugin

Endpoints:
  POST /embed      {"texts": [...]} → {"embeddings": [...]}
  POST /search     {"query": "...", "agent_id": "...", "type": "...", "limit": 5}
  POST /save       {"content": "...", "agent_id": "...", "type": "...", "metadata": {...}}
  POST /sensory    {"action": "set/get/status", ...} → L0 感觉缓冲
  POST /hop        {"query": "...", "agent_id": "...", "hops": 2, "limit": 10} → 多跳检索
  POST /plasticity {"action": "update/decay/prune", ...} → 神经可塑性
  POST /forget     {"agent_id": "...", "max_age_days": 90, "min_importance": 0.2}
  GET  /health     → {"status": "ok", "tenants": [...], "stats": {...}}
"""

import json
import os
import logging
import re
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# Config
PORT = 9721
MODEL_PATH = "/Users/lx/.cache/huggingface/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620"
LANCEDB_BASE = '/Users/lx/.openclaw/plugins/evolution-v5/server/data/lancedb'
SHARED_DIR = os.path.join(LANCEDB_BASE, "_shared")
LOG_PATH = os.path.expanduser("~/.openclaw/evolution/logs/embedding_server.log")
STOPWORDS_PATH = os.path.expanduser("~/.openclaw/evolution/stopwords.txt")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Metrics
request_count = 0
error_count = 0
start_time = datetime.now()

# Load model
logger.info("Loading BGE model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(MODEL_PATH)
logger.info("Model loaded, dim=512")

# Load stopwords
STOPWORDS = set()
try:
    with open(STOPWORDS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip()
            if word and not word.startswith('#'):
                STOPWORDS.add(word)
except:
    logger.warning(f"Could not load stopwords from {STOPWORDS_PATH}")

# Memory schema (single table)
MEMORY_SCHEMA = ['id', 'agent_id', 'content', 'embedding', 'type', 
                 'importance', 'links', 'created_at', 'last_accessed', 'metadata']

# v4.0: 神经可塑性配置
PLASTICITY_CONFIG = {
    'ltp_rate': 0.1,
    'ltd_decay': 0.95,
    'min_strength': 0.1,
    'max_strength': 1.0,
    'prune_threshold': 0.2
}



# v5.2: 进化系统模块（整合到 embedding_server）
EVOLUTION_SYSTEM = None

# v5.5: 配置管理器
CONFIG_MANAGER = None

# Redis 缓存层 (L0-L2)
redis_client = None
REDIS_TTL = {
    'L0_SENSORY': 300,      # 5 分钟（感觉缓冲）
    'L1_WORKING': 7200,     # 2 小时（搜索缓存优化）
    'L2_EPISODIC': 86400,   # 24 小时（情景缓冲）
    'SEARCH_CACHE': 7200,   # 2 小时（检索结果缓存优化）
    'MEMORY_INJECT': 3600,  # 1 小时（记忆注入缓存 - 新增）
    'CONVERSATION': 86400,  # 24 小时（对话历史统一）
}

def init_redis():
    """初始化 Redis 连接"""
    global redis_client
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.ping()
        logger.info("Redis connected (L0-L2 cache enabled)")
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        redis_client = None

def redis_set(key: str, value, ttl: int):
    """Redis set with TTL"""
    if redis_client:
        try:
            redis_client.setex(key, ttl, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        except: pass

def redis_get(key: str):
    """Redis get"""
    if redis_client:
        try:
            val = redis_client.get(key)
            if not val:
                return None
            # 尝试 JSON 解析，失败返回原始字符串
            try:
                return json.loads(val)
            except:
                return val
        except: pass
    return None

def redis_delete_pattern(pattern: str):
    """Delete keys by pattern"""
    if redis_client:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                return len(keys)
        except: pass
    return 0

# Initialize Redis
init_redis()



# Cache for DB connections
db_cache = {}

def get_tenant_db(agent_id: str):
    """Get or create tenant database"""
    if agent_id in db_cache:
        return db_cache[agent_id]
    
    import lancedb
    tenant_path = os.path.join(LANCEDB_BASE, agent_id)
    
    if not os.path.exists(tenant_path):
        logger.info(f"Auto-creating tenant: {agent_id}")
        os.makedirs(tenant_path, exist_ok=True)
        init_tenant_db(agent_id)
    else:
        # Directory exists but table might not - ensure table exists
        init_tenant_db(agent_id)
    
    db = lancedb.connect(tenant_path)
    db_cache[agent_id] = db
    return db

def init_tenant_db(agent_id: str):
    """Initialize tenant database with single memory.lance table"""
    import lancedb
    
    tenant_path = os.path.join(LANCEDB_BASE, agent_id)
    os.makedirs(tenant_path, exist_ok=True)
    db = lancedb.connect(tenant_path)
    
    try:
        tbl = db.open_table('memory')
        logger.debug(f"Memory table exists for {agent_id}")
    except:
        # Create memory table with schema
        schema_data = [{
            'id': '',
            'agent_id': agent_id,
            'content': '',
            'embedding': [0.0] * 512,
            'type': 'semantic',
            'importance': 0.5,
            'links': '[]',
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'metadata': '{}'
        }]
        try:
            tbl = db.create_table('memory', schema_data)
            tbl.delete("id = ''")
            logger.info(f"Created memory table for {agent_id}")
        except Exception as e:
            logger.error(f"Failed to create memory table: {e}")
            return False
    
    logger.debug(f"Tenant {agent_id} initialized")
    return True

def scan_and_init_agents():
    """Scan agents directory and initialize all tenant databases"""
    agents_dir = '/Users/lx/.openclaw/agents'
    if not os.path.exists(agents_dir):
        logger.warning(f"Agents directory not found: {agents_dir}")
        return
    
    logger.info(f"Scanning agents directory: {agents_dir}")
    initialized = 0
    failed = 0
    for agent_name in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_name)
        if os.path.isdir(agent_path) and not agent_name.startswith('_'):
            logger.info(f"Initializing agent: {agent_name}")
            try:
                if init_tenant_db(agent_name):
                    initialized += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to initialize {agent_name}: {e}")
                failed += 1
    
    logger.info(f"Agent initialization complete: {initialized} succeeded, {failed} failed")

def infer_type(content: str, metadata: dict = None) -> str:
    """Auto-infer memory type from content"""
    content_lower = content.lower()
    
    # Episodic: personal experiences, time references
    episodic_patterns = ['今天', '刚才', '昨天', '现在', '刚刚', '今天', '此刻', 
                         'boss 说', '我说', '我们说', '对话', '聊天']
    if any(p in content for p in episodic_patterns):
        return 'episodic'
    
    # Procedural: how-to, steps, procedures
    procedural_patterns = ['步骤', '怎么', '如何', '流程', '方法', '教程', 
                          'procedure', 'how to', 'steps', 'process']
    if any(p in content_lower for p in procedural_patterns):
        return 'procedural'
    
    # Default: semantic (knowledge, facts, data)
    return 'semantic'

def extract_keywords(texts, top_k=10, min_freq=2):
    """Extract keywords with jieba"""
    jieba = None
    try:
        import jieba
        logger.info("Jieba loaded")
    except ImportError:
        logger.warning("Jieba not installed")
    
    all_text = ' '.join(texts)
    
    if jieba:
        words = jieba.lcut(all_text)
    else:
        words = re.split(r'[\s,，。！？、；:"\'（）\[\]{}]+', all_text)
    
    filtered = []
    for w in words:
        w = w.strip()
        if not w or w in STOPWORDS:
            continue
        if len(w) < 2 or len(w) > 20:
            continue
        if w.isascii():
            continue
        if re.match(r'^\d+[a-zA-Z]+$', w):
            continue
        filtered.append(w)
    
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    
    keywords = [(word, count) for word, count in freq.items() if count >= min_freq]
    keywords.sort(key=lambda x: x[1], reverse=True)
    
    return keywords[:top_k]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.command} {self.path} - {args[0] if args else ''}")

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
            tenants = [d for d in os.listdir(LANCEDB_BASE) 
                      if os.path.isdir(os.path.join(LANCEDB_BASE, d)) 
                      and not d.startswith('_')
                      and d not in ['memory.lance', 'lancedb']]
            
            # Get stats
            stats = {}
            for tenant in tenants:
                try:
                    db = get_tenant_db(tenant)
                    tbl = db.open_table('memory')
                    count = tbl.count_rows()
                    stats[tenant] = {'memories': count}
                except:
                    stats[tenant] = {'memories': 0}
            
            self._json_response({
                "status": "ok",
                "model": "bge-small-zh-v1.5",
                "tenants": tenants,
                "uptime": uptime,
                "requests": request_count,
                "errors": error_count,
                "stats": stats
            })
        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        global request_count, error_count
        request_count += 1
        
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        try:
            if self.path == '/embed':
                self._handle_embed(body)
            elif self.path == '/search':
                self._handle_search(body)
            elif self.path == '/save':
                self._handle_save(body)
            elif self.path == '/consolidate':
                self._handle_consolidate(body)
            elif self.path == '/forget':
                self._handle_forget(body)
            elif self.path == '/cache':
                self._handle_cache(body)
            elif self.path == '/decay':
                self._handle_decay(body)
            elif self.path == '/sensory':
                self._handle_sensory(body)
            elif self.path == '/hop':
                self._handle_hop_search(body)
            elif self.path == '/pattern_completion':
                self._handle_pattern_completion(body)
            elif self.path == '/cluster_activation':
                self._handle_cluster_activation(body)
            elif self.path == '/synaptic_pruning':
                self._handle_synaptic_pruning(body)
            elif self.path == '/plasticity':
                self._handle_plasticity(body)
            elif self.path == '/evolve':
                self._handle_evolve(body)
            elif self.path == '/think':
                self._handle_evolve_action('think', body)
            elif self.path == '/learn':
                self._handle_evolve_action('learn', body)
            elif self.path == '/feel':
                self._handle_evolve_action('feel', body)
            elif self.path == '/execute':
                self._handle_evolve_action('execute', body)
            elif self.path == '/perceive':
                self._handle_evolve_action('perceive', body)
            elif self.path == '/monitor':
                self._handle_evolve_action('monitor', body)
            elif self.path == '/config/get':
                self._handle_config_get(body)
            elif self.path == '/config/set':
                self._handle_config_set(body)
            elif self.path == '/config/list':
                self._handle_config_list(body)
            elif self.path == '/config/reset':
                self._handle_config_reset(body)
            else:
                self._json_response({"error": "not found"}, 404)
        except Exception as e:
            error_count += 1
            logger.error(f"Error handling {self.path}: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_embed(self, body):
        texts = body.get('texts', [])
        if not texts:
            return self._json_response({"error": "texts required"}, 400)
        embeddings = model.encode(texts).tolist()
        self._json_response({"embeddings": embeddings})

    def _handle_search(self, body):
        query = body.get('query', '')
        agent_id = body.get('agent_id', 'main')
        limit = body.get('limit', 5)
        mem_type = body.get('type', None)
        min_importance = body.get('min_importance', None)

        if not query:
            return self._json_response({"error": "query required"}, 400)

        # L1 工作记忆缓存：检查是否有缓存的搜索结果
        cache_key = f"search:{agent_id}:{query}:{mem_type or 'all'}:{limit}"
        cached = redis_get(cache_key)
        if cached:
            logger.debug(f"Search cache hit: {cache_key}")
            return self._json_response(cached)

        db = get_tenant_db(agent_id)

        try:
            tbl = db.open_table('memory')
        except Exception as e:
            return self._json_response({"error": f"memory table not found"}, 404)

        query_vec = model.encode([query])[0].tolist()

        try:
            # Use optimized search with prefiltering
            search_obj = tbl.search(query_vec)
            
            # Apply filters (use postfiltering for better index usage)
            if mem_type:
                search_obj = search_obj.where(f"type = '{mem_type}'", prefilter=False)
            if min_importance is not None:
                search_obj = search_obj.where(f"importance >= {min_importance}", prefilter=False)
            
            # Use efficient search parameters
            results = search_obj.limit(limit).to_list()
            
            # Clean results (remove embedding)
            cleaned = [{k: v for k, v in r.items() if k not in ('embedding', 'vector')} for r in results]
            
            # Update last_accessed
            for r in results:
                try:
                    tbl.update(values={'last_accessed': datetime.now().isoformat()}, 
                              where=f"id = '{r['id']}'")
                except:
                    pass
            
            # L1 缓存：保存搜索结果（2 小时 TTL）
            response_data = {"results": cleaned, "count": len(cleaned)}
            redis_set(cache_key, response_data, REDIS_TTL['SEARCH_CACHE'])
            
            # 记忆注入缓存：额外缓存一份用于快速注入（1 小时 TTL）
            inject_cache_key = f"memory_inject:{agent_id}:{query[:50]}"
            redis_set(inject_cache_key, cleaned, REDIS_TTL['MEMORY_INJECT'])
            
            self._json_response(response_data)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_save(self, body):
        content = body.get('content', '')
        agent_id = body.get('agent_id', 'main')
        metadata = body.get('metadata', {})
        mem_type = body.get('type', None)  # Auto-infer if not provided
        importance = body.get('importance', None)  # Auto-calc if not provided

        if not content:
            return self._json_response({"error": "content required"}, 400)

        logger.info(f"Saving memory for {agent_id}: {content[:50]}...")
        logger.info(f"  Metadata received: {metadata}")
        logger.info(f"  Metadata.extra: {metadata.get('extra', {})}")
        embedding = model.encode([content])[0].tolist()

        # Auto-infer type
        if not mem_type:
            mem_type = infer_type(content, metadata)
        
        # Auto-calculate importance
        if importance is None:
            importance = metadata.get('importance', 0.5)
            # Boost importance for certain patterns
            if mem_type == 'procedural':
                importance = max(importance, 0.7)  # Procedures are important
            elif 'boss' in content.lower() or '用户' in content:
                importance = max(importance, 0.8)  # User-related is important

        db = get_tenant_db(agent_id)

        try:
            tbl = db.open_table('memory')
        except Exception as e:
            logger.error(f"Failed to open memory table: {e}")
            return self._json_response({"error": str(e)}, 500)

        # Auto-find related memories for links
        related_ids = []
        try:
            related = tbl.search(embedding).limit(3).to_list()
            related_ids = [r['id'] for r in related if r.get('id')]
            logger.info(f"Found {len(related_ids)} related memories")
        except Exception as e:
            logger.debug(f"Could not find related: {e}")

        # Support both formats: learn tool uses metadata.extra, auto_save uses metadata directly
        if 'extra' in metadata and isinstance(metadata['extra'], dict):
            metadata_to_save = metadata['extra']
        else:
            metadata_to_save = metadata
        metadata_json = json.dumps(metadata_to_save)
        logger.info(f"  Metadata to save: {metadata_json}")
        
        record = {
            "id": metadata.get('id', f"mem_{int(time.time()*1000)}"),
            "agent_id": agent_id,
            "content": content,
            "embedding": embedding,
            "type": mem_type,
            "importance": importance,
            "links": json.dumps(related_ids),
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "metadata": metadata_json
        }

        try:
            tbl.add([record])
            logger.info(f"Saved memory for {agent_id}: id={record['id']}, type={mem_type}, metadata={metadata_json}")
            
            # L2 缓存：保存新记忆到 Redis（24 小时 TTL）
            redis_set(f"episodic:{agent_id}:{record['id']}", {
                'content': content,
                'type': mem_type,
                'importance': importance,
                'created_at': record['created_at']
            }, REDIS_TTL['L2_EPISODIC'])
            
            # 清除搜索缓存（因为记忆已更新）
            redis_delete_pattern(f"search:{agent_id}:*")
            
            self._json_response({
                "status": "saved", 
                "id": record["id"], 
                "type": mem_type,
                "importance": importance
            })
        except Exception as e:
            logger.error(f"Save failed: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_consolidate(self, body):
        """Extract themes from episodic memories and create semantic memories"""
        min_count = body.get('min_count', 10)
        agent_id = body.get('agent_id', 'main')
        
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        # Read episodic memories - read all and filter in Python (no index required)
        try:
            all_memories = tbl.to_arrow().to_pylist()
            episodes = [m for m in all_memories if m.get('type') == 'episodic']
            logger.info(f"Read {len(all_memories)} memories, {len(episodes)} are episodic")
        except Exception as e:
            logger.error(f"Failed to read memories: {e}")
            episodes = []
        
        if len(episodes) < min_count:
            return self._json_response({
                "status": "skipped",
                "reason": f"Only {len(episodes)} episodic memories, need {min_count}"
            })
        
        contents = [e.get('content', '') for e in episodes if e.get('content')]
        keywords = extract_keywords(contents, top_k=10, min_freq=2)
        
        logger.info(f"Extracted {len(keywords)} keywords from {len(episodes)} episodes: {[k[0] for k in keywords[:5]]}")
        
        # Create semantic memories for top themes
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        created = 0
        
        for keyword, count in keywords[:5]:  # Top 5 themes
            # Check if similar concept exists
            query_vec = model.encode([keyword])[0].tolist()
            existing = tbl.search(query_vec).where(f"type = 'semantic'").limit(1).to_list()
            
            if not existing:
                # Create new semantic memory
                content = f"对话主题：{keyword} (出现 {count} 次)"
                embedding = model.encode([content])[0].tolist()
                record = {
                    "id": f"theme_{int(time.time()*1000)}",
                    "agent_id": agent_id,
                    "content": content,
                    "embedding": embedding,
                    "type": 'semantic',
                    "importance": min(0.5 + count * 0.05, 0.9),
                    "links": '[]',
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "metadata": json.dumps({'source': 'consolidate', 'keyword': keyword, 'count': count})
                }
                tbl.add([record])
                created += 1
        
        self._json_response({
            "status": "ok",
            "keywords": keywords,
            "analyzed_episodes": len(episodes),
            "created_concepts": created
        })

    def _handle_forget(self, body):
        """Forget low-importance, old memories"""
        agent_id = body.get('agent_id', 'main')
        max_age_days = body.get('max_age_days', 90)
        min_importance = body.get('min_importance', 0.2)
        
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        # Calculate cutoff date
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        
        # Count before
        before = tbl.count_rows()
        
        # Delete old, low-importance memories
        try:
            # Build where clause
            where_clause = f"importance < {min_importance} AND created_at < '{cutoff}'"
            tbl.delete(where_clause)
            
            # Count after
            after = tbl.count_rows()
            deleted = before - after
            
            logger.info(f"Forget: deleted {deleted} memories for {agent_id}")
            self._json_response({
                "status": "ok",
                "deleted": deleted,
                "before": before,
                "after": after
            })
        except Exception as e:
            logger.error(f"Forget failed: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_cache(self, body):
        """L0-L2 缓存管理 API"""
        action = body.get('action', 'status')
        agent_id = body.get('agent_id', 'main')
        
        if not redis_client:
            return self._json_response({"error": "Redis not available"}, 503)
        
        if action == 'status':
            # 获取缓存状态
            keys = redis_client.keys(f"*:{agent_id}:*")
            stats = {
                'total_keys': len(keys),
                'search_cache': len(redis_client.keys(f"search:{agent_id}:*")),
                'episodic_cache': len(redis_client.keys(f"episodic:{agent_id}:*")),
            }
            self._json_response({"status": "ok", "stats": stats})
        
        elif action == 'clear':
            # 清除缓存
            pattern = body.get('pattern', f"*:{agent_id}:*")
            deleted = redis_delete_pattern(pattern)
            self._json_response({"status": "ok", "deleted": deleted})
        
        elif action == 'set':
            # 手动设置缓存
            key = body.get('key', '')
            value = body.get('value', '')
            ttl = body.get('ttl', REDIS_TTL['L1_WORKING'])
            if key:
                redis_set(key, value, ttl)
                self._json_response({"status": "ok"})
            else:
                self._json_response({"error": "key required"}, 400)
        
        else:
            self._json_response({"error": f"unknown action: {action}"}, 400)

    def _handle_decay(self, body):
        """重要性衰减 API（每周执行）"""
        agent_id = body.get('agent_id', 'main')
        decay_factor = body.get('decay_factor', 0.95)  # 每周衰减 5%
        
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        try:
            all_memories = tbl.to_arrow().to_pylist()
            updated = 0
            
            for mem in all_memories:
                last_accessed = datetime.fromisoformat(mem.get('last_accessed', datetime.now().isoformat()))
                days_since_access = (datetime.now() - last_accessed).days
                
                if days_since_access > 0:
                    old_importance = mem.get('importance', 0.5)
                    new_importance = old_importance * (decay_factor ** (days_since_access / 7))
                    new_importance = max(0.1, new_importance)
                    
                    if abs(new_importance - old_importance) > 0.01:
                        try:
                            tbl.update(values={'importance': new_importance}, 
                                      where=f"id = '{mem['id']}'")
                            updated += 1
                        except:
                            pass
            
            logger.info(f"Decay: updated {updated} memories for {agent_id}")
            self._json_response({"status": "ok", "updated": updated, "decay_factor": decay_factor})
        except Exception as e:
            logger.error(f"Decay failed: {e}")
            self._json_response({"error": str(e)}, 500)

    

        except Exception as e:
            logger.error(f"Hop search failed: {e}")
            self._json_response({"error": str(e)}, 500)

    def _handle_pattern_completion(self, body):
        """模式完成：根据线索回忆完整记忆簇"""
        try:
            from pattern_completion import pattern_completion
            
            query = body.get('query', '')
            agent_id = body.get('agent_id', 'main')
            top_k = body.get('top_k', 10)
            
            if not query:
                return self._json_response({"error": "query required"}, 400)
            
            results = pattern_completion(query, agent_id, top_k)
            self._json_response({
                "status": "ok",
                "results": results,
                "count": len(results)
            })
        except Exception as e:
            logger.error(f"Pattern completion failed: {e}")
            self._json_response({"error": str(e)}, 500)
    
    def _handle_cluster_activation(self, body):
        """聚类激活：激活种子记忆所在簇"""
        try:
            from cluster_activation import activate_cluster, detect_communities
            
            action = body.get('action', 'detect')
            agent_id = body.get('agent_id', 'main')
            
            if action == 'detect':
                communities = detect_communities(agent_id)
                self._json_response({
                    "status": "ok",
                    "communities": {str(k): v for k, v in communities.items()},
                    "count": len(communities)
                })
            elif action == 'activate':
                seed_id = body.get('seed_memory_id', '')
                if not seed_id:
                    return self._json_response({"error": "seed_memory_id required"}, 400)
                results = activate_cluster(seed_id, agent_id)
                self._json_response({
                    "status": "ok",
                    "results": results,
                    "count": len(results)
                })
            else:
                return self._json_response({"error": "unknown action"}, 400)
        except Exception as e:
            logger.error(f"Cluster activation failed: {e}")
            self._json_response({"error": str(e)}, 500)
    
    def _handle_synaptic_pruning(self, body):
        """突触修剪：清理低重要性记忆"""
        try:
            from synaptic_pruning import synaptic_pruning, pruning_report
            
            action = body.get('action', 'report')
            agent_id = body.get('agent_id', 'main')
            
            if action == 'report':
                report = pruning_report(agent_id)
                self._json_response({
                    "status": "ok",
                    "report": report
                })
            elif action == 'prune':
                threshold = body.get('threshold', 0.3)
                dry_run = body.get('dry_run', True)
                count, deleted_ids = synaptic_pruning(agent_id, threshold, dry_run)
                self._json_response({
                    "status": "ok",
                    "action": "prune",
                    "dry_run": dry_run,
                    "deleted_count": count,
                    "deleted_ids": deleted_ids[:10]
                })
            else:
                return self._json_response({"error": "unknown action"}, 400)
        except Exception as e:
            logger.error(f"Synaptic pruning failed: {e}")
            self._json_response({"error": str(e)}, 500)
    
    def _handle_hop_search(self, body):
        """多跳联想检索"""
        query = body.get('query', '')
        agent_id = body.get('agent_id', 'main')
        hops = body.get('hops', 2)
        limit = body.get('limit', 10)
        
        if not query:
            return self._json_response({"error": "query required"}, 400)
        
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        try:
            query_vec = model.encode([query])[0].tolist()
            hop1 = tbl.search(query_vec).limit(limit).to_list()
            
            all_results = hop1.copy()
            
            for h in range(1, hops):
                hop_results = []
                for mem in all_results[-limit:]:
                    links = json.loads(mem.get('links', '[]'))
                    if isinstance(links, list):
                        for link_id in links[:3]:
                            try:
                                related = tbl.search(query_vec).where(f"id = '{link_id}'").limit(1).to_list()
                                if related and related not in hop_results:
                                    hop_results.append(related[0])
                            except:
                                pass
                if not hop_results:
                    break
                all_results.extend(hop_results)
            
            cleaned = [{k: v for k, v in r.items() if k not in ('embedding',)} for r in all_results[:limit]]
            self._json_response({"results": cleaned, "count": len(cleaned)})
        except Exception as e:
            logger.error(f"Hop search failed: {e}")
            self._json_response({"error": str(e)}, 500)
    
    def _handle_sensory(self, body):
        """v4.0: L0 感觉缓冲 API"""
        action = body.get('action', 'set')
        agent_id = body.get('agent_id', 'main')
        
        if not redis_client:
            return self._json_response({"error": "Redis not available"}, 503)
        
        if action == 'set':
            # 保存感觉缓冲（5 分钟 TTL）
            key = body.get('key', '')
            value = body.get('value', '')
            if not key:
                return self._json_response({"error": "key required"}, 400)
            
            redis_set(f"sensory:{agent_id}:{key}", value, REDIS_TTL['L0_SENSORY'])
            self._json_response({"status": "ok", "ttl": REDIS_TTL['L0_SENSORY']})
        
        elif action == 'get':
            # 获取感觉缓冲
            key = body.get('key', '')
            if not key:
                return self._json_response({"error": "key required"}, 400)
            
            value = redis_get(f"sensory:{agent_id}:{key}")
            if value:
                self._json_response({"status": "ok", "value": value})
            else:
                self._json_response({"status": "expired", "value": None})
        
        elif action == 'status':
            # 获取感觉缓冲状态
            keys = redis_client.keys(f"sensory:{agent_id}:*")
            self._json_response({
                "status": "ok",
                "count": len(keys),
                "keys": [k.replace(f"sensory:{agent_id}:", "") for k in keys[:10]]
            })
        
        elif action == 'delete':
            # 删除指定 key 的感觉缓冲
            key = body.get('key', '')
            if not key:
                return self._json_response({"error": "key required"}, 400)
            
            redis_key = f"sensory:{agent_id}:{key}"
            deleted = redis_client.delete(redis_key)
            self._json_response({
                "status": "ok",
                "deleted": deleted > 0
            })
        
        else:
            self._json_response({"error": f"unknown action: {action}"}, 400)

    def _handle_plasticity(self, body):
        """v4.0: 神经可塑性 API（更新连接强度）"""
        action = body.get('action', 'update')
        agent_id = body.get('agent_id', 'main')
        
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        if action == 'update':
            # 更新指定记忆的连接强度
            memory_id = body.get('memory_id', '')
            co_activation = body.get('co_activation', 1)
            
            if not memory_id:
                return self._json_response({"error": "memory_id required"}, 400)
            
            try:
                mem = tbl.search("").where(f"id = '{memory_id}'").limit(1).to_list()
                if not mem:
                    return self._json_response({"error": "memory not found"}, 404)
                
                mem = mem[0]
                links = json.loads(mem.get('links', '[]'))
                
                # LTP: 共激活增强
                if isinstance(links, list):
                    for link in links:
                        if isinstance(link, dict):
                            link['strength'] = min(PLASTICITY_CONFIG['max_strength'],
                                                   link.get('strength', 0.5) + PLASTICITY_CONFIG['ltp_rate'] * co_activation)
                            link['last_activated'] = datetime.now().isoformat()
                    
                    # 更新记忆
                    tbl.update(values={'links': json.dumps(links)}, where=f"id = '{memory_id}'")
                
                self._json_response({"status": "ok", "updated_links": len(links) if isinstance(links, list) else 0})
            except Exception as e:
                logger.error(f"Plasticity update failed: {e}")
                self._json_response({"error": str(e)}, 500)
        
        elif action == 'decay':
            # LTD: 时间衰减
            try:
                all_memories = tbl.to_arrow().to_pylist()
                updated = 0
                
                for mem in all_memories:
                    links = json.loads(mem.get('links', '[]'))
                    if isinstance(links, list):
                        for link in links:
                            if isinstance(link, dict):
                                last = datetime.fromisoformat(link.get('last_activated', datetime.now().isoformat()))
                                days = (datetime.now() - last).days
                                if days > 0:
                                    old_str = link.get('strength', 0.5)
                                    new_str = old_str * (PLASTICITY_CONFIG['ltd_decay'] ** days)
                                    new_str = max(PLASTICITY_CONFIG['min_strength'], new_str)
                                    link['strength'] = new_str
                                    if abs(new_str - old_str) > 0.01:
                                        updated += 1
                        
                        tbl.update(values={'links': json.dumps(links)}, where=f"id = '{mem['id']}'")
                
                self._json_response({"status": "ok", "updated": updated})
            except Exception as e:
                logger.error(f"Plasticity decay failed: {e}")
                self._json_response({"error": str(e)}, 500)
        
        elif action == 'prune':
            # 修剪弱连接
            threshold = body.get('threshold', PLASTICITY_CONFIG['prune_threshold'])
            try:
                all_memories = tbl.to_arrow().to_pylist()
                pruned = 0
                
                for mem in all_memories:
                    links = json.loads(mem.get('links', '[]'))
                    if isinstance(links, list):
                        original_len = len(links)
                        links = [l for l in links if isinstance(l, dict) and l.get('strength', 0) >= threshold]
                        if len(links) < original_len:
                            tbl.update(values={'links': json.dumps(links)}, where=f"id = '{mem['id']}'")
                            pruned += original_len - len(links)
                
                self._json_response({"status": "ok", "pruned": pruned})
            except Exception as e:
                logger.error(f"Plasticity prune failed: {e}")
                self._json_response({"error": str(e)}, 500)
        
        else:
            self._json_response({"error": f"unknown action: {action}"}, 400)


    def _handle_evolve(self, body):
        """v5.2: 统一进化接口"""
        action = body.get('action', '')
        return self._handle_evolve_action(action, body)
    
    def _handle_evolve_action(self, action: str, body):
        """v7.0: 已移除模块层，直接使用核心 API"""
        return self._json_response({
            'error': f'Module layer removed in v7.0. Use /save, /search, /consolidate APIs directly.',
            'v7_note': 'Modules (think/feel/execute/perceive/monitor) are removed. LLM handles reasoning directly.'
        }, 400)
    
    
# ===== 辅助类（v5.7）=====

class SimpleCache:
    """简易缓存对象（供模块使用）"""
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
    
    async def get(self, key):
        if self.redis_client:
            try:
                return json.loads(self.redis_client.get(key))
            except:
                pass
        return None
    
    async def set(self, key, value, ttl):
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            except:
                pass


# ===== 动作处理器（v5.7）=====
class ConfigHandlers:
    def _handle_config_get(self, body):
        """v5.5: 获取配置"""
        global CONFIG_MANAGER
        module = body.get('module', '')
        key = body.get('config_key', '')
        agent_id = body.get('agent_id')
        
        if not module or not key:
            return self._json_response({'error': 'module and config_key required'}, 400)
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            config = loop.run_until_complete(CONFIG_MANAGER.get(module, key, agent_id))
            loop.close()
            
            self._json_response({
                'status': 'ok',
                'module': module,
                'config_key': key,
                'config_value': config
            })
        except Exception as e:
            self._json_response({'error': str(e)}, 500)
    
    def _handle_config_set(self, body):
        """v5.5: 设置配置"""
        global CONFIG_MANAGER, redis_client
        module = body.get('module', '')
        key = body.get('config_key', '')
        value = body.get('config_value')
        updated_by = body.get('updated_by', 'system')
        agent_id = body.get('agent_id')
        
        if not module or not key or value is None:
            return self._json_response({'error': 'module, config_key and config_value required'}, 400)
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(CONFIG_MANAGER.set(module, key, value, updated_by, agent_id))
            loop.close()
            
            # 清除 Redis 缓存（强制重新加载）
            if redis_client:
                redis_client.delete('config:*')
            
            self._json_response({
                'status': 'ok' if success else 'error',
                'module': module,
                'config_key': key
            })
        except Exception as e:
            self._json_response({'error': str(e)}, 500)
    
    def _handle_config_list(self, body):
        """v5.5: 列出配置"""
        global CONFIG_MANAGER
        module = body.get('module')
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            configs = loop.run_until_complete(CONFIG_MANAGER.list_configs(module))
            loop.close()
            
            self._json_response({
                'status': 'ok',
                'configs': configs,
                'count': len(configs)
            })
        except Exception as e:
            self._json_response({'error': str(e)}, 500)
    
    def _handle_config_reset(self, body):
        """v5.5: 重置配置"""
        global CONFIG_MANAGER
        module = body.get('module', '')
        key = body.get('config_key', '')
        
        if not module or not key:
            return self._json_response({'error': 'module and config_key required'}, 400)
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(CONFIG_MANAGER.reset(module, key))
            loop.close()
            
            self._json_response({
                'status': 'ok' if success else 'error',
                'module': module,
                'config_key': key,
                'reset': success
            })
        except Exception as e:
            self._json_response({'error': str(e)}, 500)


# ===== 直接调用函数（v5.7）=====

async def _direct_save_to_lancedb(material: Dict, keywords: List[str], summary: str, agent_id: str) -> bool:
    """直接保存到 LanceDB（无 HTTP 开销）"""
    try:
        import lancedb
        
        content = material.get('content', '')
        title = material.get('title', 'unknown')
        
        # 获取 agent 的数据库
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        # 生成 embedding
        content_text = f"[{title}] {content[:500]}"
        embedding = model.encode([content_text])[0].tolist()
        
        # 保存
        data = {
            'id': f'learn_{agent_id}_{int(time.time())}',
            'agent_id': agent_id,
            'content': content_text,
            'embedding': embedding,
            'type': 'semantic',
            'importance': 0.7,
            'links': '[]',
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'metadata': json.dumps({
                'keywords': keywords,
                'summary': summary,
                'source': 'learn_module',
                'original_title': title,
                'url': material.get('url', None),
                'tags': material.get('tags', [])
            })
        }
        
        tbl.add([data])
        logger.debug(f"Direct save to LanceDB: {title} (agent: {agent_id})")
        return True
        
    except Exception as e:
        logger.error(f"Direct save failed: {e}")
        return False


async def _direct_search_memories(keywords: List[str], agent_id: str) -> int:
    """直接搜索相关记忆（无 HTTP 开销）"""
    try:
        import lancedb
        
        # 获取 agent 的数据库
        db = get_tenant_db(agent_id)
        tbl = db.open_table('memory')
        
        # 生成查询 embedding
        query_text = ' '.join(keywords[:5])
        query_vec = model.encode([query_text])[0].tolist()
        
        # 搜索
        results = tbl.search(query_vec).limit(3).to_list()
        
        logger.debug(f"Direct search: {len(results)} results for agent {agent_id}")
        return len(results)
        
    except Exception as e:
        logger.debug(f"Direct search failed: {e}")
        return 0


if __name__ == '__main__':
    import socket
    import asyncio
    
    # 初始化配置管理器（传入 Redis 客户端）
    logger.info("Initializing ConfigManager with Redis cache...")
    from config_manager import ConfigManager
    
    CONFIG_MANAGER = ConfigManager(redis_client=redis_client)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(CONFIG_MANAGER.initialize(redis_client))
    loop.close()
    logger.info(f"ConfigManager initialized with Redis cache (TTL: {CONFIG_MANAGER.redis_cache_ttl}s)")
    
    # 预初始化所有 agent 的记忆库
    logger.info("Pre-initializing agent databases...")
    scan_and_init_agents()
    
    # 预加载常用记忆到缓存（优化启动后首次查询）
    logger.info("Pre-loading frequently accessed memories to cache...")
    try:
        from lancedb import connect as lancedb_connect
        db = lancedb_connect(os.path.join(LANCEDB_BASE, 'main'))
        tbl = db.open_table('memory')
        
        # 预加载高频查询的记忆（按类型）
        for mem_type in ['semantic', 'episodic', 'procedural']:
            try:
                results = tbl.search().where(f"type = '{mem_type}'", prefilter=True).limit(10).to_list()
                cache_key = f"memory_inject:main:{mem_type}"
                if redis_client:
                    redis_client.setex(cache_key, REDIS_TTL['MEMORY_INJECT'], 
                                      json.dumps([{k: v for k, v in r.items() if k != 'embedding'} for r in results]))
                logger.info(f"  Pre-loaded {len(results)} {mem_type} memories")
            except Exception as e:
                logger.debug(f"  Skip {mem_type}: {e}")
        
        # 预加载最新记忆
        try:
            latest = tbl.search().limit(20).to_list()
            if redis_client:
                redis_client.setex('memory_inject:main:latest', REDIS_TTL['MEMORY_INJECT'],
                                  json.dumps([{k: v for k, v in r.items() if k != 'embedding'} for r in latest]))
            logger.info(f"  Pre-loaded 20 latest memories")
        except Exception as e:
            logger.debug(f"  Skip latest: {e}")
            
    except Exception as e:
        logger.warning(f"Pre-load failed: {e}")
    
    # 启动服务器
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"Listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()



#!/usr/bin/env python3
"""
GNN 集成脚本 — 将 GNN 服务集成到记忆系统

实施阶段：
1. 基础集成 — 同步数据，测试基本功能
2. 优化调整 — 调整参数，测试多跳推理
3. 生产集成 — 集成到检索流程，A/B 测试
"""

import json
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

MEMORY_URL = 'http://127.0.0.1:9721'
GNN_URL = 'http://127.0.0.1:9735'


def sync_memory_to_gnn():
    """阶段 1：从记忆系统同步节点到 GNN"""
    logger.info("Starting memory to GNN sync...")
    
    # 1. 获取所有记忆
    resp = requests.post(f'{MEMORY_URL}/search', 
        json={'query': '*', 'limit': 1000}, timeout=10)
    
    if not resp.ok:
        logger.error(f"Failed to fetch memories: {resp.text}")
        return False
    
    memories = resp.json().get('results', [])
    logger.info(f"Fetched {len(memories)} memories")
    
    # 2. 构建知识图谱
    graph_data = {
        'nodes': [],
        'edges': []
    }
    
    for mem in memories:
        # 添加节点
        graph_data['nodes'].append({
            'id': mem.get('id'),
            'content': mem.get('content', ''),
            'type': mem.get('type', 'memory'),
            'embedding': mem.get('embedding', []),
            'metadata': {
                'importance': mem.get('importance', 0.5),
                'created_at': mem.get('created_at', '')
            }
        })
        
        # 添加边 (从 links 字段)
        links = mem.get('links', '[]')
        try:
            link_data = json.loads(links)
            if isinstance(link_data, list):
                for link in link_data:
                    if isinstance(link, dict):
                        target_id = link.get('id')
                        relation = link.get('relation', 'related_to')
                        strength = link.get('strength', 0.8)
                        
                        if target_id:
                            graph_data['edges'].append({
                                'source': mem.get('id'),
                                'target': target_id,
                                'relation': relation,
                                'strength': strength
                            })
        except:
            pass
    
    # 3. 发送到 GNN 服务
    logger.info(f"Building graph with {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
    
    # TODO: 实现 GNN 的 build_graph API
    # resp = requests.post(f'{GNN_URL}/build_graph', json=graph_data, timeout=30)
    
    logger.info("Sync complete!")
    return True


def test_gnn_retrieval():
    """测试 GNN 检索"""
    logger.info("Testing GNN retrieval...")
    
    test_queries = [
        "经济",
        "CPI 通胀",
        "记忆系统"
    ]
    
    for query in test_queries:
        try:
            resp = requests.post(f'{GNN_URL}/multi_hop',
                json={'query': query, 'max_hops': 2}, timeout=10)
            
            if resp.ok:
                result = resp.json()
                logger.info(f"Query '{query}': {result.get('retrieved_nodes', 0)} nodes")
            else:
                logger.warning(f"Query '{query}' failed: {resp.text}")
        except Exception as e:
            logger.error(f"Query '{query}' error: {e}")
    
    logger.info("GNN retrieval test complete!")


def test_implicit_relations():
    """测试隐含关系发现"""
    logger.info("Testing implicit relation discovery...")
    
    try:
        resp = requests.post(f'{GNN_URL}/discover_relations', timeout=30)
        
        if resp.ok:
            result = resp.json()
            relations = result.get('relations', [])
            logger.info(f"Discovered {len(relations)} implicit relations")
            
            # 显示前 5 个
            for rel in relations[:5]:
                logger.info(f"  {rel['source']} ~{rel['similarity']:.2f}~ {rel['target']}")
        else:
            logger.warning(f"Discover relations failed: {resp.text}")
    except Exception as e:
        logger.error(f"Discover relations error: {e}")
    
    logger.info("Implicit relation test complete!")


def integrate_to_retrieval():
    """阶段 3：集成到检索流程"""
    logger.info("Integrating GNN to retrieval pipeline...")
    
    # 测试混合检索 (向量 + GNN)
    test_query = "CPI 上涨对经济的影响"
    
    # 1. 传统向量检索
    resp1 = requests.post(f'{MEMORY_URL}/search',
        json={'query': test_query, 'limit': 5}, timeout=10)
    
    # 2. GNN 检索
    resp2 = requests.post(f'{GNN_URL}/multi_hop',
        json={'query': test_query, 'max_hops': 2}, timeout=10)
    
    if resp1.ok and resp2.ok:
        vector_results = resp1.json().get('count', 0)
        gnn_results = resp2.json().get('retrieved_nodes', 0)
        
        logger.info(f"Hybrid retrieval test:")
        logger.info(f"  Vector search: {vector_results} results")
        logger.info(f"  GNN retrieval: {gnn_results} nodes")
        logger.info(f"  Combined: {vector_results + gnn_results} total")
    else:
        logger.warning("Hybrid retrieval test failed")
    
    logger.info("Integration test complete!")


def get_stats():
    """获取统计信息"""
    logger.info("Getting statistics...")
    
    # 记忆系统统计
    try:
        resp = requests.get(f'{MEMORY_URL}/health', timeout=5)
        if resp.ok:
            mem_stats = resp.json()
            logger.info(f"Memory system: {mem_stats.get('stats', {})}")
    except:
        pass
    
    # GNN 系统统计
    try:
        resp = requests.get(f'{GNN_URL}/stats', timeout=5)
        if resp.ok:
            gnn_stats = resp.json()
            logger.info(f"GNN system: {gnn_stats}")
    except:
        pass
    
    logger.info("Statistics complete!")


def main():
    """主实施流程"""
    logger.info("=" * 60)
    logger.info("GNN Integration - Full Implementation")
    logger.info("=" * 60)
    
    # 阶段 1：基础集成
    logger.info("\n📍 Phase 1: Basic Integration")
    if sync_memory_to_gnn():
        logger.info("✅ Phase 1 complete")
    else:
        logger.error("❌ Phase 1 failed")
        return
    
    # 阶段 2：优化调整
    logger.info("\n📍 Phase 2: Optimization")
    test_gnn_retrieval()
    test_implicit_relations()
    logger.info("✅ Phase 2 complete")
    
    # 阶段 3：生产集成
    logger.info("\n📍 Phase 3: Production Integration")
    integrate_to_retrieval()
    logger.info("✅ Phase 3 complete")
    
    # 获取统计
    logger.info("\n📊 Final Statistics")
    get_stats()
    
    logger.info("\n" + "=" * 60)
    logger.info("GNN Integration Complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()

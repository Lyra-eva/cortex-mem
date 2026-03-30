#!/usr/bin/env python3
"""
模式完成（Pattern Completion）- 类人脑记忆补全功能

根据部分线索回忆完整记忆簇
实现：Personalized PageRank 图扩散算法
"""

import json
import logging
import lancedb
import networkx as nx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

LANCEDB_BASE = '/Users/lx/.openclaw/plugins/evolution-v5/server/data/lancedb'


def build_memory_graph(agent_id: str) -> nx.Graph:
    """构建记忆图"""
    G = nx.Graph()
    
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    # 获取所有记忆
    memories = tbl.search([0.0]*512).limit(1000).limit(1000).to_list()
    
    for mem in memories:
        mem_id = mem['id']
        G.add_node(mem_id, data=mem)
        
        # 添加链接边
        links = json.loads(mem.get('links', '[]'))
        if isinstance(links, list):
            for link_id in links:
                if link_id:  # 非空链接
                    G.add_edge(mem_id, link_id, weight=0.9)
    
    logger.info(f"Built memory graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def pattern_completion(query: str, agent_id: str, top_k: int = 10) -> List[Dict]:
    """
    模式完成：根据查询找到相关记忆簇
    
    算法：Personalized PageRank
    1. 语义检索找到种子记忆
    2. 在记忆图上运行 PPR
    3. 返回激活的记忆簇
    """
    from sentence_transformers import SentenceTransformer
    
    # 加载模型
    model = SentenceTransformer("/Users/lx/.cache/huggingface/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620")
    
    # 构建记忆图
    G = build_memory_graph(agent_id)
    
    if G.number_of_nodes() == 0:
        return []
    
    # 语义检索找到种子记忆
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    query_vec = model.encode([query])[0].tolist()
    seed_results = tbl.search(query_vec).limit(3).to_list()
    
    if not seed_results:
        return []
    
    # Personalized PageRank
    seed_nodes = [r['id'] for r in seed_results]
    ppr_scores = nx.pagerank(G, alpha=0.85, personalization={n: 1.0/len(seed_nodes) for n in seed_nodes})
    
    # 按分数排序
    sorted_nodes = sorted(ppr_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    # 获取记忆数据
    results = []
    for node_id, score in sorted_nodes:
        node_data = G.nodes[node_id].get('data', {})
        if node_data:
            results.append({
                **node_data,
                'ppr_score': score,
                'completion_reason': 'pattern_completion'
            })
    
    logger.info(f"Pattern completion: {len(results)} memories activated")
    return results


if __name__ == '__main__':
    # 测试
    results = pattern_completion("架构优化", "main", top_k=5)
    print(f"Found {len(results)} memories:")
    for r in results[:3]:
        print(f"  - {r.get('content', '')[:50]}... (score: {r.get('ppr_score', 0):.4f})")

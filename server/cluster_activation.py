#!/usr/bin/env python3
"""
聚类激活（Cluster Activation）- 类人脑记忆簇唤醒功能

激活相关记忆簇（社区发现）
实现：Louvain 算法
"""

import json
import logging
import lancedb
import networkx as nx
import community as community_louvain
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

LANCEDB_BASE = '/Users/lx/.openclaw/plugins/evolution-v5/server/data/lancedb'


def detect_communities(agent_id: str) -> Dict[str, List[str]]:
    """
    检测记忆社区（记忆簇）
    
    算法：Louvain 社区发现
    返回：{community_id: [memory_ids]}
    """
    # 构建记忆图
    G = build_memory_graph(agent_id)
    
    if G.number_of_nodes() < 2:
        logger.warning("Not enough nodes for community detection")
        return {}
    
    # Louvain 社区发现
    partition = community_louvain.best_partition(G, random_state=42)
    
    # 按社区分组
    communities = {}
    for node_id, comm_id in partition.items():
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(node_id)
    
    logger.info(f"Detected {len(communities)} communities")
    for comm_id, members in communities.items():
        logger.info(f"  Community {comm_id}: {len(members)} memories")
    
    return communities


def activate_cluster(seed_memory_id: str, agent_id: str) -> List[Dict]:
    """
    激活种子记忆所在的整个簇
    
    1. 找到种子记忆所属社区
    2. 返回该社区所有记忆
    """
    communities = detect_communities(agent_id)
    
    if not communities:
        return []
    
    # 找到种子记忆所属社区
    seed_community = None
    for comm_id, members in communities.items():
        if seed_memory_id in members:
            seed_community = comm_id
            break
    
    if seed_community is None:
        return []
    
    # 获取社区所有记忆
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    member_ids = communities[seed_community]
    results = []
    
    for mem_id in member_ids:
        try:
            mem = tbl.search([0.0]*512).limit(1000).where(f"id = '{mem_id}'").limit(1).to_list()
            if mem:
                results.append({
                    **mem[0],
                    'community_id': seed_community,
                    'cluster_size': len(member_ids),
                    'activation_reason': 'cluster_activation'
                })
        except Exception as e:
            logger.warning(f"Failed to get memory {mem_id}: {e}")
    
    logger.info(f"Activated cluster: {len(results)} memories in community {seed_community}")
    return results


def build_memory_graph(agent_id: str) -> nx.Graph:
    """构建记忆图（复用）"""
    G = nx.Graph()
    
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    memories = tbl.search([0.0]*512).limit(1000).limit(1000).to_list()
    
    for mem in memories:
        mem_id = mem['id']
        G.add_node(mem_id, data=mem)
        
        links = json.loads(mem.get('links', '[]'))
        if isinstance(links, list):
            for link_id in links:
                if link_id:
                    G.add_edge(mem_id, link_id, weight=0.9)
    
    return G


if __name__ == '__main__':
    # 测试
    communities = detect_communities("main")
    print(f"Found {len(communities)} communities:")
    for comm_id, members in list(communities.items())[:3]:
        print(f"  Community {comm_id}: {len(members)} memories")
    
    if communities:
        first_comm = list(communities.keys())[0]
        first_member = communities[first_comm][0]
        results = activate_cluster(first_member, "main")
        print(f"\nActivated {len(results)} memories from cluster")

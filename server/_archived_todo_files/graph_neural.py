#!/usr/bin/env python3
"""
图神经网络增强模块 — GNN 知识图谱推理

核心功能：
1. 知识图谱构建 (节点 + 边)
2. GraphSAGE 节点编码
3. 图注意力检索
4. 多跳推理
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """知识图谱数据结构"""
    
    def __init__(self):
        # 节点：memory_id → node_data
        self.nodes: Dict[str, Dict] = {}
        
        # 边：(source_id, target_id) → edge_data
        self.edges: Dict[Tuple[str, str], Dict] = {}
        
        # 邻接表：node_id → [(neighbor_id, relation_type)]
        self.adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # 节点特征缓存
        self.node_features: Dict[str, np.ndarray] = {}
        
        logger.info("KnowledgeGraph initialized")
    
    def add_node(self, memory_id: str, content: str, node_type: str = 'memory', 
                 embedding: List[float] = None, metadata: Dict = None):
        """添加节点"""
        self.nodes[memory_id] = {
            'id': memory_id,
            'content': content,
            'type': node_type,
            'embedding': np.array(embedding) if embedding is not None else None,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        logger.info(f"Added node: {memory_id}")
    
    def add_edge(self, source_id: str, target_id: str, relation: str, 
                 strength: float = 0.8, metadata: Dict = None):
        """添加边"""
        edge_key = (source_id, target_id)
        
        self.edges[edge_key] = {
            'source': source_id,
            'target': target_id,
            'relation': relation,
            'strength': strength,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
        # 更新邻接表
        self.adjacency[source_id].append((target_id, relation))
        
        logger.info(f"Added edge: {source_id} -[{relation}]-> {target_id}")
    
    def get_neighbors(self, node_id: str, hops: int = 1) -> List[Dict]:
        """获取邻居节点 (支持多跳)"""
        visited = {node_id}
        queue = [(node_id, 0)]
        neighbors = []
        
        while queue:
            current_id, current_hop = queue.pop(0)
            
            if current_hop >= hops:
                continue
            
            for neighbor_id, relation in self.adjacency.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor_data = self.nodes.get(neighbor_id, {})
                    neighbor_data['_relation'] = relation
                    neighbor_data['_hop'] = current_hop + 1
                    neighbors.append(neighbor_data)
                    queue.append((neighbor_id, current_hop + 1))
        
        return neighbors
    
    def get_subgraph(self, seed_nodes: List[str], hops: int = 2) -> 'KnowledgeGraph':
        """获取子图 (用于 GNN 推理)"""
        subgraph = KnowledgeGraph()
        
        # 收集相关节点
        all_nodes = set(seed_nodes)
        for node_id in seed_nodes:
            neighbors = self.get_neighbors(node_id, hops)
            all_nodes.update(n['id'] for n in neighbors)
        
        # 添加节点到子图
        for node_id in all_nodes:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                subgraph.add_node(
                    node_id,
                    node['content'],
                    node['type'],
                    node.get('embedding'),
                    node.get('metadata')
                )
        
        # 添加相关边
        for (src, tgt), edge_data in self.edges.items():
            if src in all_nodes and tgt in all_nodes:
                subgraph.add_edge(src, tgt, edge_data['relation'], 
                                 edge_data['strength'], edge_data['metadata'])
        
        logger.info(f"Extracted subgraph: {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
        return subgraph
    
    def get_stats(self) -> Dict:
        """获取图统计信息"""
        return {
            'num_nodes': len(self.nodes),
            'num_edges': len(self.edges),
            'avg_degree': sum(len(neighbors) for neighbors in self.adjacency.values()) / max(1, len(self.nodes)),
            'relation_types': list(set(edge['relation'] for edge in self.edges.values()))
        }


class GraphSAGE:
    """GraphSAGE 图神经网络编码器"""
    
    def __init__(self, input_dim: int = 512, hidden_dim: int = 256, 
                 num_layers: int = 2, num_neighbors: int = 10):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_neighbors = num_neighbors
        
        # 简化版权重矩阵 (实际应使用 PyTorch)
        self.weights = self._init_weights()
        
        logger.info(f"GraphSAGE initialized: {input_dim}→{hidden_dim}, {num_layers} layers")
    
    def _init_weights(self) -> List[np.ndarray]:
        """初始化权重"""
        weights = []
        
        # 第一层：input_dim * 2 (self + neighbors) → hidden_dim
        weights.append(np.random.randn(self.hidden_dim, self.input_dim * 2) * 0.1)
        
        # 后续层：hidden_dim * 2 → hidden_dim
        for i in range(1, self.num_layers):
            weights.append(np.random.randn(self.hidden_dim, self.hidden_dim * 2) * 0.1)
        
        return weights
    
    def encode(self, graph: KnowledgeGraph, node_ids: List[str]) -> Dict[str, np.ndarray]:
        """
        编码节点
        
        Args:
            graph: 知识图谱
            node_ids: 要编码的节点 ID 列表
        
        Returns:
            node_id → embedding
        """
        node_embeddings = {}
        
        # 初始化节点特征
        for node_id in node_ids:
            node = graph.nodes.get(node_id, {})
            if node.get('embedding') is not None:
                node_embeddings[node_id] = node['embedding'][:self.input_dim]  # 确保维度匹配
            else:
                node_embeddings[node_id] = np.random.randn(self.input_dim) * 0.1
        
        # GraphSAGE 消息传递
        for layer in range(self.num_layers):
            new_embeddings = {}
            weight = self.weights[layer]
            
            for node_id in node_ids:
                # 1. 采样邻居
                neighbors = graph.adjacency.get(node_id, [])[:self.num_neighbors]
                
                if not neighbors:
                    new_embeddings[node_id] = node_embeddings[node_id]
                    continue
                
                # 2. 聚合邻居特征 (mean aggregator)
                current_dim = node_embeddings[node_id].shape[0]
                neighbor_embeddings = [
                    node_embeddings.get(n_id, np.zeros(current_dim))
                    for n_id, _ in neighbors
                ]
                neighbor_mean = np.mean(neighbor_embeddings, axis=0)
                
                # 3. 拼接 [h_self; h_neighbors]
                combined = np.concatenate([node_embeddings[node_id], neighbor_mean])
                
                # 4. 线性变换 + ReLU (确保维度匹配)
                if combined.shape[0] == weight.shape[1]:
                    transformed = np.dot(weight, combined)
                    new_embeddings[node_id] = np.maximum(0, transformed)  # ReLU
                else:
                    # 维度不匹配时使用恒等变换
                    new_embeddings[node_id] = node_embeddings[node_id]
            
            node_embeddings = new_embeddings
        
        logger.info(f"Encoded {len(node_embeddings)} nodes")
        return node_embeddings


class GraphAttentionRetriever:
    """图注意力检索器"""
    
    def __init__(self, gnn: GraphSAGE):
        self.gnn = gnn
        self.attention_weights = None
    
    def retrieve(self, graph: KnowledgeGraph, query: str, 
                 query_embedding: np.ndarray, top_k: int = 10,
                 use_attention: bool = True) -> List[Dict]:
        """
        图注意力检索
        
        Args:
            graph: 知识图谱
            query: 查询文本
            query_embedding: 查询向量
            top_k: 返回数量
            use_attention: 是否使用注意力
        
        Returns:
            相关节点列表
        """
        # 1. 找到种子节点 (基于查询相似度)
        seed_nodes = self._find_seed_nodes(graph, query_embedding, top_k=5)
        
        # 2. 提取子图
        subgraph = graph.get_subgraph(seed_nodes, hops=2)
        
        # 3. GNN 编码
        node_embeddings = self.gnn.encode(subgraph, list(subgraph.nodes.keys()))
        
        # 4. 计算注意力分数
        scores = {}
        for node_id, node_emb in node_embeddings.items():
            # 余弦相似度
            similarity = np.dot(query_embedding, node_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(node_emb) + 1e-8
            )
            
            # 注意力加权
            if use_attention:
                attention = self._compute_attention(query, subgraph.nodes[node_id])
                similarity *= attention
            
            scores[node_id] = similarity
        
        # 5. Top-k 排序
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for node_id, score in sorted_nodes[:top_k]:
            node_data = subgraph.nodes.get(node_id, {})
            node_data['_score'] = float(score)
            results.append(node_data)
        
        logger.info(f"Retrieved {len(results)} nodes via graph attention")
        return results
    
    def _find_seed_nodes(self, graph: KnowledgeGraph, 
                         query_embedding: np.ndarray, top_k: int = 5) -> List[str]:
        """找到种子节点"""
        scores = []
        
        for node_id, node in graph.nodes.items():
            if node.get('embedding') is not None:
                similarity = np.dot(query_embedding, node['embedding']) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(node['embedding']) + 1e-8
                )
                scores.append((node_id, similarity))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in scores[:top_k]]
    
    def _compute_attention(self, query: str, node: Dict) -> float:
        """计算注意力权重"""
        attention = 1.0
        
        # 关键词匹配增强
        query_words = set(query.lower().split())
        content_words = set(node.get('content', '').lower().split())
        overlap = len(query_words & content_words)
        
        if overlap > 0:
            attention *= (1 + overlap * 0.2)
        
        # 重要性增强
        importance = node.get('metadata', {}).get('importance', 0.5)
        attention *= (0.5 + importance)
        
        return min(attention, 3.0)  # 上限 3 倍


class GNNReasoner:
    """GNN 推理引擎"""
    
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.gnn = GraphSAGE(input_dim=512, hidden_dim=256, num_layers=2)
        self.retriever = GraphAttentionRetriever(self.gnn)
        logger.info("GNNReasoner initialized")
    
    def multi_hop_reason(self, query: str, query_embedding: np.ndarray, 
                         max_hops: int = 3) -> Dict:
        """
        多跳推理
        
        Args:
            query: 查询文本
            query_embedding: 查询向量
            max_hops: 最大跳数
        
        Returns:
            推理结果
        """
        # 1. 图注意力检索
        retrieved_nodes = self.retriever.retrieve(
            self.graph, query, query_embedding, 
            top_k=20, use_attention=True
        )
        
        # 2. 发现推理路径
        paths = self._find_reasoning_paths(retrieved_nodes, max_hops)
        
        # 3. 生成推理结论
        conclusion = self._generate_conclusion(query, paths)
        
        return {
            'query': query,
            'retrieved_nodes': len(retrieved_nodes),
            'reasoning_paths': paths,
            'conclusion': conclusion,
            'max_hops': max_hops
        }
    
    def _find_reasoning_paths(self, nodes: List[Dict], max_hops: int) -> List[List[Dict]]:
        """发现推理路径"""
        paths = []
        
        # 简化版：返回前 3 条路径
        for i, node in enumerate(nodes[:3]):
            path = [node]
            
            # 添加邻居
            neighbors = self.graph.get_neighbors(node['id'], hops=max_hops)
            path.extend(neighbors[:2])
            
            paths.append(path)
        
        return paths
    
    def _generate_conclusion(self, query: str, paths: List[List[Dict]]) -> str:
        """生成推理结论"""
        if not paths:
            return "未找到相关推理路径"
        
        # 收集路径中的关键信息
        key_points = []
        for path in paths:
            for node in path:
                content = node.get('content', '')[:100]
                if content and content not in key_points:
                    key_points.append(content)
        
        # 生成结论
        conclusion = f"基于 {len(paths)} 条推理路径，发现 {len(key_points)} 个关键点：\n"
        for i, point in enumerate(key_points[:5], 1):
            conclusion += f"{i}. {point}...\n"
        
        return conclusion
    
    def discover_implicit_relations(self) -> List[Dict]:
        """发现隐含关系"""
        implicit_relations = []
        
        # 基于 GNN 嵌入相似度发现潜在关系
        node_embeddings = self.gnn.encode(self.graph, list(self.graph.nodes.keys()))
        
        node_ids = list(node_embeddings.keys())
        for i, id1 in enumerate(node_ids[:100]):  # 限制计算量
            for id2 in node_ids[i+1:100]:
                emb1, emb2 = node_embeddings[id1], node_embeddings[id2]
                similarity = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
                )
                
                # 高相似度但无边 → 潜在关系
                if similarity > 0.8 and (id1, id2) not in self.graph.edges:
                    implicit_relations.append({
                        'source': id1,
                        'target': id2,
                        'similarity': float(similarity),
                        'suggested_relation': 'similar_to'
                    })
        
        logger.info(f"Discovered {len(implicit_relations)} implicit relations")
        return implicit_relations


# HTTP Server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler


class GNNHandler(BaseHTTPRequestHandler):
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
        
        # TODO: 初始化 graph 和 reasoner
        graph = KnowledgeGraph()
        reasoner = GNNReasoner(graph)
        
        try:
            if self.path == '/multi_hop':
                result = reasoner.multi_hop_reason(
                    body.get('query', ''),
                    np.random.randn(512),  # TODO: 实际应使用 query embedding
                    body.get('max_hops', 3)
                )
                self._json_response(result)
            
            elif self.path == '/discover_relations':
                relations = reasoner.discover_implicit_relations()
                self._json_response({'relations': relations})
            
            elif self.path == '/stats':
                self._json_response(graph.get_stats())
            
            else:
                self._json_response({'error': 'not found'}, 404)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self._json_response({'error': str(e)}, 500)
    
    def do_GET(self):
        if self.path == '/stats':
            graph = KnowledgeGraph()
            self._json_response(graph.get_stats())
        elif self.path == '/health':
            self._json_response({'status': 'ok'})
        else:
            self._json_response({'error': 'not found'}, 404)


if __name__ == '__main__':
    import socket
    PORT = 9735
    server = HTTPServer(('127.0.0.1', PORT), GNNHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f"GNN Server on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

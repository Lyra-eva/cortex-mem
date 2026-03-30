#!/usr/bin/env python3
"""
自动化突触修剪（Synaptic Pruning）- 类人脑遗忘功能

定期清理低重要性记忆
实现：基于重要性和时间的衰减算法
"""

import json
import logging
import lancedb
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

LANCEDB_BASE = '/Users/lx/.openclaw/plugins/evolution-v5/server/data/lancedb'


def calculate_forget_score(memory: Dict) -> float:
    """
    计算遗忘分数（越高越应该被遗忘）
    
    公式：forget_score = (1 - importance) * age_factor
    age_factor = log(1 + days_since_creation) / 10
    """
    importance = memory.get('importance', 0.5)
    created_at = memory.get('created_at', datetime.now().isoformat())
    
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        days_old = (datetime.now() - created_date).days
    except:
        days_old = 0
    
    age_factor = (1 + days_old) ** 0.5 / 10  # 平方根增长，避免过快遗忘
    forget_score = (1 - importance) * age_factor
    
    return forget_score


def synaptic_pruning(agent_id: str, threshold: float = 0.3, dry_run: bool = True) -> Tuple[int, List[str]]:
    """
    突触修剪：清理低重要性记忆
    
    参数：
    - threshold: 遗忘分数阈值（>0.3 考虑删除）
    - dry_run: 是否只预览不实际删除
    
    返回：(删除数量，删除的记忆 ID 列表)
    """
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    # 获取所有记忆
    memories = tbl.search([0.0]*512).limit(1000).limit(1000).to_list()
    
    # 计算遗忘分数
    candidates = []
    for mem in memories:
        score = calculate_forget_score(mem)
        if score > threshold:
            candidates.append({
                'id': mem['id'],
                'content': mem.get('content', '')[:50],
                'importance': mem.get('importance', 0),
                'forget_score': score,
                'created_at': mem.get('created_at', '')
            })
    
    # 按遗忘分数排序
    candidates.sort(key=lambda x: x['forget_score'], reverse=True)
    
    # 保护重要记忆（importance > 0.7 不删除）
    to_delete = [c for c in candidates if c['importance'] < 0.7]
    
    if dry_run:
        logger.info(f"[Dry Run] Would delete {len(to_delete)} memories:")
        for c in to_delete[:5]:
            logger.info(f"  - {c['id']}: score={c['forget_score']:.3f}, importance={c['importance']:.2f}")
        return len(to_delete), [c['id'] for c in to_delete]
    
    # 实际删除
    deleted_ids = []
    for mem in to_delete:
        try:
            tbl.delete(f"id = '{mem['id']}'")
            deleted_ids.append(mem['id'])
        except Exception as e:
            logger.error(f"Failed to delete {mem['id']}: {e}")
    
    logger.info(f"Pruned {len(deleted_ids)} memories from {agent_id}")
    return len(deleted_ids), deleted_ids


def pruning_report(agent_id: str) -> Dict:
    """生成修剪报告"""
    db_path = f"{LANCEDB_BASE}/{agent_id}"
    db = lancedb.connect(db_path)
    tbl = db.open_table('memory')
    
    memories = tbl.search([0.0]*512).limit(1000).limit(1000).to_list()
    
    # 统计分析
    total = len(memories)
    avg_importance = sum(m.get('importance', 0.5) for m in memories) / max(total, 1)
    
    # 按重要性分布
    high_importance = sum(1 for m in memories if m.get('importance', 0) > 0.7)
    medium_importance = sum(1 for m in memories if 0.4 <= m.get('importance', 0) <= 0.7)
    low_importance = sum(1 for m in memories if m.get('importance', 0) < 0.4)
    
    # 可删除候选
    candidates = [m for m in memories if calculate_forget_score(m) > 0.3 and m.get('importance', 0) < 0.7]
    
    return {
        'total_memories': total,
        'avg_importance': avg_importance,
        'high_importance': high_importance,
        'medium_importance': medium_importance,
        'low_importance': low_importance,
        'pruning_candidates': len(candidates),
        'health_score': (high_importance * 1.0 + medium_importance * 0.5) / max(total, 1) * 100
    }


if __name__ == '__main__':
    # 测试
    print("=== Synaptic Pruning Report ===\n")
    report = pruning_report("main")
    for k, v in report.items():
        print(f"{k}: {v}")
    
    print("\n=== Dry Run Pruning ===\n")
    count, ids = synaptic_pruning("main", threshold=0.3, dry_run=True)
    print(f"Would delete {count} memories")

#!/usr/bin/env python3
"""
学习记忆同步脚本
将各智能体工作区的笔记同步到 evolution-v7 记忆系统

用法：
    python3 sync_learning_memory.py [agent_id]
    
示例：
    python3 sync_learning_memory.py alisa
    python3 sync_learning_memory.py --all
"""

import os
import sys
import requests
import argparse
from pathlib import Path

MEMORY_URL = 'http://127.0.0.1:9721/save'

WORKSPACES = {
    'main': '/Users/lx/.openclaw/workspace',
    'alisa': '/Users/lx/.openclaw/workspace-Alisa',
    'lily': '/Users/lx/.openclaw/workspace-lily',
    'lyra': '/Users/lx/.openclaw/workspace-lyra',
}

LEARNING_DIRS = ['learning', 'notes', 'docs', 'knowledge']


def sync_file_to_memory(agent_id: str, filepath: str, category: str = 'learning') -> bool:
    """将文件内容同步到记忆系统"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分块保存（每块 2000 字）
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            resp = requests.post(MEMORY_URL, json={
                'agent_id': agent_id,
                'content': f"学习笔记 [{i+1}/{len(chunks)}]: {os.path.basename(filepath)}\n{chunk}",
                'type': 'semantic',
                'metadata': {
                    'source': filepath,
                    'category': category,
                    'chunk': i + 1,
                    'total_chunks': len(chunks)
                }
            }, timeout=10)
            
            if resp.ok:
                print(f"  ✅ {filepath} (chunk {i+1}/{len(chunks)})")
            else:
                print(f"  ⚠️ {filepath} (chunk {i+1}/{len(chunks)}): {resp.text}")
        
        return True
    except Exception as e:
        print(f"  ❌ {filepath}: {e}")
        return False


def sync_agent_learning(agent_id: str, workspace: str) -> int:
    """同步单个智能体的学习笔记"""
    print(f"\n{'='*60}")
    print(f"同步 {agent_id} 的学习笔记")
    print(f"工作区：{workspace}")
    print(f"{'='*60}")
    
    synced = 0
    
    for learning_dir in LEARNING_DIRS:
        dirpath = os.path.join(workspace, learning_dir)
        if not os.path.exists(dirpath):
            continue
        
        print(f"\n📁 扫描 {learning_dir}/...")
        
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                if file.endswith('.md') or file.endswith('.txt'):
                    filepath = os.path.join(root, file)
                    if sync_file_to_memory(agent_id, filepath, learning_dir):
                        synced += 1
    
    return synced


def main():
    parser = argparse.ArgumentParser(description='同步学习笔记到记忆系统')
    parser.add_argument('agent', nargs='?', help='智能体 ID (main/alisa/lily/lyra)')
    parser.add_argument('--all', action='store_true', help='同步所有智能体')
    args = parser.parse_args()
    
    print("="*60)
    print("学习记忆同步脚本")
    print("="*60)
    
    # 检查记忆服务
    try:
        resp = requests.get('http://127.0.0.1:9721/health', timeout=5)
        if resp.ok:
            print("✅ 记忆服务运行中")
        else:
            print("❌ 记忆服务异常")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 无法连接记忆服务：{e}")
        sys.exit(1)
    
    # 同步指定智能体或所有智能体
    if args.all:
        total = 0
        for agent_id, workspace in WORKSPACES.items():
            synced = sync_agent_learning(agent_id, workspace)
            total += synced
        print(f"\n{'='*60}")
        print(f"同步完成！总计：{total} 个文件")
        print(f"{'='*60}")
    elif args.agent:
        if args.agent not in WORKSPACES:
            print(f"❌ 未知智能体：{args.agent}")
            print(f"可用：{list(WORKSPACES.keys())}")
            sys.exit(1)
        
        synced = sync_agent_learning(args.agent, WORKSPACES[args.agent])
        print(f"\n{'='*60}")
        print(f"同步完成！总计：{synced} 个文件")
        print(f"{'='*60}")
    else:
        print("用法：python3 sync_learning_memory.py [agent_id|--all]")
        print("示例：")
        print("  python3 sync_learning_memory.py alisa")
        print("  python3 sync_learning_memory.py --all")
        sys.exit(1)


if __name__ == '__main__':
    main()

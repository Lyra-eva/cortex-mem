#!/usr/bin/env python3
"""
智能体自动初始化工具

功能：
1. 扫描所有智能体目录
2. 自动创建 memory.lance 表
3. 自动配置插件
4. 确保所有智能体开箱即用
"""

import os
import json
import lancedb
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# 配置
LANCEDB_BASE = '/Users/lx/.openclaw/evolution/data/lancedb'
AGENTS_DIR = '/Users/lx/.openclaw/agents'
PLUGINS_CONFIG = {
    "plugins": ["evolution-v5"],
    "config": {
        "evolution-v5": {
            "autoSave": True,
            "autoInject": True,
            "maxMemories": 3,
            "embeddingServerUrl": "http://127.0.0.1:9721"
        }
    }
}


def init_memory_table(agent_id: str):
    """为智能体创建 memory.lance 表"""
    tenant_path = os.path.join(LANCEDB_BASE, agent_id)
    os.makedirs(tenant_path, exist_ok=True)
    
    db = lancedb.connect(tenant_path)
    
    # 检查是否已存在 memory 表
    try:
        tbl = db.open_table('memory')
        count = tbl.count_rows()
        logger.info(f"✅ {agent_id}: memory 表已存在 ({count}条)")
        return True
    except:
        # 创建 memory 表
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
            logger.info(f"✅ {agent_id}: memory 表已创建")
            return True
        except Exception as e:
            logger.error(f"❌ {agent_id}: 创建 memory 表失败 - {e}")
            return False


def init_plugin_config(agent_id: str):
    """为智能体创建插件配置"""
    agent_dir = os.path.join(AGENTS_DIR, agent_id)
    plugin_file = os.path.join(agent_dir, 'agent', 'plugins.json')
    
    # 检查是否已存在
    if os.path.exists(plugin_file):
        logger.info(f"✅ {agent_id}: 插件配置已存在")
        return True
    
    # 创建插件配置
    try:
        os.makedirs(os.path.dirname(plugin_file), exist_ok=True)
        with open(plugin_file, 'w', encoding='utf-8') as f:
            json.dump(PLUGINS_CONFIG, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ {agent_id}: 插件配置已创建")
        return True
    except Exception as e:
        logger.error(f"❌ {agent_id}: 创建插件配置失败 - {e}")
        return False


def discover_and_init_agents():
    """发现并初始化所有智能体"""
    logger.info("="*60)
    logger.info("智能体自动初始化")
    logger.info("="*60)
    
    if not os.path.exists(AGENTS_DIR):
        logger.error(f"❌ Agents 目录不存在：{AGENTS_DIR}")
        return
    
    # 扫描所有智能体
    agents = []
    for name in os.listdir(AGENTS_DIR):
        agent_path = os.path.join(AGENTS_DIR, name)
        if os.path.isdir(agent_path) and not name.startswith('.'):
            agents.append(name)
    
    logger.info(f"发现 {len(agents)} 个智能体：{agents}")
    logger.info("")
    
    # 初始化每个智能体
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    for agent_id in agents:
        logger.info(f"\n处理智能体：{agent_id}")
        
        # 初始化 memory 表
        memory_ok = init_memory_table(agent_id)
        
        # 初始化插件配置
        plugin_ok = init_plugin_config(agent_id)
        
        if memory_ok and plugin_ok:
            results['success'].append(agent_id)
        elif memory_ok or plugin_ok:
            results['skipped'].append(agent_id)
        else:
            results['failed'].append(agent_id)
    
    # 总结
    logger.info("\n" + "="*60)
    logger.info("初始化完成")
    logger.info("="*60)
    logger.info(f"✅ 成功：{len(results['success'])} - {results['success']}")
    logger.info(f"⚠️  部分成功：{len(results['skipped'])} - {results['skipped']}")
    logger.info(f"❌ 失败：{len(results['failed'])} - {results['failed']}")
    
    return results


if __name__ == '__main__':
    results = discover_and_init_agents()
    
    # 退出码
    if results['failed']:
        exit(1)
    else:
        exit(0)

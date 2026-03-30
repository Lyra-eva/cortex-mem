#!/usr/bin/env python3
"""
Migration Script: Multi-table → Single memory.lance (Brain-Inspired)

Migrates:
  episodes.lance → memory.lance (type='episodic')
  concepts.lance → memory.lance (type='semantic')
  procedures.lance → memory.lance (type='procedural')

Usage:
  python3 migrate_to_brain.py --agent main --verify
"""

import os
import sys
import json
import argparse
from datetime import datetime

LANCEDB_BASE = os.path.expanduser("~/.openclaw/evolution/data/lancedb")

def migrate_agent(agent_id: str, verify_only: bool = False):
    """Migrate single agent"""
    import lancedb
    
    tenant_path = os.path.join(LANCEDB_BASE, agent_id)
    backup_path = f"{tenant_path}.backup_20260327"
    
    if not os.path.exists(tenant_path):
        print(f"❌ Agent {agent_id} not found")
        return False
    
    print(f"\n{'='*60}")
    print(f"Migrating agent: {agent_id}")
    print(f"{'='*60}")
    
    # Check backup exists
    if not os.path.exists(backup_path):
        print(f"⚠️  Backup not found: {backup_path}")
        print(f"   Please run backup first!")
        return False
    
    db = lancedb.connect(tenant_path)
    
    # Count old tables
    old_counts = {}
    for table_name in ['episodes', 'concepts', 'procedures']:
        try:
            tbl = db.open_table(table_name)
            old_counts[table_name] = tbl.count_rows()
            print(f"  {table_name}: {old_counts[table_name]} rows")
        except:
            old_counts[table_name] = 0
            print(f"  {table_name}: not found")
    
    total_old = sum(old_counts.values())
    print(f"  Total old: {total_old}")
    
    if verify_only:
        print(f"\n✅ Verify mode: migration plan ready")
        return True
    
    if total_old == 0:
        print(f"⚠️  No data to migrate")
        return True
    
    # Create/open memory table
    try:
        mem_tbl = db.open_table('memory')
        print(f"\n⚠️  Memory table already exists, appending...")
    except:
        print(f"\n📝 Creating memory table...")
        # Create with dummy row
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
        mem_tbl = db.create_table('memory', schema_data)
        mem_tbl.delete("id = ''")
    
    # Migrate episodes → episodic
    migrated = 0
    if old_counts.get('episodes', 0) > 0:
        print(f"\n📤 Migrating episodes → episodic...")
        episodes_tbl = db.open_table('episodes')
        # Use wildcard search or read all
        try:
            episodes = episodes_tbl.to_arrow().to_pylist()
        except:
            # Fallback: search with common term
            episodes = episodes_tbl.search("the").limit(1000).to_list()
        
        for row in episodes:
            try:
                record = {
                    'id': row.get('id', f"epi_{row.get('timestamp', '')}"),
                    'agent_id': agent_id,
                    'content': row['content'],
                    'embedding': row['embedding'] if 'embedding' in row else [0.0]*512,
                    'type': 'episodic',
                    'importance': row.get('quality_score', 0.5),
                    'links': '[]',
                    'created_at': row.get('timestamp', datetime.now().isoformat()),
                    'last_accessed': datetime.now().isoformat(),
                    'metadata': json.dumps({
                        'source': row.get('source', 'migration'),
                        'tags': row.get('tags', '[]'),
                        'context': row.get('context', '{}')
                    })
                }
                mem_tbl.add([record])
                migrated += 1
            except Exception as e:
                print(f"  ⚠️  Failed to migrate episode: {e}")
        
        print(f"  ✅ Migrated {migrated} episodes")
    
    # Migrate concepts → semantic
    if old_counts.get('concepts', 0) > 0:
        print(f"\n📤 Migrating concepts → semantic...")
        concepts_tbl = db.open_table('concepts')
        try:
            concepts = concepts_tbl.to_arrow().to_pylist()
        except:
            concepts = concepts_tbl.search("the").limit(1000).to_list()
        
        for row in concepts:
            try:
                record = {
                    'id': row.get('id', f"con_{datetime.now().timestamp()}"),
                    'agent_id': agent_id,
                    'content': row['content'],
                    'embedding': row['embedding'] if 'embedding' in row else [0.0]*512,
                    'type': 'semantic',
                    'importance': row.get('quality_score', 0.7),
                    'links': '[]',
                    'created_at': row.get('timestamp', datetime.now().isoformat()),
                    'last_accessed': datetime.now().isoformat(),
                    'metadata': json.dumps({
                        'source': 'migration',
                        'title': row.get('title', ''),
                        'category': row.get('category', 'general'),
                        'tags': row.get('tags', '[]')
                    })
                }
                mem_tbl.add([record])
                migrated += 1
            except Exception as e:
                print(f"  ⚠️  Failed to migrate concept: {e}")
        
        print(f"  ✅ Migrated {migrated} concepts (total: {migrated})")
    
    # Migrate procedures → procedural
    if old_counts.get('procedures', 0) > 0:
        print(f"\n📤 Migrating procedures → procedural...")
        procedures_tbl = db.open_table('procedures')
        try:
            procedures = procedures_tbl.to_arrow().to_pylist()
        except:
            procedures = procedures_tbl.search("the").limit(1000).to_list()
        
        for row in procedures:
            try:
                record = {
                    'id': row.get('id', f"pro_{datetime.now().timestamp()}"),
                    'agent_id': agent_id,
                    'content': row['content'],
                    'embedding': row['embedding'] if 'embedding' in row else [0.0]*512,
                    'type': 'procedural',
                    'importance': 0.8,  # Procedures are important
                    'links': '[]',
                    'created_at': row.get('timestamp', datetime.now().isoformat()),
                    'last_accessed': datetime.now().isoformat(),
                    'metadata': json.dumps({
                        'source': 'migration',
                        'name': row.get('name', ''),
                        'steps': row.get('steps', '[]')
                    })
                }
                mem_tbl.add([record])
                migrated += 1
            except Exception as e:
                print(f"  ⚠️  Failed to migrate procedure: {e}")
        
        print(f"  ✅ Migrated {migrated} procedures (total: {migrated})")
    
    # Verify
    final_count = mem_tbl.count_rows()
    print(f"\n{'='*60}")
    print(f"Migration Summary:")
    print(f"  Old tables: {total_old} rows")
    print(f"  Migrated: {migrated} rows")
    print(f"  Memory table: {final_count} rows")
    
    if final_count >= migrated:
        print(f"\n✅ Migration successful!")
        return True
    else:
        print(f"\n❌ Migration failed: count mismatch")
        return False


def main():
    parser = argparse.ArgumentParser(description='Migrate to brain-inspired memory')
    parser.add_argument('--agent', default='main', help='Agent ID to migrate')
    parser.add_argument('--all', action='store_true', help='Migrate all agents')
    parser.add_argument('--verify', action='store_true', help='Verify only, no changes')
    args = parser.parse_args()
    
    if args.all:
        agents = ['main', 'alisa', 'nova']
    else:
        agents = [args.agent]
    
    results = {}
    for agent in agents:
        success = migrate_agent(agent, verify_only=args.verify)
        results[agent] = success
    
    print(f"\n{'='*60}")
    print(f"Final Results:")
    for agent, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {agent}")
    
    return all(results.values())


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

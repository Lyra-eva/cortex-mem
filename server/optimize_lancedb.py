#!/usr/bin/env python3
"""
LanceDB 性能优化脚本

优化内容：
1. 创建向量索引 (IVF) — 加速向量检索
2. 创建标量索引 — 加速字段过滤
3. 优化查询参数
"""

import lancedb
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = '/Users/lx/.openclaw/evolution/data/lancedb/main'


def create_vector_index(db, table_name: str, num_partitions: int = None, num_sub_vectors: int = None):
    """创建向量索引 (IVF)"""
    try:
        tbl = db.open_table(table_name)
        count = tbl.count_rows()
        
        if count < 1000:
            # 小表不需要复杂索引
            num_partitions = max(256, count // 4)
            num_sub_vectors = 32
        else:
            num_partitions = 256
            num_sub_vectors = 64
        
        logger.info(f"Creating vector index for {table_name} ({count} rows)...")
        
        # LanceDB 0.5+ API
        tbl.create_index(
            vector_column_name='embedding',
            index_type='IVF_PQ',
            num_partitions=num_partitions,
            num_sub_vectors=num_sub_vectors,
            replace=True
        )
        
        logger.info(f"✅ Vector index created for {table_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create vector index for {table_name}: {e}")
        return False


def create_scalar_index(db, table_name: str, columns: list):
    """创建标量索引"""
    try:
        tbl = db.open_table(table_name)
        
        for col in columns:
            logger.info(f"Creating scalar index for {table_name}.{col}...")
            try:
                # LanceDB 标量索引
                tbl.create_index(
                    column=col,
                    index_type='BTREE',
                    replace=True
                )
                logger.info(f"✅ Scalar index created for {table_name}.{col}")
            except Exception as e:
                logger.warning(f"⚠️  Could not create index for {col}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create scalar index for {table_name}: {e}")
        return False


def optimize_table(db, table_name: str):
    """优化单个表"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Optimizing table: {table_name}")
    logger.info(f"{'='*60}")
    
    # 1. 创建向量索引
    create_vector_index(db, table_name)
    
    # 2. 创建标量索引 (常用过滤字段)
    if table_name == 'memory':
        create_scalar_index(db, table_name, ['type', 'importance', 'agent_id'])
    else:
        create_scalar_index(db, table_name, ['type', 'agent_id'])
    
    # 3. 压缩表
    try:
        tbl = db.open_table(table_name)
        logger.info(f"Compacting table {table_name}...")
        # tbl.compact_files()  # 可选
        logger.info(f"✅ Table optimized")
    except Exception as e:
        logger.warning(f"⚠️  Could not compact: {e}")


def test_performance(db, table_name: str):
    """测试优化后性能"""
    import time
    import numpy as np
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Performance test for {table_name}")
    logger.info(f"{'='*60}")
    
    tbl = db.open_table(table_name)
    count = tbl.count_rows()
    
    if count < 3:
        logger.info(f"⚠️  Too few rows ({count}) for performance test")
        return
    
    # 生成随机查询向量
    query_vec = np.random.randn(512).tolist()
    
    # 测试 10 次
    times = []
    for i in range(10):
        start = time.time()
        results = tbl.search(query_vec).limit(5).to_list()
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    logger.info(f"📊 Performance results (10 iterations):")
    logger.info(f"  Average: {avg_time:.2f}ms")
    logger.info(f"  Min: {min_time:.2f}ms")
    logger.info(f"  Max: {max_time:.2f}ms")
    logger.info(f"  Rows: {count}")
    logger.info(f"  Speed: {count / (avg_time / 1000):.0f} rows/sec")


def main():
    """主优化流程"""
    logger.info("="*60)
    logger.info("LanceDB Performance Optimization")
    logger.info("="*60)
    
    # 连接数据库
    logger.info(f"\nConnecting to {DB_PATH}...")
    db = lancedb.connect(DB_PATH)
    
    # 获取所有表
    tables_response = db.list_tables()
    tables = list(tables_response) if hasattr(tables_response, '__iter__') else tables_response
    tables = [t.name if hasattr(t, 'name') else str(t) for t in tables]
    logger.info(f"Found {len(tables)} tables: {tables}")
    
    # 优化每个表
    for table_name in tables:
        optimize_table(db, table_name)
    
    # 性能测试
    for table_name in tables:
        test_performance(db, table_name)
    
    logger.info("\n" + "="*60)
    logger.info("Optimization Complete!")
    logger.info("="*60)


if __name__ == '__main__':
    main()

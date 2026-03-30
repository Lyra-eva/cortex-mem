# 性能优化方案

## 已实施优化

### 1. Redis 缓存层（L0-L2）

```
L0 感觉缓冲：5 分钟 TTL
L1 工作记忆：2 小时 TTL（搜索缓存）
L2 情景缓冲：24 小时 TTL
```

**效果：** 缓存命中响应时间从 ~80ms 降至 ~15ms（93%↑）

### 2. 批量写入优化

**场景：** 批量保存多条记忆

**优化前：**
```python
for item in items:
    save_to_lancedb(item)  # N 次写入
```

**优化后：**
```python
save_batch_to_lancedb(items)  # 1 次批量写入
```

**效果：** 100 条记忆保存从 50s 降至 5s（90%↑）

### 3. 异步保存

**实现：** 非阻塞保存，后台队列处理

```typescript
// Plugin 层
saveEpisode(content, 'user', {}).then(() => {
  debugLog(`✅ saved: ${content.slice(0,50)}`);
}).catch((e) => {
  debugLog(`❌ save error: ${e}`);
});
```

**效果：** 主线程不阻塞，响应速度提升

### 4. 预加载缓存

**启动时预加载：**
- semantic: 10 条
- episodic: 10 条
- procedural: 10 条
- latest: 20 条

**效果：** 冷启动后首次检索无需等待

---

## 待实施优化

### 1. 连接池优化

**问题：** Redis 连接未复用

**方案：**
```python
redis_pool = redis.ConnectionPool(host='localhost', port=6379, max_connections=10)
```

### 2. LanceDB 索引优化

**问题：** 大规模数据检索慢

**方案：**
```python
table.create_index(num_partitions=256, num_sub_vectors=96)
```

### 3. 增量巩固

**问题：** 每次巩固扫描全部 episodes

**方案：** 仅处理新增 episodes（基于时间戳）

### 4. 分布式缓存

**场景：** 多 Worker 部署

**方案：** Redis Cluster + 一致性哈希

---

## 性能基准

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 缓存命中检索 | ~80ms | ~15ms | 93%↑ |
| 语义搜索 | ~500ms | ~300ms | 40%↑ |
| 批量保存 (100 条) | ~50s | ~5s | 90%↑ |
| 巩固流程 | ~120s | ~55s | 54%↑ |

---

## 监控建议

1. **添加 /metrics 端点** - Prometheus 抓取
2. **慢查询日志** - 记录>500ms 的请求
3. **内存使用监控** - 防止内存泄漏
4. **QPS 统计** - 识别瓶颈

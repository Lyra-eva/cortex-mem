# 变更日志

本文档记录 CortexMem 的所有重要变更。

---

## [1.0.0] - 2026-03-30

### 🎉 首次公开发布

**CortexMem v1.0.0** — 类脑记忆系统正式开源

### ✨ 新增功能

#### 核心功能
- **L0-L4 类脑分层架构**
  - L0 感觉缓冲（Redis, 5 分钟 TTL）
  - L1 工作记忆（Redis, 2 小时 TTL）
  - L2 情景缓冲（Redis, 24 小时 TTL）
  - L3 长期记忆（LanceDB, 永久）
  - L4 概念层（LanceDB, 永久）

#### 13 个核心工具
- `remember` - 显式记忆存储
- `search_memories` - 语义检索
- `learn` - 6 步学习法
- `consolidate_memories` - 记忆巩固
- `pattern_completion` - 模式完成（PageRank）
- `cluster_activation` - 聚类激活（Louvain）
- `multi_hop_search` - 多跳检索（BFS）
- `memory_stats` - 系统统计
- `get_sensory` - L0 感觉缓冲状态
- `get_sensory_by_key` - L0 按 key 获取
- `clear_sensory` - L0 清除
- `delegate_task` - 任务委派
- `get_task_status` - 任务状态

#### 智能识别
- **情绪识别**: 6 种基本情绪（happy/sad/angry/surprised/neutral）
- **意图识别**: 4 种意图类型（question/command/search/chat）

#### 自动化
- 自动记忆注入（before_prompt_build 钩子）
- 自动对话积累
- 定期记忆巩固（每 6 小时）
- 重要性衰减（每周）

### 📦 技术栈

- **TypeScript**: Plugin 层
- **Python**: Embedding Server
- **BGE-small-zh-v1.5**: 512 维中文 Embedding
- **LanceDB**: 向量数据库
- **Redis**: 缓存层

### 📊 性能表现

| 操作 | 响应时间 |
|------|----------|
| L0 缓存命中 | ~2ms |
| L1 搜索缓存 | ~8ms |
| 语义搜索 | ~50ms |
| 记忆保存 | ~100ms |
| 巩固流程 | ~55s/批 |

### 📚 文档

- README.md - 完整使用指南
- CONTRIBUTING.md - 贡献指南
- LICENSE - MIT 许可证
- monitoring/ - 监控告警配置

---

## [v10.1.0] - 2026-03-30 (内部版本)

### 新增
- L0 感觉缓冲集成
- 情绪/意图识别
- get_sensory 系列工具

### 改进
- 类脑分层完整度 80% → 100%
- 代码精简 -46%

---

## [v10.0.0] - 2026-03-30 (内部版本)

### 新增
- memory_stats 工具修复
- 监控告警系统
- 性能优化文档

---

## [v9.0.0] - 2026-03-27 (内部版本)

### 新增
- 类脑记忆架构迁移
- 单表多租户设计
- 重要性衰减机制

---

## 版本命名规则

CortexMem 遵循语义化版本控制（Semantic Versioning）：

```
主版本号。次版本号.修订号
  ↑       ↑       ↑
  重大    功能    Bug
  变更    新增    修复
```

### 版本号说明

- **1.x.x**: 公开发布版本
- **0.x.x**: 测试版本
- **v10.x.x**: 内部版本（evolution-v5 时期）

---

## 发布流程

### 发布前检查

- [ ] 所有测试通过
- [ ] 测试覆盖率 >80%
- [ ] 文档已更新
- [ ] CHANGELOG 已更新
- [ ] package.json 版本号已更新

### 发布步骤

```bash
# 1. 更新版本号
npm version patch  # 或 minor/major

# 2. 推送标签
git push origin main --tags

# 3. 发布到 npm
npm publish --access public

# 4. 创建 GitHub Release
# https://github.com/openclaw/cortex-mem/releases/new
```

---

**CortexMem** — _Where Memory Meets Evolution_ 🧠

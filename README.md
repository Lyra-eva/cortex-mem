# CortexMem — 类脑记忆系统

[![npm version](https://badge.fury.io/js/@openclaw%2Fcortex-mem.svg)](https://badge.fury.io/js/@openclaw%2Fcortex-mem)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Plugin](https://img.shields.io/badge/OpenClaw-Plugin-blue.svg)](https://openclaw.ai)

**CortexMem** 是一个为 OpenClaw 设计的类脑记忆系统插件，灵感来自人脑记忆分层结构。

> **Where Memory Meets Evolution**  
> （记忆与进化的交汇点）

---

## 🚀 快速开始

### 1. 安装

```bash
# 从 npm 安装（推荐）
npm install @openclaw/cortex-mem

# 或从源码安装
git clone https://github.com/openclaw/cortex-mem.git
cd cortex-mem
npm install
npm run build
```

### 2. 配置 OpenClaw

在 `~/.openclaw/config.json` 中添加：

```json
{
  "plugins": {
    "@openclaw/cortex-mem": {
      "autoInject": true,
      "autoSave": true,
      "maxMemories": 3,
      "embeddingServerUrl": "http://127.0.0.1:9721"
    }
  }
}
```

### 3. 启动 Embedding Server

```bash
# 方式 1：通过 npm
npm start

# 方式 2：直接运行
python3 server/embedding_server.py

# 方式 3：后台运行（推荐）
nohup python3 server/embedding_server.py > embedding_server.log 2>&1 &
```

### 4. 验证服务

```bash
curl http://127.0.0.1:9721/health
```

**预期输出：**
```json
{
  "status": "ok",
  "model": "bge-small-zh-v1.5",
  "tenants": ["main"],
  "uptime": "0:05:00",
  "requests": 10,
  "errors": 0
}
```

---

## 🧠 核心特性

### L0-L4 类脑分层

| 层级 | 名称 | 存储 | TTL | 功能 |
|------|------|------|-----|------|
| **L0** | 感觉缓冲 | Redis | 5 分钟 | 瞬时记忆（情绪/意图识别） |
| **L1** | 工作记忆 | Redis | 2 小时 | 搜索缓存 |
| **L2** | 情景缓冲 | Redis | 24 小时 | 情景记忆 |
| **L3** | 长期记忆 | LanceDB | 永久 | 持久化存储 |
| **L4** | 概念层 | LanceDB | 永久 | 巩固生成的抽象知识 |

### 13 个核心工具

| 工具 | 功能 | 调用示例 |
|------|------|----------|
| `remember` | 显式记忆存储 | `remember({key, value})` |
| `search_memories` | 语义检索 | `search_memories({query, limit})` |
| `learn` | 6 步学习法 | `learn({title, content, category})` |
| `consolidate_memories` | 记忆巩固 | `consolidate_memories()` |
| `pattern_completion` | 模式完成（PageRank） | `pattern_completion({query, top_k})` |
| `cluster_activation` | 聚类激活（Louvain） | `cluster_activation({action, seed_memory_id})` |
| `multi_hop_search` | 多跳检索（BFS） | `multi_hop_search({query, hops, limit})` |
| `memory_stats` | 系统统计 | `memory_stats()` |
| `get_sensory` | L0 感觉缓冲状态 | `get_sensory({agent_id})` |
| `get_sensory_by_key` | L0 按 key 获取 | `get_sensory_by_key({key, agent_id})` |
| `clear_sensory` | L0 清除 | `clear_sensory({agent_id})` |
| `delegate_task` | 任务委派 | `delegate_task({description})` |
| `get_task_status` | 任务状态 | `get_task_status({taskId})` |

---

## 📊 架构设计

```
┌─────────────────────────────────────────┐
│           OpenClaw Gateway              │
├─────────────────────────────────────────┤
│         CortexMem Plugin                │
│  ┌─────────────────────────────────┐    │
│  │  TypeScript (index.ts)          │    │
│  │  - 13 个工具                     │    │
│  │  - before_prompt_build 钩子      │    │
│  │  - 自动记忆注入                  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
           ↓ HTTP (port 9721)
┌─────────────────────────────────────────┐
│      Embedding Server (Python)          │
│  ┌─────────────────────────────────┐    │
│  │  BGE-small-zh-v1.5 (512 维)      │    │
│  │  LanceDB + Redis                │    │
│  │  L0-L4 记忆管理                  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## 🛠️ 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `autoInject` | boolean | `true` | 自动注入相关记忆到 prompt |
| `autoSave` | boolean | `true` | 自动保存对话到记忆 |
| `maxMemories` | number | `3` | 每次注入的记忆数量 |
| `embeddingServerUrl` | string | `http://127.0.0.1:9721` | Embedding Server 地址 |
| `consolidateIntervalMs` | number | `21600000` | 巩固间隔（6 小时） |
| `minEpisodesForConsolidate` | number | `10` | 触发巩固的最小 episodes 数 |
| `disabledTools` | string[] | `[]` | 禁用的工具列表 |

---

## 📈 性能表现

| 操作 | 响应时间 | 说明 |
|------|----------|------|
| L0 缓存命中 | ~2ms | Redis 读取 |
| L1 搜索缓存 | ~8ms | Redis 读取 |
| 语义搜索 | ~50ms | LanceDB 向量检索 |
| 记忆保存 | ~100ms | LanceDB 写入 |
| 巩固流程 | ~55s/批 | 批量处理 |

---

## 🧪 测试

```bash
# 运行测试
npm test

# 测试覆盖
npm test -- --coverage

# 手动测试 Embedding Server
python3 server/embedding_server.py
curl http://127.0.0.1:9721/health
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [L0_INTEGRATION_REPORT.md](./L0_INTEGRATION_REPORT.md) | L0 感觉缓冲集成报告 |
| [IMPROVEMENT_REPORT.md](./IMPROVEMENT_REPORT.md) | v10 改进报告 |
| [monitoring/README.md](./monitoring/README.md) | 监控告警配置 |
| [docs/](./docs/) | 历史版本文档 |

---

## 🔧 故障排查

### Embedding Server 无法启动

```bash
# 检查端口占用
lsof -i :9721

# 查看日志
tail -f ~/.openclaw/evolution/logs/embedding_server.log

# 重新安装依赖
pip3 install -r server/requirements.txt
```

### 记忆检索失败

```bash
# 检查 LanceDB
ls -la server/data/lancedb/

# 检查 Redis
redis-cli ping

# 重启服务
openclaw gateway restart
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](./LICENSE) 文件了解详情。

---

## 🙏 致谢

- [OpenClaw](https://openclaw.ai) - AI 助理框架
- [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5) - 中文 Embedding 模型
- [LanceDB](https://lancedb.com) - 向量数据库
- [Redis](https://redis.io) - 缓存数据库

---

**CortexMem** — _Where Memory Meets Evolution_ 🧠

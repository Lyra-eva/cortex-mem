# ClawHub 官方插件市场提交指南

---

## ✅ 准备工作完成

- [x] npm 包发布完成（@ggvc/cortex-mem）
- [x] GitHub 仓库公开
- [x] README.md 完善
- [x] LICENSE 添加
- [x] CHANGELOG.md 更新

---

## 📋 提交方式

### 方式 1: 网页提交（推荐）

#### 步骤 1: 访问提交页面

打开浏览器访问：
```
https://clawhub.ai/submit
```

#### 步骤 2: 登录/注册

- 使用 GitHub 账号登录
- 或创建新账号

#### 步骤 3: 填写插件信息

**基本信息：**

| 字段 | 内容 |
|------|------|
| **Plugin Name** | `CortexMem` |
| **npm Package** | `@ggvc/cortex-mem` |
| **Version** | `1.0.0` |
| **Description** | `Brain-Inspired Memory System for OpenClaw (类脑记忆系统)` |
| **Repository URL** | `https://github.com/Lyra-eva/cortex-mem` |
| **Homepage** | `https://github.com/Lyra-eva/cortex-mem#readme` |
| **Author** | `ggvc` |
| **License** | `MIT` |

**关键词：**
```
memory, brain-inspired, semantic-search, vector-store, openclaw, plugin
```

**特性描述：**
```
- L0-L4 layered memory architecture
- 13 core memory management tools
- Semantic search with BGE embeddings
- Automatic memory consolidation
- Multi-agent support
- Emotion and intent recognition
```

**文档链接：**
```
https://github.com/Lyra-eva/cortex-mem/blob/main/README.md
```

#### 步骤 4: 上传截图（可选）

可以上传：
- 安装流程截图
- 功能演示截图
- 性能对比图表

#### 步骤 5: 提交审核

点击 **"Submit"** 按钮

**审核时间：** 1-3 个工作日

---

### 方式 2: API 提交

```bash
curl -X POST https://clawhub.ai/api/v1/plugins \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_CLAWHUB_TOKEN" \
  -d '{
    "name": "CortexMem",
    "npmPackage": "@ggvc/cortex-mem",
    "version": "1.0.0",
    "description": "Brain-Inspired Memory System for OpenClaw",
    "repository": "https://github.com/Lyra-eva/cortex-mem",
    "keywords": ["memory", "brain-inspired", "semantic-search"],
    "license": "MIT"
  }'
```

**获取 Token：**
1. 登录 https://clawhub.ai
2. 访问 Settings → API Tokens
3. 创建新 Token

---

### 方式 3: 通过 OpenClaw CLI（如果支持）

```bash
# 查看 marketplace 命令
openclaw plugins marketplace --help

# 提交插件（如果支持）
openclaw plugins marketplace submit @ggvc/cortex-mem
```

---

## 📊 提交信息模板

### 插件描述（英文）

```
CortexMem is a brain-inspired memory system for OpenClaw.

Features:
- L0-L4 layered memory architecture (sensory buffer to long-term memory)
- 13 core tools for memory management
- Semantic search with BGE embeddings (512 dimensions)
- Automatic memory consolidation and forgetting
- Multi-agent support with isolated memory spaces
- Emotion and intent recognition

Installation:
npm install @ggvc/cortex-mem

Documentation:
https://github.com/Lyra-eva/cortex-mem
```

### 插件描述（中文）

```
CortexMem 是一个为 OpenClaw 设计的类脑记忆系统。

核心功能：
- L0-L4 类脑记忆分层架构（从感觉缓冲到长期记忆）
- 13 个核心记忆管理工具
- BGE 语义搜索（512 维向量）
- 自动记忆巩固和遗忘机制
- 多智能体支持，独立记忆空间
- 情绪和意图识别

安装：
npm install @ggvc/cortex-mem

文档：
https://github.com/Lyra-eva/cortex-mem
```

---

## ✅ 审核检查清单

### 必需条件

- [x] npm 包已发布
- [x] GitHub 仓库公开
- [x] README.md 完整
- [x] LICENSE 文件
- [x] CHANGELOG.md 更新

### 推荐条件

- [x] 功能演示截图
- [x] 安装教程
- [x] API 文档
- [x] 示例代码
- [ ] 视频教程（可选）

---

## 📈 审核流程

### 阶段 1: 自动检查（5 分钟）

- npm 包验证
- GitHub 仓库验证
- 基础信息完整性

### 阶段 2: 人工审核（1-3 工作日）

- 功能完整性
- 文档质量
- 代码安全性
- 许可证合规

### 阶段 3: 上架发布

- 添加到 ClawHub 索引
- 公开到插件市场
- 邮件通知

---

## 🔗 相关链接

| 平台 | 链接 |
|------|------|
| **ClawHub 提交** | https://clawhub.ai/submit |
| **ClawHub 市场** | https://clawhub.ai |
| **npm 包** | https://www.npmjs.com/package/@ggvc/cortex-mem |
| **GitHub** | https://github.com/Lyra-eva/cortex-mem |

---

## 📝 提交后跟进

### 审核中

- 等待 1-3 个工作日
- 关注邮件通知
- 检查 ClawHub 后台状态

### 审核通过

- 插件上架到市场
- 收到确认邮件
- 可以开始推广

### 审核未通过

- 查看拒绝原因
- 根据反馈修改
- 重新提交

---

## 💡 推广建议

### 审核通过后

**1. OpenClaw Discord**
- 频道：#announcements
- 发布上架公告

**2. 社交媒体**
```
🎉 CortexMem 已上架 ClawHub！

🧠 类脑记忆系统
✅ L0-L4 分层架构
✅ 13 个核心工具
✅ 语义搜索 + 情绪识别

立即安装：
npm install @ggvc/cortex-mem

#OpenClaw #AI #Memory #OpenSource
```

**3. 技术博客**
- 知乎/掘金/Medium
- 架构设计文章
- 使用教程

---

_创建时间：2026-03-30_

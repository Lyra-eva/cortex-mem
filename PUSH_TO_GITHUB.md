# 推送代码到 GitHub 指南

---

## ✅ 已完成步骤

- [x] GitHub Token 配置
- [x] Git 凭证保存
- [x] Git 仓库初始化
- [x] 首次提交完成（88 个文件）

---

## 📋 待执行步骤

### 步骤 1: 创建 GitHub 仓库

**访问：** https://github.com/new

**填写信息：**

| 字段 | 内容 |
|------|------|
| **Owner** | `flyingplumage` |
| **Repository name** | `cortex-mem` |
| **Description** | `CortexMem — Brain-Inspired Memory System for OpenClaw (类脑记忆系统)` |
| **Visibility** | ✅ Public（开源） |
| **Initialize** | ❌ 全部不勾选 |

**点击：** "Create repository"

---

### 步骤 2: 推送代码

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem

# 已执行
git remote add origin https://github.com/flyingplumage/cortex-mem.git
git branch -M main

# 执行推送
git push -u origin main
```

**预期输出：**
```
Enumerating objects: 88, done.
Counting objects: 100% (88/88), done.
Delta compression using up to 8 threads
Compressing objects: 100% (85/85), done.
Writing objects: 100% (88/88), 45.2 KiB | 5.0 MiB/s, done.
Total 88 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/flyingplumage/cortex-mem.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

### 步骤 3: 验证推送

**访问：** https://github.com/flyingplumage/cortex-mem

**检查：**
- ✅ 代码文件已显示
- ✅ README.md 渲染正常
- ✅ 提交历史显示

---

### 步骤 4: 创建 GitHub Release

**访问：** https://github.com/flyingplumage/cortex-mem/releases/new

**填写信息：**

| 字段 | 内容 |
|------|------|
| **Tag version** | `v1.0.0` |
| **Release title** | `CortexMem v1.0.0 — Initial Release` |
| **Description** | 复制 CHANGELOG.md 内容 |
| **Set as latest** | ✅ 勾选 |

**点击：** "Publish release"

---

### 步骤 5: 发布到 npm

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem

# 登录 npm（如果未登录）
npm login

# 发布
npm publish --access public

# 验证
npm view @openclaw/cortex-mem
```

**预期输出：**
```
@openclaw/cortex-mem@1.0.0 | MIT | deps: 3 | versions: 1
CortexMem — Brain-Inspired Memory System for OpenClaw
```

---

### 步骤 6: 提交到 ClawHub

**访问：** https://clawhub.ai/submit

**填写信息：**

| 字段 | 内容 |
|------|------|
| **Plugin Name** | `CortexMem` |
| **npm Package** | `@openclaw/cortex-mem` |
| **Repository URL** | `https://github.com/flyingplumage/cortex-mem` |
| **Description** | `Brain-Inspired Memory System for OpenClaw` |
| **Keywords** | `memory, brain-inspired, semantic-search, vector-store` |

**点击：** "Submit"

---

## 🎯 快速推送命令

```bash
# 一键推送（复制粘贴）
cd /Users/lx/.openclaw/plugins/cortex-mem && git push -u origin main
```

---

## 📊 提交统计

| 指标 | 数值 |
|------|------|
| 文件数 | 88 个 |
| 代码行数 | ~20,264 行 |
| 提交哈希 | 56fb21d |
| 提交时间 | 2026-03-30 |

---

## 🔗 相关链接

- **GitHub 仓库:** https://github.com/flyingplumage/cortex-mem
- **npm 包页面:** https://www.npmjs.com/package/@openclaw/cortex-mem
- **ClawHub 市场:** https://clawhub.ai

---

_创建时间：2026-03-30_

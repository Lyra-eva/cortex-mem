# GitHub Token 配置指南

---

## 🔐 生成 GitHub Personal Access Token

### 步骤 1: 访问 Token 设置页面

打开浏览器访问：
```
https://github.com/settings/tokens
```

### 步骤 2: 生成新 Token

1. 点击 **"Generate new token"** 按钮
2. 选择 **"Generate new token (classic)"**

### 步骤 3: 填写 Token 信息

| 字段 | 填写内容 |
|------|----------|
| **Note** | `CortexMem Plugin Publish` |
| **Expiration** | `No expiration`（或选择 90 天） |

### 步骤 4: 选择权限（Scopes）

**必需权限：**

- ✅ **repo** - Full control of private repositories
  - `repo:status`
  - `repo_deployment`
  - `public_repo`
  - `repo:invite`
  - `security_events`

- ✅ **workflow** - Update GitHub Action workflows

- ✅ **read:org** - Read org membership

- ✅ **write:packages** - Upload packages to GitHub Package Registry

- ✅ **read:packages** - Download packages from GitHub Package Registry

**可选权限：**

- ✅ **gist** - Create gists（如果需要）
- ✅ **delete:packages** - 删除包（谨慎使用）

### 步骤 5: 生成并保存

1. 点击 **"Generate token"** 绿色按钮
2. **复制 Token**（以 `ghp_` 开头）
3. **立即保存**到安全位置（密码管理器等）

⚠️ **重要：** Token 只会显示一次，刷新页面后无法再次查看！

---

## 🔧 配置 Git 凭证

### 方式 1: 使用凭证存储（推荐）

```bash
# 1. 启用凭证存储
git config --global credential.helper store

# 2. 执行一次 git 操作（会提示输入凭证）
cd /Users/lx/.openclaw/plugins/cortex-mem
git push

# 3. 输入用户名和 Token
Username: flyingplumage
Password: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 4. 凭证会保存到 ~/.git-credentials
```

### 方式 2: 手动配置

```bash
# 1. 创建凭证文件
cat > ~/.git-credentials << EOF
https://flyingplumage:ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx@github.com
EOF

# 2. 设置权限
chmod 600 ~/.git-credentials

# 3. 启用凭证存储
git config --global credential.helper store
```

### 方式 3: 使用 macOS Keychain

```bash
# 启用 macOS Keychain 集成
git config --global credential.helper osxkeychain

# 然后执行 git push 时会自动保存到 Keychain
```

---

## ✅ 验证配置

### 测试 GitHub 连接

```bash
# 测试 API 连接
curl -u "flyingplumage:ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  https://api.github.com/user

# 预期输出包含你的用户信息
{
  "login": "flyingplumage",
  "id": 12345678,
  ...
}
```

### 测试 Git 操作

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem

# 初始化仓库
git init

# 添加文件
git add .

# 提交
git commit -m "Test commit"

# 推送（需要远程仓库）
git push origin main
```

---

## 🚀 创建 GitHub 仓库

### 步骤 1: 访问新建仓库页面

```
https://github.com/new
```

### 步骤 2: 填写仓库信息

| 字段 | 内容 |
|------|------|
| **Owner** | `flyingplumage`（或你的组织） |
| **Repository name** | `cortex-mem` |
| **Description** | `CortexMem — Brain-Inspired Memory System for OpenClaw` |
| **Visibility** | ✅ Public（开源项目） |
| **Initialize** | ❌ 不勾选（使用本地已有代码） |

### 步骤 3: 创建仓库

点击 **"Create repository"** 绿色按钮

### 步骤 4: 关联远程仓库

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem

# 添加远程仓库
git remote add origin https://github.com/flyingplumage/cortex-mem.git

# 推送代码
git branch -M main
git push -u origin main
```

---

## 📦 发布 npm 包（并行步骤）

### 发布到 npm

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem

# 登录 npm
npm login

# 发布
npm publish --access public

# 验证
npm view @openclaw/cortex-mem
```

---

## 🔗 提交到 ClawHub

### 步骤 1: 访问提交页面

```
https://clawhub.ai/submit
```

### 步骤 2: 填写插件信息

| 字段 | 内容 |
|------|------|
| **Plugin Name** | `CortexMem` |
| **npm Package** | `@openclaw/cortex-mem` |
| **Repository URL** | `https://github.com/flyingplumage/cortex-mem` |
| **Description** | `Brain-Inspired Memory System for OpenClaw` |
| **Keywords** | `memory, brain-inspired, semantic-search, vector-store` |

### 步骤 3: 提交审核

点击 **"Submit"** 按钮

**审核时间：** 1-3 个工作日

---

## 🎯 完整流程总结

```
1. 生成 GitHub Token
   ↓
2. 配置 Git 凭证
   ↓
3. 创建 GitHub 仓库
   ↓
4. 推送代码到 GitHub
   ↓
5. 发布到 npm
   ↓
6. 提交到 ClawHub
   ↓
7. 等待审核（1-3 工作日）
   ↓
8. 上架成功
```

---

## ⚠️ 安全提示

### Token 安全

- ✅ 不要将 Token 提交到 Git 仓库
- ✅ 使用 `.gitignore` 排除敏感文件
- ✅ 定期轮换 Token（建议 90 天）
- ✅ 使用最小权限原则

### .gitignore 示例

```gitignore
# 敏感信息
.git-credentials
.env
*.key
*.pem

# 依赖
node_modules/
__pycache__/
*.pyc

# 数据
server/data/
server/logs/

# 构建产物
*.tgz
dist/

# 系统文件
.DS_Store
Thumbs.db
```

---

## 🆘 故障排查

### 问题 1: Token 格式错误

**错误：** `❌ Token 格式错误`

**解决：** 确保 Token 以 `ghp_` 开头

### 问题 2: 认证失败

**错误：** `Authentication failed`

**解决：**
```bash
# 清除旧凭证
rm ~/.git-credentials
git config --global --unset credential.helper

# 重新配置
git config --global credential.helper store
git push  # 会提示重新输入
```

### 问题 3: 权限不足

**错误：** `403 Forbidden`

**解决：** 检查 Token 权限是否包含 `repo` 和 `workflow`

---

## 📞 获取帮助

- **GitHub 文档:** https://docs.github.com/en/authentication
- **OpenClaw Discord:** https://discord.gg/clawd
- **CortexMem Issues:** https://github.com/flyingplumage/cortex-mem/issues

---

_配置完成后，执行以下命令推送代码：_

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem
git init
git add .
git commit -m "Initial release: CortexMem v1.0.0"
git remote add origin https://github.com/flyingplumage/cortex-mem.git
git push -u origin main
```

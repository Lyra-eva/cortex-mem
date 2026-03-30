# npm 发布指南

---

## ⚠️ 需要手动登录 npm

GitHub Token 不能用于 npm 认证，需要使用 npm 账号登录。

---

## 🔐 方式 1: 网页验证码登录（推荐）

### 步骤 1: 执行登录命令

```bash
npm login
```

### 步骤 2: 访问验证码链接

终端会显示：
```
Create your account at:
https://www.npmjs.com/login/cli/xxx-xxx-xxx
```

### 步骤 3: 输入验证码

在网页上输入终端显示的验证码

### 步骤 4: 发布

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem
npm publish --access public
```

---

## 🔐 方式 2: 使用 npm Access Token

### 步骤 1: 获取 npm Token

1. 访问 https://www.npmjs.com/settings/your-username/tokens
2. 点击 "Generate New Token"
3. 选择 "Automation Token"
4. 复制 Token（以 `npm_` 开头）

### 步骤 2: 配置 .npmrc

```bash
cat > ~/.npmrc << EOF
//registry.npmjs.org/:_authToken=npm_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
registry=https://registry.npmjs.org/
EOF
```

### 步骤 3: 验证登录

```bash
npm whoami
```

### 步骤 4: 发布

```bash
cd /Users/lx/.openclaw/plugins/cortex-mem
npm publish --access public
```

---

## 📦 发布验证

```bash
# 查看包信息
npm view @openclaw/cortex-mem

# 预期输出：
@openclaw/cortex-mem@1.0.0 | MIT | deps: 3 | versions: 1
CortexMem — Brain-Inspired Memory System for OpenClaw
```

---

## 🎯 快速发布命令

```bash
# 一键登录 + 发布（复制粘贴）
npm login && cd /Users/lx/.openclaw/plugins/cortex-mem && npm publish --access public && npm view @openclaw/cortex-mem
```

---

## ⚠️ 常见问题

### 问题 1: 包已存在

**错误：** `npm error 403 Forbidden - PUT https://registry.npmjs.org/@openclaw%2fcortex-mem - You cannot publish over previously published versions`

**解决：** 修改 package.json 版本号

```json
{
  "version": "1.0.1"  // 递增版本号
}
```

### 问题 2: 权限不足

**错误：** `npm error 403 403 Forbidden - PUT https://registry.npmjs.org/@openclaw%2fcortex-mem - You do not have permission to publish to this package`

**解决：** 确保使用正确的 npm 账号登录

### 问题 3: 网络问题

**错误：** `npm error code ETIMEDOUT`

**解决：** 使用国内镜像

```bash
npm config set registry https://registry.npmmirror.com
npm login
npm publish
```

---

## 📊 发布检查清单

- [ ] npm 账号准备
- [ ] 执行 npm login
- [ ] 验证 npm whoami
- [ ] 执行 npm publish
- [ ] 验证 npm view
- [ ] 检查 npm 包页面

---

## 🔗 相关链接

- **npm 登录:** https://www.npmjs.com/login
- **npm Token 设置:** https://www.npmjs.com/settings/tokens
- **CortexMem npm 页面:** https://www.npmjs.com/package/@openclaw/cortex-mem (待发布)

---

_创建时间：2026-03-30_

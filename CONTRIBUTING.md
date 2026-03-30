# 贡献指南

感谢你对 CortexMem 的兴趣！本文档将指导你如何参与项目贡献。

---

## 🚀 快速开始

### 1. Fork 仓库

点击 GitHub 页面右上角的 "Fork" 按钮。

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/cortex-mem.git
cd cortex-mem
```

### 3. 安装依赖

```bash
npm install
```

### 4. 创建分支

```bash
git checkout -b feature/your-feature-name
```

---

## 📝 开发规范

### 代码风格

- **TypeScript**: 遵循 ESLint 配置
- **Python**: 遵循 PEP 8
- **提交信息**: 使用 Conventional Commits

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type 类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例：**
```
feat(memory): 添加 L0 感觉缓冲功能

- 实现 saveToSensoryBuffer 函数
- 添加 get_sensory 工具
- 集成情绪识别

Closes #123
```

---

## 🧪 测试要求

### 运行测试

```bash
# 单元测试
npm test

# 测试覆盖
npm test -- --coverage

# Python 服务器测试
python3 server/test_embedding.py
```

### 测试覆盖要求

- 新功能必须有测试
- 核心功能覆盖率 >80%
- 不得降低现有覆盖率

---

## 📤 提交 PR

### 1. 更新代码

```bash
git pull upstream main
```

### 2. 运行测试

```bash
npm test
npm run build
```

### 3. 提交 PR

1. 推送到你的 Fork
2. 在 GitHub 创建 Pull Request
3. 填写 PR 描述模板

### PR 描述模板

```markdown
## 变更说明

简要描述此 PR 的目的。

## 相关 Issue

Closes #123

## 测试计划

- [ ] 单元测试通过
- [ ] 手动测试完成
- [ ] 文档已更新

## 截图（如适用）

添加相关截图。
```

---

## 📚 文档贡献

### 代码注释

- TypeScript: JSDoc 格式
- Python: Google Style Docstrings

### 文档更新

- README.md 保持最新
- 新功能需添加文档
- 变更需更新 CHANGELOG

---

## 🐛 报告 Bug

### Bug 报告模板

```markdown
**描述问题**
清晰简洁地描述问题。

**复现步骤**
1. 执行步骤 1
2. 执行步骤 2
3. 观察到错误

**预期行为**
描述预期结果。

**环境信息**
- OS: macOS 14.0
- Node: v20.0.0
- Python: 3.9
- CortexMem: v1.0.0

**日志**
```
粘贴相关日志
```

**截图**
如适用，添加截图。
```

---

## 💡 功能建议

### 功能建议模板

```markdown
**功能描述**
清晰简洁地描述功能。

**使用场景**
描述使用场景和目标用户。

**实现建议**
如有，提供实现思路。

**替代方案**
考虑过的其他方案。
```

---

## 📋 Code Review 清单

### 提交前自检

- [ ] 代码通过 lint 检查
- [ ] 测试通过
- [ ] 文档已更新
- [ ] 提交信息规范
- [ ] 无敏感信息泄露

### Reviewer 检查

- [ ] 代码功能正确
- [ ] 代码风格一致
- [ ] 测试覆盖充分
- [ ] 文档完整
- [ ] 无性能退化

---

## 🎯 贡献领域

### 高优先级

- [ ] 测试覆盖提升
- [ ] 性能优化
- [ ] 文档完善
- [ ] Bug 修复

### 中优先级

- [ ] 新功能开发
- [ ] 工具增强
- [ ] 监控改进

### 低优先级

- [ ] 代码重构
- [ ] 技术债务清理
- [ ] 示例代码

---

## 📞 联系方式

- **GitHub Issues**: [cortex-mem/issues](https://github.com/openclaw/cortex-mem/issues)
- **Discord**: [OpenClaw Community](https://discord.gg/clawd)
- **Email**: team@openclaw.ai

---

感谢你的贡献！🎉

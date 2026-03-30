#!/bin/bash
# CortexMem GitHub 仓库配置脚本

set -e

echo "🔧 CortexMem GitHub 仓库配置"
echo "=============================="
echo ""

# 配置变量
GITHUB_USERNAME="flyingplumage"
REPO_NAME="cortex-mem"
REPO_DESCRIPTION="CortexMem — Brain-Inspired Memory System for OpenClaw (类脑记忆系统)"

echo "1. 配置 Git 凭证"
echo "----------------"
echo "请输入你的 GitHub Personal Access Token:"
echo "（访问 https://github.com/settings/tokens 生成）"
echo ""
read -s -p "Token (ghp_开头): " GITHUB_TOKEN
echo ""
echo ""

if [[ ! "$GITHUB_TOKEN" =~ ^ghp_ ]]; then
    echo "❌ Token 格式错误，应该以 ghp_ 开头"
    exit 1
fi

# 保存凭证
echo "https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
git config --global credential.helper store

echo "✅ Git 凭证已配置"
echo ""

echo "2. 初始化本地仓库"
echo "------------------"
cd /Users/lx/.openclaw/plugins/cortex-mem

if [ -d ".git" ]; then
    echo "⚠️ Git 仓库已存在，跳过初始化"
else
    git init
    echo "✅ Git 仓库已初始化"
fi
echo ""

echo "3. 添加所有文件"
echo "---------------"
git add .
echo "✅ 文件已添加到暂存区"
echo ""

echo "4. 首次提交"
echo "-----------"
git commit -m "Initial release: CortexMem v1.0.0

- Brain-Inspired Memory System for OpenClaw
- L0-L4 layered memory architecture
- 13 core tools for memory management
- Semantic search with BGE embeddings
- Automatic memory consolidation
- Multi-agent support

See: README.md for usage guide"

echo "✅ 首次提交完成"
echo ""

echo "5. 创建 GitHub 远程仓库"
echo "------------------------"
echo "请前往以下地址创建新仓库："
echo "https://github.com/new"
echo ""
echo "填写信息："
echo "  Repository name: ${REPO_NAME}"
echo "  Description: ${REPO_DESCRIPTION}"
echo "  Visibility: Public"
echo "  ✅ Add a README file: NO"
echo "  ✅ Add .gitignore: NO"
echo "  ✅ Add a license: NO"
echo ""
read -p "创建完成后按回车继续..."

# 设置远程仓库
git remote add origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git
echo "✅ 远程仓库已添加"
echo ""

echo "6. 推送到 GitHub"
echo "----------------"
git branch -M main
git push -u origin main
echo "✅ 代码已推送到 GitHub"
echo ""

echo "7. 创建 GitHub Release"
echo "----------------------"
echo "请前往以下地址创建 Release："
echo "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/releases/new"
echo ""
echo "填写信息："
echo "  Tag version: v1.0.0"
echo "  Release title: CortexMem v1.0.0 — Initial Release"
echo "  Description: 复制 CHANGELOG.md 内容"
echo "  ✅ Set as the latest release"
echo ""

echo "=============================="
echo "✅ GitHub 配置完成！"
echo ""
echo "下一步："
echo "1. 发布到 npm: npm publish --access public"
echo "2. 提交到 clawhub: https://clawhub.ai/submit"
echo ""

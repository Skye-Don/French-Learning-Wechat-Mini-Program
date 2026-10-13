#!/usr/bin/env bash
# ============================================================
# 一键把项目所有文档、代码上传到 GitHub（Git Bash / macOS / Linux 通用）
#
# 用法（在项目根目录 french-miniprogram/ 下执行）：
#   bash scripts/git_push.sh                     # 首次：初始化并推送
#   bash scripts/git_push.sh "修复打卡幂等问题"    # 日常：带说明提交
#
# 仓库：https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program
# ============================================================
set -euo pipefail

REPO_URL="https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program.git"
MSG="${1:-update: 项目更新 $(date '+%Y-%m-%d %H:%M')}"

cd "$(dirname "$0")/.."

# 0) 安全检查：确认没有密钥文件会被提交
if ls .env backend/.env 2>/dev/null | grep -q .; then
  echo "❌ 检测到 .env 文件，已被 .gitignore 排除；请确认它不在 git 追踪中："
  git check-ignore -v .env backend/.env 2>/dev/null || true
fi

# 1) 初始化 / 绑定远程
if [ ! -d .git ]; then
  echo "→ 初始化 git 仓库"
  git init
  git branch -M main
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "→ 绑定远程仓库 $REPO_URL"
  git remote add origin "$REPO_URL"
fi

# 2) 提交
echo "→ 暂存全部文件（.env / *.db / __pycache__ 已被 .gitignore 排除）"
git add -A
if git diff --cached --quiet; then
  echo "✓ 没有需要提交的变更"
else
  git commit -m "$MSG"
fi

# 3) 推送
echo "→ 推送到 origin/main"
if git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git pull --rebase origin main || true   # 远端有提交时先 rebase，避免被拒
fi
git push -u origin main

echo ""
echo "✅ 已上传：https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program"
echo "   首次推送时浏览器会弹出 GitHub 登录（或提示安装 Git Credential Manager），按提示授权即可。"

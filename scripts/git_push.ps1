# ============================================================
# 一键把项目所有文档、代码上传到 GitHub（Windows PowerShell 版）
#
# 用法（在项目根目录 french-miniprogram/ 下，右键"在终端中打开"）：
#   powershell -ExecutionPolicy Bypass -File scripts\git_push.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\git_push.ps1 -Message "修复打卡幂等问题"
#
# 仓库：https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program
# ============================================================
param([string]$Message = "")

$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program.git"
if (-not $Message) { $Message = "update: 项目更新 $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }

Set-Location (Join-Path $PSScriptRoot "..")

# 1) 初始化 / 绑定远程
if (-not (Test-Path ".git")) {
    Write-Host "-> 初始化 git 仓库"
    git init | Out-Null
    git branch -M main
}
$remote = git remote 2>$null | Select-Object -First 1
if (-not $remote) {
    Write-Host "-> 绑定远程仓库 $repoUrl"
    git remote add origin $repoUrl
}

# 2) 提交（.env / *.db / __pycache__ 已被 .gitignore 排除）
Write-Host "-> 暂存全部文件"
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "OK 没有需要提交的变更"
} else {
    git commit -m $Message | Out-Null
    Write-Host ("-> 已提交 {0} 个文件" -f $staged.Count)
}

# 3) 推送
Write-Host "-> 推送到 origin/main"
git push -u origin main

Write-Host ""
Write-Host "已上传: https://github.com/Skye-Don/French-Learning-Wechat-Mini-Program"
Write-Host "首次推送会弹出 GitHub 登录窗口（Git Credential Manager），按提示授权即可。"

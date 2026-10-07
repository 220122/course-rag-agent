@echo off
chcp 936 >nul
title RAG-推送到GitHub
cd /d %~dp0

echo ============================================================
echo   将本项目推送到 GitHub
echo ============================================================
echo.

REM 检查是否已配置远端
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo 未配置远端，正在添加 origin ...
    git remote add origin https://github.com/220122/course-rag-agent.git
)

echo 远端地址：
git remote get-url origin
echo.

echo 本地提交数：
git rev-list --count HEAD
echo.

echo ------------------------------------------------------------
echo  首次推送需要登录 GitHub，请注意：
echo   1. 若弹出浏览器，请按提示授权登录
echo   2. 若提示输入 Username：填你的 GitHub 用户名 220122
echo   3. 若提示输入 Password：必须粘贴 Personal Access Token
echo      （GitHub 已不支持用登录密码推送）
echo      Token 生成地址：https://github.com/settings/tokens
echo      勾选 repo 权限即可
echo ------------------------------------------------------------
echo.

pause
echo.
echo 正在推送...
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  推送失败，常见原因：
    echo   1. GitHub 上还没有这个仓库
    echo      请先打开 https://github.com/new
    echo      仓库名填 course-rag-agent
    echo      不要勾选 Add a README file / .gitignore / license
    echo      然后重新双击本脚本
    echo   2. 认证失败：Password 处要粘贴 Personal Access Token
    echo   3. 远端已有内容导致冲突：先执行 git pull --rebase origin main
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  推送成功！
echo  仓库地址：https://github.com/220122/course-rag-agent
echo ============================================================
pause

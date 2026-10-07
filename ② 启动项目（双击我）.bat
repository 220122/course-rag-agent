@echo off
chcp 65001 >nul
title RAG-启动器
cd /d %~dp0

REM 未安装则提示先运行安装脚本
if not exist backend\.venv (
    echo 检测到尚未安装环境，请先双击运行「① 首次安装（双击我）.bat」
    pause
    exit /b 1
)

echo 正在启动后端服务（窗口 1）...
start "RAG-Backend" cmd /k "chcp 65001 >nul && cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000"

echo 正在启动前端服务（窗口 2）...
start "RAG-Frontend" cmd /k "chcp 65001 >nul && cd /d %~dp0frontend && npm run dev"

echo.
echo 等待服务就绪（约 8 秒）...
timeout /t 8 /nobreak >nul

echo 正在打开浏览器...
start http://localhost:5173

echo.
echo 已启动！使用完毕后请双击「③ 停止项目（双击我）.bat」关闭服务。
timeout /t 3 /nobreak >nul
exit

@echo off
chcp 65001 >nul
title RAG-首次安装
cd /d %~dp0

echo ============================================================
echo   课程知识问答 RAG 智能体 - 首次环境安装
echo   全程自动，使用国内镜像下载，请耐心等待 3-8 分钟
echo ============================================================
echo.

REM -------------------- 后端依赖 --------------------
echo [1/4] 检查后端配置文件 .env ...
cd backend
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo 已自动生成 backend\.env，接下来会打开记事本：
    echo 请把 ARK_API_KEY 改成你自己的豆包 API Key，
    echo 并确认 CHAT_MODEL、EMBEDDING_MODEL 为你的模型接入点，保存后关闭记事本。
    echo.
    pause
    notepad .env
)

echo.
echo [2/4] 创建 Python 虚拟环境并安装后端依赖（清华镜像）...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo 后端依赖安装失败，请把本窗口报错信息截图反馈。
    pause
    exit /b 1
)
cd ..

REM -------------------- 前端依赖 --------------------
echo.
echo [3/4] 配置 npm 国内镜像（淘宝）...
call npm config set registry https://registry.npmmirror.com

echo.
echo [4/4] 安装前端依赖 ...
cd frontend
call npm install
if errorlevel 1 (
    echo.
    echo 前端依赖安装失败，请把本窗口报错信息截图反馈。
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================================
echo   安装完成！以后直接双击「② 启动项目（双击我）.bat」即可
echo ============================================================
pause

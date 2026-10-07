@echo off
chcp 936 >nul
title RAG-停止器

echo 正在关闭后端服务...
taskkill /F /T /FI "WINDOWTITLE eq RAG-Backend*" >nul 2>&1

echo 正在关闭前端服务...
taskkill /F /T /FI "WINDOWTITLE eq RAG-Frontend*" >nul 2>&1

echo.
echo 服务已全部关闭。
timeout /t 2 /nobreak >nul
exit

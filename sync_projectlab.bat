@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] 更新项目索引...
python build_index.py

echo [2/3] 提交本地变更...
git add -A
git commit -m "chore(ProjectLab): update index and notes"

echo [3/3] 推送到 GitHub...
git push origin main

echo.
echo [OK] 已同步到 GitHub。
pause

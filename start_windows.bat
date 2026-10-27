@echo off
if not exist .venv\Scripts\python.exe (echo Create environment first: py -3.11 -m venv .venv & pause & exit /b 1)
.venv\Scripts\python.exe run.py
pause

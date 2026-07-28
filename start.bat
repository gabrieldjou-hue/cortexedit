@echo off
echo ============================================
echo   CortexEdit - AI Video Post-Production
echo ============================================
echo.
echo Iniciando servidor em http://localhost:8000
echo Pressione CTRL+C para parar.
echo.
cd /d "%~dp0backend"
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause

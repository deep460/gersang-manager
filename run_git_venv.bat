@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ===================================================
echo   my_integrator 자동 업데이트 및 실행
echo ===================================================

where git >nul 2>nul
if %errorlevel% == 0 (
    echo [1/3] 최신 코드를 불러오는 중입니다 (git pull)...
    git pull
)

if not exist "venv" (
    echo.
    echo [2/3] 가상환경(venv)을 생성 중입니다...
    python -m venv venv
    
    echo [3/3] 필수 패키지를 설치 중입니다...
    call .\venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo [2/3] 가상환경 활성화 중...
    call .\venv\Scripts\activate
)

echo.
echo my_integrator 실행 중...
python my_integrator/main_integrator.py

pause
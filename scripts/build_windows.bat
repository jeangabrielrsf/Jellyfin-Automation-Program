@echo off
echo Building Jellyfin Automation for Windows...

REM Build frontend
cd frontend
call npm install
call npm run build
cd ..

REM Install backend dependencies
cd backend
call pip install -r requirements.txt
call pip install pyinstaller

REM Build backend executable with PyInstaller
call pyinstaller --onefile --name "JellyfinAutomation" ^
  --add-data "../frontend/dist;frontend/dist" ^
  --hidden-import sqlalchemy ^
  --hidden-import psycopg2 ^
  --hidden-import alembic ^
  --hidden-import httpx ^
  app/main.py

cd ..

echo Build complete! Executable is in backend/dist/JellyfinAutomation.exe
echo.
echo To run:
echo   1. Make sure PostgreSQL is running
echo   2. Copy .env.example to .env and configure
echo   3. Run backend/dist/JellyfinAutomation.exe
echo.
pause

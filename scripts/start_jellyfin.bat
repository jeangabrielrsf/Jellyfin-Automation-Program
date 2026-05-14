@echo off
title Jellyfin Automation - Starting Docker Containers
echo Aguardando Docker Desktop iniciar...

:loop
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 5 /nobreak >nul
    goto loop
)

echo Docker pronto. Subindo containers...
wsl -d Ubuntu docker compose -f "C:\Users\jeanfrusca\Projetos\jellyfin_automation\docker-compose.yml" up -d

echo Containers iniciados com sucesso!

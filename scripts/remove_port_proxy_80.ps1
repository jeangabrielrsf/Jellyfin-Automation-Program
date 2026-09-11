# Remover port proxy da porta 80
# Execute como Administrador no PowerShell

Write-Host "=== Removendo port proxy da porta 80 ===" -ForegroundColor Cyan

# Listar todos os port proxies
Write-Host "`nPort proxies atuais:" -ForegroundColor Yellow
netsh interface portproxy show all

# Remover port proxy da porta 80 (todas as variantes)
Write-Host "`nRemovendo port proxies da porta 80..." -ForegroundColor Yellow

# IPv4 para IPv4
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=127.0.0.1 2>$null
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=* 2>$null

# IPv4 para IPv6
netsh interface portproxy delete v4tov6 listenport=80 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov6 listenport=80 listenaddress=127.0.0.1 2>$null

# IPv6 para IPv4
netsh interface portproxy delete v6tov4 listenport=80 listenaddress=:: 2>$null
netsh interface portproxy delete v6tov4 listenport=80 listenaddress=* 2>$null

# IPv6 para IPv6
netsh interface portproxy delete v6tov6 listenport=80 listenaddress=:: 2>$null
netsh interface portproxy delete v6tov6 listenport=80 listenaddress=* 2>$null

Write-Host "Port proxies removidos." -ForegroundColor Green

# Verificar se ainda há algo na porta 80
Write-Host "`n=== Verificação ===" -ForegroundColor Cyan
Write-Host "Port proxies restantes:" -ForegroundColor Yellow
netsh interface portproxy show all

Write-Host "`nVerificando porta 80..." -ForegroundColor Yellow
$port80 = netstat -ano | findstr "LISTENING" | findstr ":80 "
if ($port80) {
    Write-Host "ALERTA: Algo ainda na porta 80:" -ForegroundColor Red
    Write-Host $port80 -ForegroundColor Red
} else {
    Write-Host "Porta 80 liberada!" -ForegroundColor Green
}

Write-Host "`n=== Próximos passos ===" -ForegroundColor Cyan
Write-Host "No WSL2, execute:" -ForegroundColor White
Write-Host "  cd /home/jeanfrusca/Projetos/jellyfin_automation" -ForegroundColor Yellow
Write-Host "  docker compose down frontend" -ForegroundColor Yellow
Write-Host "  docker compose up -d frontend" -ForegroundColor Yellow

# Diagnosticar e liberar porta 80 no Windows
# Execute como Administrador no PowerShell

Write-Host "=== Diagnosticando porta 80 ===" -ForegroundColor Cyan

# 1. Verificar port proxies
Write-Host "`n1. Port proxies ativos:" -ForegroundColor Yellow
$proxies = netsh interface portproxy show all
if ($proxies -match "80") {
    Write-Host "Port proxy encontrado na porta 80!" -ForegroundColor Red
    Write-Host "Removendo port proxy..." -ForegroundColor Yellow
    netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0
    netsh interface portproxy delete v4tov4 listenport=80 listenaddress=127.0.0.1
    Write-Host "Port proxy removido." -ForegroundColor Green
} else {
    Write-Host "Nenhum port proxy na porta 80." -ForegroundColor Green
}

# 2. Verificar processos na porta 80
Write-Host "`n2. Processos usando porta 80:" -ForegroundColor Yellow
$connections = netstat -ano | findstr ":80 "
if ($connections) {
    Write-Host $connections -ForegroundColor Red
    
    # Extrair PIDs
    $pids = $connections | ForEach-Object {
        if ($_ -match '\s+(\d+)\s*$') { $matches[1] }
    } | Select-Object -Unique
    
    foreach ($pid in $pids) {
        if ($pid -and $pid -ne "0") {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "`nProcesso: $($process.ProcessName) (PID: $pid)" -ForegroundColor Red
                Write-Host "Comando: $($process.Path)" -ForegroundColor Gray
                
                # Parar serviços conhecidos que usam porta 80
                if ($process.ProcessName -in @("w3wp", "http", "svchost", "sqlservr")) {
                    Write-Host "Tentando parar serviço..." -ForegroundColor Yellow
                    
                    # Tentar parar via serviço
                    $service = Get-Service | Where-Object { $_.Status -eq 'Running' -and $_.DisplayName -match $process.ProcessName }
                    if ($service) {
                        Write-Host "Parando serviço: $($service.Name)" -ForegroundColor Yellow
                        Stop-Service -Name $service.Name -Force -ErrorAction SilentlyContinue
                    }
                    
                    # Mata o processo se ainda estiver rodando
                    $process.Refresh()
                    if (!$process.HasExited) {
                        Write-Host "Matando processo..." -ForegroundColor Yellow
                        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
    }
} else {
    Write-Host "Nenhum processo usando porta 80." -ForegroundColor Green
}

# 3. Verificar serviços IIS
Write-Host "`n3. Verificando IIS..." -ForegroundColor Yellow
$iisService = Get-Service -Name "W3SVC" -ErrorAction SilentlyContinue
if ($iisService -and $iisService.Status -eq 'Running') {
    Write-Host "IIS está rodando. Parando..." -ForegroundColor Yellow
    Stop-Service -Name "W3SVC" -Force
    Write-Host "IIS parado." -ForegroundColor Green
} else {
    Write-Host "IIS não está rodando." -ForegroundColor Green
}

# 4. Verificar SQL Server Reporting Services
Write-Host "`n4. Verificando SQL Server Reporting Services..." -ForegroundColor Yellow
$ssrsService = Get-Service -Name "ReportServer*" -ErrorAction SilentlyContinue
if ($ssrsService -and $ssrsService.Status -eq 'Running') {
    Write-Host "SQL Server Reporting Services está rodando. Parando..." -ForegroundColor Yellow
    Stop-Service -Name $ssrsService.Name -Force
    Write-Host "SQL Server Reporting Services parado." -ForegroundColor Green
} else {
    Write-Host "SQL Server Reporting Services não está rodando." -ForegroundColor Green
}

# 5. Verificação final
Write-Host "`n=== Verificação final ===" -ForegroundColor Cyan
Start-Sleep -Seconds 2
$finalCheck = netstat -ano | findstr ":80 "
if ($finalCheck) {
    Write-Host "ALERTA: Porta 80 ainda em uso!" -ForegroundColor Red
    Write-Host $finalCheck -ForegroundColor Red
    Write-Host "`nExecute este script novamente ou reinicie o Windows." -ForegroundColor Yellow
} else {
    Write-Host "Porta 80 liberada com sucesso!" -ForegroundColor Green
    Write-Host "Agora execute: docker compose up -d" -ForegroundColor Cyan
}

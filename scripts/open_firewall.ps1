# Abre portas no Windows Firewall para acesso LAN ao Jellyfin Automation
# Execute como Administrador no PowerShell do Windows

Write-Host "Abrindo portas no Firewall para Jellyfin Automation..." -ForegroundColor Cyan

$ports = @(8000, 3001)
$description = "Jellyfin Automation - {0}"

foreach ($port in $ports) {
    $name = if ($port -eq 8000) { "JFA Backend" } else { "JFA Frontend" }

    $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Regra '$name' ja existe na porta $port, pulando." -ForegroundColor Yellow
        continue
    }

    New-NetFirewallRule `
        -DisplayName $name `
        -Direction Inbound `
        -LocalPort $port `
        -Protocol TCP `
        -Action Allow `
        -Profile Private | Out-Null

    Write-Host "Regra '$name' criada na porta $port." -ForegroundColor Green
}

Write-Host "`nPortas liberadas! Agora acesse http://<seu-ip>:3001 de qualquer dispositivo na rede." -ForegroundColor Cyan

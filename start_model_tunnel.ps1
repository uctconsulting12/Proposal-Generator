# Starts Ollama + an ngrok tunnel on your STATIC domain, so the public URL the
# cloud backend uses never changes. Run this once whenever your PC boots.
#
# Usage:
#   ./start_model_tunnel.ps1                      (uses $Domain below)
#   ./start_model_tunnel.ps1 -Domain my.ngrok-free.app

param(
    # Paste your claimed static ngrok domain here so you can just run the script.
    [string]$Domain = "pegasus-accurate-positively.ngrok-free.app"
)

if ($Domain -like "PASTE-*") {
    Write-Host "Edit this script and set -Domain to your static ngrok domain first." -ForegroundColor Red
    exit 1
}

# Ollama must listen on all interfaces so the tunnel can reach it.
$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:OLLAMA_ORIGINS = "*"

Write-Host "Starting Ollama (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$env:OLLAMA_HOST='0.0.0.0:11434'; `$env:OLLAMA_ORIGINS='*'; ollama serve"
)

Start-Sleep -Seconds 3

Write-Host "Starting ngrok tunnel on $Domain (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "ngrok http 11434 --host-header=`"localhost:11434`" --domain=$Domain"
)

Write-Host ""
Write-Host "Set this ONCE on your cloud host (Render) and never change it again:" -ForegroundColor Green
Write-Host "  COPILOT_OLLAMA_URL=https://$Domain/api/chat" -ForegroundColor Yellow
Write-Host ""
Write-Host "Verify in ~10s:  curl https://$Domain/api/tags" -ForegroundColor Cyan

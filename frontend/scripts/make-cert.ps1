# Certificat HTTPS local pour tester sur téléphone (la caméra exige HTTPS).
# Usage (dossier frontend) : npm run cert   puis   npm run dev:phone
# Le certificat est valable 30 jours, pour localhost et les adresses IP de ce PC.
# Le téléphone affichera un avertissement la première fois : « Paramètres avancés » > « Continuer ».
# Fichiers dans .certs/ (jamais envoyés sur GitHub).
$ErrorActionPreference = 'Stop'

$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) { $openssl = 'C:\Program Files\Git\usr\bin\openssl.exe' }
if (-not (Test-Path $openssl)) { throw "openssl introuvable : installez Git pour Windows." }

$san = 'DNS:localhost,IP:127.0.0.1'
$ips = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
  Select-Object -ExpandProperty IPAddress
foreach ($ip in $ips) { $san += ",IP:$ip" }

New-Item -ItemType Directory -Force -Path .certs | Out-Null
# openssl écrit sa progression sur stderr : PowerShell 5.1 la prendrait pour une erreur.
$ErrorActionPreference = 'Continue'
& $openssl req -x509 -newkey rsa:2048 -nodes -days 30 `
  -keyout .certs/key.pem -out .certs/cert.pem `
  -subj '/CN=BAOBIA demo' -addext "subjectAltName=$san" 2>$null
if ($LASTEXITCODE -ne 0) { throw "openssl a échoué." }

Write-Host "Certificat créé dans .certs/ pour : $san"
Write-Host "Sur le téléphone (même Wi-Fi) : https://<adresse-IP-de-ce-PC>:5173"

# Instala en TU Claude Code (nivel usuario) solo las 6 herramientas aprobadas. Ejecutar en PowerShell de Windows:
#   powershell -ExecutionPolicy Bypass -File .\instalar-herramientas-claude.ps1
# Si un paso falla, el script se detiene y muestra el error: no improvisa.

$ErrorActionPreference = "Stop"

# --- telemetria apagada
$env:DO_NOT_TRACK = "1"
$env:DISABLE_TELEMETRY = "1"
$env:IMPECCABLE_NO_TELEMETRY = "1"

# --- localizar claude
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $claude) {
    $c = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
    if ($c) { $claude = $c.FullName }
}
if (-not $claude) { throw "No encontre claude ni en el PATH ni en la extension de VS Code." }
Write-Host "Usando claude: $claude"

function Paso($titulo, [scriptblock]$cmd) {
    Write-Host ""
    Write-Host "== $titulo" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "Fallo el paso '$titulo' (codigo $LASTEXITCODE). Copiame el error de arriba y que probaste." }
}

# --- backup con fecha
$fecha = Get-Date -Format "yyyyMMdd-HHmmss"
$bk = "$env:USERPROFILE\.claude\backups"
New-Item -ItemType Directory -Force -Path $bk | Out-Null
foreach ($f in @("$env:USERPROFILE\.claude\settings.json", "$env:USERPROFILE\.claude.json")) {
    if (Test-Path $f) { Copy-Item $f "$bk\$(Split-Path $f -Leaf).$fecha.bak"; Write-Host "Backup: $bk\$(Split-Path $f -Leaf).$fecha.bak" }
    else { Write-Host "No existe $f (se omite el backup)" }
}

# --- hooks antes (para comparar al final)
$settings = "$env:USERPROFILE\.claude\settings.json"
function Hooks-Hash { if (Test-Path $settings) { $j = Get-Content $settings -Raw | ConvertFrom-Json; if ($j.hooks) { return ($j.hooks | ConvertTo-Json -Depth 20 -Compress) } } return "" }
$hooksAntes = Hooks-Hash
function Chequear-Hooks($paso) {
    if ((Hooks-Hash) -ne $hooksAntes) { throw "El paso '$paso' agrego hooks a settings.json. Frene aca: no se instalo nada mas. Backup en $bk." }
}

# --- instalacion (los 6 items de la lista, en orden)
Paso "1. Playwright MCP" { & $claude mcp add playwright --scope user -- npx "@playwright/mcp@latest" }
Chequear-Hooks "Playwright MCP"
Paso "2. Skill emil-design-eng" { npx --yes skills add emilkowalski/skill --skill emil-design-eng -g -a claude-code -y }
Chequear-Hooks "emil-design-eng"
Paso "3. Skill break-ui" { npx --yes skills add emilkowalski/skill --skill break-ui -g -a claude-code -y }
Chequear-Hooks "break-ui"
Paso "4. Impeccable (sin hooks)" { npx --yes impeccable install --user --providers=claude --no-hooks -y }
Chequear-Hooks "Impeccable"

$tienePlugin = (& $claude plugin --help 2>&1 | Out-String) -match "marketplace|install"
if ($tienePlugin) {
    Paso "5a. Marketplace de Ponytail" { & $claude plugin marketplace add DietrichGebert/ponytail }
    Paso "5b. Plugin ponytail" { & $claude plugin install ponytail@ponytail --scope user }
    Paso "6. Plugin frontend-design" { & $claude plugin install frontend-design@anthropic-plugin-directory --scope user }
    Chequear-Hooks "plugins"
} else {
    Write-Host ""
    Write-Host "Tu version no tiene 'claude plugin'. Dentro de Claude Code corre vos:" -ForegroundColor Yellow
    Write-Host "  /plugin marketplace add DietrichGebert/ponytail"
    Write-Host "  /plugin install ponytail@ponytail"
    Write-Host "  /plugin install frontend-design@anthropic-plugin-directory"
}

# --- verificacion
Write-Host ""; Write-Host "== Verificacion" -ForegroundColor Green
Write-Host "-- claude mcp list (tiene que figurar playwright)"; & $claude mcp list
if ($tienePlugin) { Write-Host "-- claude plugin list (ponytail y frontend-design)"; & $claude plugin list }
Write-Host "-- ~/.claude/skills (emil-design-eng, break-ui, impeccable)"; Get-ChildItem "$env:USERPROFILE\.claude\skills" | Select-Object -ExpandProperty Name
Write-Host "-- hooks en settings.json"
if ((Hooks-Hash) -eq $hooksAntes) { Write-Host "Sin hooks nuevos." -ForegroundColor Green } else { Write-Host "HAY HOOKS NUEVOS. Revisar." -ForegroundColor Red }

Write-Host ""
Write-Host "Listo. Cerra TODAS las ventanas de VS Code y volve a abrirlo para que se carguen las herramientas." -ForegroundColor Green

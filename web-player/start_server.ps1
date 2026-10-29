param(
    [int]$Port = 54321,
    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$WebRoot = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$Url = "http://127.0.0.1:$Port/"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw '没有找到 Python。请安装 Python 3，然后重新运行此脚本。'
}

if (-not (Test-Path (Join-Path $WebRoot 'rom\alpha8v2_npc.gba'))) {
    throw '找不到 web-player\rom\alpha8v2_npc.gba，请先运行工作区中的准备脚本或复制输出 ROM。'
}

Write-Host "网页播放器地址：$Url" -ForegroundColor Cyan
Write-Host '按 Ctrl+C 停止本地服务。' -ForegroundColor DarkGray
if ($OpenBrowser) {
    Start-Process $Url
}

python -m http.server $Port --bind 127.0.0.1 --directory $WebRoot

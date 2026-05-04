#
# Redis 二进制文件自动下载脚本 (Windows PowerShell)
# 用法: .\download-redis.ps1
#

param(
    [switch]$Force  # 强制重新下载
)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Redis 自动下载脚本 (Windows)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$RedisWindowsDir = Join-Path $ProjectRoot "tools\redis-windows"
$RedisExe = Join-Path $RedisWindowsDir "redis-server.exe"

Write-Host "[信息] 目标目录: $RedisWindowsDir" -ForegroundColor Yellow

# 检查是否已存在
if ((Test-Path $RedisExe) -and (-not $Force)) {
    Write-Host "[提示] redis-server.exe 已存在，跳过下载。" -ForegroundColor Green
    Write-Host "如需重新下载，请使用 -Force 参数或手动删除现有文件。" -ForegroundColor Yellow
    exit 0
}

# 创建目标目录
if (-not (Test-Path $RedisWindowsDir)) {
    New-Item -ItemType Directory -Path $RedisWindowsDir -Force | Out-Null
}

# 方案 1: 检查 MemuraiValkey 是否已安装
Write-Host ""
Write-Host "[步骤 1/3] 检查 MemuraiValkey 安装..." -ForegroundColor Cyan

$MemuraiPaths = @(
    "C:\Program Files\Memurai\memurai.exe",
    "C:\Program Files (x86)\Memurai\memurai.exe",
    "${env:LOCALAPPDATA}\Programs\Memurai\memurai.exe"
)

foreach ($path in $MemuraiPaths) {
    if (Test-Path $path) {
        Write-Host "  ✓ 找到 MemuraiValkey: $path" -ForegroundColor Green
        
        $response = Read-Host "  是否复制此文件? [Y/n]"
        if ($response -eq "" -or $response -match "^[Yy]") {
            Copy-Item $path $RedisExe -Force
            Write-Host "  ✓ 已复制到: $RedisExe" -ForegroundColor Green
            
            # 验证
            Write-Host ""
            Write-Host "[验证]" -ForegroundColor Cyan
            & $RedisExe --version
            Write-Host ""
            Write-Host "✅ 完成！Redis (MemuraiValkey) 已准备就绪。" -ForegroundColor Green
            exit 0
        }
    }
}

# 方案 2: 检查 Redis for Windows (tporadowski)
Write-Host ""
Write-Host "[步骤 2/3] 检查 Redis for Windows..." -ForegroundColor Cyan

$RedisPaths = @(
    "C:\Program Files\Redis\redis-server.exe",
    "C:\Redis\redis-server.exe",
    "${env:LOCALAPPDATA}\Programs\Redis\redis-server.exe"
)

foreach ($path in $RedisPaths) {
    if (Test-Path $path) {
        Write-Host "  ✓ 找到 Redis for Windows: $path" -ForegroundColor Green
        
        $response = Read-Host "  是否复制此文件? [Y/n]"
        if ($response -eq "" -or $response -match "^[Yy]") {
            Copy-Item $path $RedisExe -Force
            Write-Host "  ✓ 已复制到: $RedisExe" -ForegroundColor Green
            
            # 验证
            Write-Host ""
            Write-Host "[验证]" -ForegroundColor Cyan
            & $RedisExe --version
            Write-Host ""
            Write-Host "✅ 完成！Redis 已准备就绪。" -ForegroundColor Green
            exit 0
        }
    }
}

# 方案 3: 提供下载链接指南
Write-Host ""
Write-Host "[步骤 3/3] 需要手动下载..." -ForegroundColor Yellow
Write-Host ""
Write-Host "未在系统中找到 Redis。请按以下步骤操作：" -ForegroundColor Red
Write-Host ""
Write-Host "方案 A - MemuraiValkey (推荐):" -ForegroundColor Cyan
Write-Host "  1. 访问: https://www.memurai.com/get-memurai-valkey" -ForegroundColor White
Write-Host "  2. 下载并安装 Developer Edition (免费)" -ForegroundColor White
Write-Host "  3. 运行此脚本再次检测" -ForegroundColor White
Write-Host ""
Write-Host "方案 B - Redis for Windows:" -ForegroundColor Cyan
Write-Host "  1. 访问: https://github.com/tporadowski/redis/releases" -ForegroundColor White
Write-Host "  2. 下载 Redis-x64-*.zip (最新版)" -ForegroundColor White
Write-Host "  3. 解压后复制 redis-server.exe 到以下目录:" -ForegroundColor White
Write-Host "     $RedisWindowsDir" -ForegroundColor Yellow
Write-Host ""

# 打开浏览器
$response = Read-Host "是否打开 MemuraiValkey 下载页面? [Y/n]"
if ($response -eq "" -or $response -match "^[Yy]") {
    Start-Process "https://www.memurai.com/get-memurai-valkey"
}

exit 1

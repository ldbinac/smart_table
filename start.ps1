# SmartTable Docker 快速启动脚本（Windows PowerShell）

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "SmartTable Docker 快速部署" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否安装
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker 已安装：$dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查 Docker Compose 是否安装
try {
    $composeVersion = docker compose version
    Write-Host "✅ Docker Compose 已安装：$composeVersion" -ForegroundColor Green
    $composeCmd = "docker compose"
} catch {
    try {
        $composeVersion = docker-compose --version
        Write-Host "✅ docker-compose 已安装：$composeVersion" -ForegroundColor Green
        $composeCmd = "docker-compose"
    } catch {
        Write-Host "❌ Docker Compose 未安装" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# 检查 .env 文件
if (-not (Test-Path .env)) {
    Write-Host "📝 创建环境变量文件..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env 文件已创建，请编辑此文件修改密钥配置" -ForegroundColor Green
    Write-Host ""
}

# 选择部署模式
Write-Host "请选择部署模式:" -ForegroundColor Cyan
Write-Host "1) 简单部署（SQLite，适合测试）"
Write-Host "2) 完整部署（PostgreSQL + Redis + MinIO，适合生产）"
$choice = Read-Host "请输入选项 (1/2)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 开始简单部署..." -ForegroundColor Cyan
        & $composeCmd -f docker-compose.yml up -d --build
        
        Write-Host ""
        Write-Host "✅ 部署完成！" -ForegroundColor Green
        Write-Host ""
        Write-Host "访问地址：http://localhost" -ForegroundColor Cyan
        Write-Host "查看日志：$composeCmd logs -f" -ForegroundColor Gray
    }
    "2" {
        Write-Host ""
        Write-Host "🚀 开始完整部署..." -ForegroundColor Cyan
        if (-not (Test-Path .env)) {
            Copy-Item .env.full.example .env
        }
        & $composeCmd -f docker-compose.full.yml up -d --build
        
        Write-Host ""
        Write-Host "✅ 部署完成！" -ForegroundColor Green
        Write-Host ""
        Write-Host "访问地址：http://localhost" -ForegroundColor Cyan
        Write-Host "PostgreSQL: localhost:5432" -ForegroundColor Gray
        Write-Host "Redis: localhost:6379" -ForegroundColor Gray
        Write-Host "MinIO: localhost:9000" -ForegroundColor Gray
        Write-Host "MinIO 控制台：localhost:9001" -ForegroundColor Gray
        Write-Host "查看日志：$composeCmd logs -f" -ForegroundColor Gray
    }
    default {
        Write-Host "❌ 无效选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "常用的命令:" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "查看状态：$composeCmd ps" -ForegroundColor Gray
Write-Host "查看日志：$composeCmd logs -f" -ForegroundColor Gray
Write-Host "停止服务：$composeCmd down" -ForegroundColor Gray
Write-Host "重启服务：$composeCmd restart" -ForegroundColor Gray
Write-Host "======================================" -ForegroundColor Cyan

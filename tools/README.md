# Redis 二进制文件获取指南

## 概述

SmartTable 打包版本需要内嵌 Redis 服务以支持缓存和实时协作功能。本目录包含两个平台的 Redis 可执行文件：

- `redis-windows/` - Windows x64 版本
- `redis-linux/` - Linux x64 版本

## Windows 版本获取

### 方案 A: MemuraiValkey（推荐，原生支持）

**下载地址**: https://www.memurai.com/get-memurai-valkey

1. 访问上述网址
2. 下载 **MemuraiValkey Developer Edition**（免费）
3. 安装后，从安装目录（通常为 `C:\Program Files\Memurai\`）复制 `memurai.exe`
4. 重命名为 `redis-server.exe` 并放入 `tools/redis-windows/` 目录

### 方案 B: Redis for Windows（开源替代）

**GitHub**: https://github.com/tporadowski/redis/releases

1. 访问 GitHub Releases 页面
2. 下载最新版本的 **Redis-x64-*.msi** 或 **Redis-x64-*.zip**
3. 如果是 MSI 安装包，安装后从安装目录复制 `redis-server.exe`
4. 如果是 ZIP 包，解压后复制 `redis-server.exe` 到 `tools/redis-windows/`

### 验证

```powershell
cd tools\redis-windows
.\redis-server.exe --version
# 预期输出: Redis server v=7.x.x sha=... malloc=jemalloc-5.2.1 bits=64
```

---

## Linux 版本获取

### 方法 1: 从源码编译（推荐，通用性强）

```bash
# 下载 Redis 7.x 源码
cd /tmp
wget https://github.com/redis/redis/archive/refs/tags/7.2.4.tar.gz
tar xzf 7.2.4.tar.gz
cd redis-7.2.4

# 编译（需要 gcc 和 make）
make
make install PREFIX=/tmp/redis-build

# 复制到项目目录
cp /tmp/redis-build/bin/redis-server <project-root>/tools/redis-linux/

# 验证
<project-root>/tools/redis-linux/redis-server --version
```

### 方法 2: 使用系统包管理器后复制

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install -y redis-server
which redis-server  # 通常在 /usr/bin/redis-server
cp /usr/bin/redis-server <project-root>/tools/redis-linux/
```

**CentOS/RHEL/Fedora**:
```bash
sudo yum install -y redis
which redis-server  # 通常在 /usr/bin/redis-server
cp /usr/bin/redis-server <project-root>/tools/redis-linux/
```

### 验证

```bash
cd tools/linux
chmod +x redis-server
./redis-server --version
# 预期输出: Redis server v=7.2.4 sha=... malloc=jemalloc-5.2.1 bits=64
```

---

## 自动下载脚本（可选）

如果希望自动化此过程，可运行：

```bash
# Windows (PowerShell)
.\tools\download-redis.ps1

# Linux (Bash)
chmod +x tools/download-redis.sh
./tools/download-redis.sh
```

> 注意：自动脚本可能因网络原因失败，建议手动下载以确保可靠性。

---

## 文件大小参考

| 平台 | 文件名 | 预期大小 |
|------|--------|----------|
| Windows | redis-server.exe | 2-5 MB |
| Linux | redis-server | 2-5 MB |

---

## 常见问题

### Q: 为什么不直接把 Redis 打包进 PyInstaller？

**A**: Redis 是用 C 语言编写的独立服务程序，无法通过 Python 的打包工具集成。将其作为独立文件分发是最可靠的方式。

### Q: 可以使用其他端口吗？

**A**: 可以。修改 `config/.env` 中的 `REDIS_PORT` 即可。

### Q: Redis 必须运行吗？

**A**: 不是必须的。如果 Redis 启动失败，应用会以降级模式运行（使用内存缓存），核心功能不受影响，但实时协作功能不可用。

---

## 许可证信息

- **MemuraiValkey**: 基于 SSPL-1.0 许可证（免费用于开发和内部部署）
- **Redis**: BSD 3-Clause 许可证
- **Redis for Windows (tporadowski)**: MIT 许可证

请确保遵守相应的开源许可证要求。

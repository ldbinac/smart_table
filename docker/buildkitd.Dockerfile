# 自定义 buildkit 镜像: 内置 buildkitd.toml, 为 Windows Docker Desktop 下
# 的 buildx 多平台构建配置 Docker Hub 国内镜像加速器,
# 绕开 buildx 容器直连 auth.docker.io 不稳定的问题。
FROM moby/buildkit:buildx-stable-1

COPY buildkitd.toml /etc/buildkit/buildkitd.toml

# 泛微 E10 OAuth2 单点登录集成说明

本文说明如何在**尽量不修改上游源码**的前提下，把 SmartTable 接入泛微 E10 的统一认证（OAuth2 授权码模式），并保证后续可以跟随上游仓库升级。

- 集成分支：`feat/e10-sso`
- 后端扩展目录：`smarttable-backend/app/integrations/e10/`
- 前端扩展目录：`smart-table/src/extensions/e10/`
- 配置示例：`env.example`

---

## 1. 设计原则：为什么可以“无损更新”

所有业务逻辑都放在**新增目录**中，上游文件只保留极小的、可快速重新应用的钩子：

| 文件 | 改动 | 作用 |
| --- | --- | --- |
| `smarttable-backend/app/__init__.py` | 2 行 | 导入并调用 `register_e10_integration(app)` |
| `smart-table/src/router/index.ts` | 1 个路由 | 注册 `/#/e10-callback` |
| `smart-table/src/views/auth/Login.vue` | 少量模板/挂载代码 | 显示 E10 登录按钮、按配置隐藏密码登录 |
| `smart-table/src/components/common/AppHeader.vue` | 少量登出代码 | 退出时可选注销 E10 会话 |
| `smart-table/src/i18n/locales/{zh-CN,en-US}/auth.json` | 新增 key | E10 相关文案 |
| `smart-table/src/i18n/locales/{zh-CN,en-US}/route.json` | 新增 key | 回调页标题 |

新增文件（升级时不会被上游覆盖）：

```
smarttable-backend/app/integrations/__init__.py
smarttable-backend/app/integrations/e10/__init__.py
smarttable-backend/app/integrations/e10/config.py
smarttable-backend/app/integrations/e10/client.py
smarttable-backend/app/integrations/e10/models.py
smarttable-backend/app/integrations/e10/service.py
smarttable-backend/app/integrations/e10/routes.py
smarttable-backend/app/integrations/e10/i18n.py
smarttable-backend/tests/test_e10_sso.py

smart-table/src/extensions/e10/api.ts
smart-table/src/extensions/e10/E10LoginButton.vue
smart-table/src/extensions/e10/E10Callback.vue

README.md
env.example
schema.sql.example
```

> E10 集成只新增 `e10_sso_identities` 一张表，不修改 `users` 表；关闭开关后即可完全停用。

---

## 2. 认证流程

SmartTable 的前端使用 hash 路由（`/#/...`），而 E10 明确要求 `redirect_uri` **不能包含 `#` 路由**。因此采用“后端回调 + 一次性票据”的方式：

```
浏览器                SmartTable 后端                     E10
  |  GET /api/integrations/e10/login?redirect=/base/1
  | ----------------------> |
  |                         | 生成签名 state，写入 HttpOnly Cookie
  |  302 到 E10 /authorize  |
  | <---------------------- |
  |  GET E10 authorize?client_id=...&redirect_uri=...&response_type=code
  | -----------------------------------------------------------> |
  |                         |        用户在 E10 登录/授权
  |  302 回调 /api/integrations/e10/callback?code=...&state=...
  | <----------------------------------------------------------- |
  |  GET callback           |
  | ----------------------> | 校验 state Cookie
  |                         | POST /accessToken 用 code 换 access_token
  |                         | POST /profile 用 access_token 取用户 id
  |                         | 按 id 查找/创建 SmartTable 用户
  |                         | 生成短时一次性 ticket
  |  302 到 /#/e10-callback?ticket=...
  | <---------------------- |
  |  POST /api/integrations/e10/exchange {ticket}
  | ----------------------> | 消费 ticket，返回 SmartTable JWT
  | <---------------------- |
```

关键点：

1. **JWT 不放在地址栏**：回调地址只带一次性 `ticket`，前端再通过 POST 换取 JWT。
2. **state 双检**：既放在授权 URL 中，也写入 HttpOnly + SameSite=Lax Cookie；即使 E10 不回传 state，Cookie 仍可完成校验。
3. **ticket 一次性且绑定浏览器**：默认 120 秒有效，消费后立即删除；同时通过 HttpOnly Cookie 绑定到发起回调的浏览器，防止登录 CSRF；
4. **不信任前端传入的用户信息**：用户身份完全来自 E10 `/profile`，前端只提交 ticket。
5. **Redis 可选**：ticket/state 的共享存储优先使用 Redis；Redis 不可用时退化为单进程内存（多进程部署请确保 Redis 可用）。

---

## 3. E10 侧配置

以下步骤对应 E10 文档《业务系统通过 OAuth2 接入 E10》。

### 3.1 注册 OAuth2 认证应用

进入 E10：

`统一认证中心 -> 认证应用管理 -> 注册应用系统`

填写：

| 项目 | 建议值 |
| --- | --- |
| 应用名称 | SmartTable |
| 业务系统 URL / 回调地址 | `https://smarttable.example.com/api/integrations/e10/callback` |
| 账号映射规则 | 推荐 **电子邮箱**；也可用登录名/工号/手机号，见第 4 节 |
| 适用对象 | 需要使用 SmartTable 的人员范围 |

注意：

- 回调地址**不能带 `#`**，必须是后端地址；
- 协议必须与 SmartTable 一致（E10 是 HTTPS，SmartTable 也必须是 HTTPS）；
- 不要把回调地址写成前端页面地址（如 `/#/e10-callback`）。

### 3.2 开启 OAuth2 认证

进入：

`统一认证中心 -> 认证协议管理 -> OAuth2 认证`

开启后确认以下接口地址（不同 E10 版本可能不同，可在集成配置中覆盖）：

```
授权地址：  https://oa.example.com/papi/sso/oauth2.0/authorize
Token 地址：https://oa.example.com/papi/sso/oauth2.0/accessToken
用户信息：  https://oa.example.com/papi/sso/oauth2.0/profile
退出地址：  https://oa.example.com/sp/integration/oauth2.0/logout
```

### 3.3 把回调域名加入白名单

按 E10 文档要求，将 SmartTable 的域名加入 E10 白名单，否则 E10 可能拒绝回调或退出跳转。

### 3.4 取得凭据

注册完成后取得：

- `client_id`
- `client_secret`

填入 SmartTable 的 `E10_CLIENT_ID` / `E10_CLIENT_SECRET`。

---

## 4. 账号映射说明（最重要）

E10 `/profile` 接口文档说明 `attributes` 暂不返回，但部分 E10 版本/环境会返回自定义属性。本集成已兼容以下形态：

- 字典：`{"username": "张三", "job_num": "A1001"}`
- 列表：`[{"name": "username", "value": "张三"}, ...]`
- 自定义属性平铺在 `/profile` 顶层
- `attributes` 为 JSON 字符串

这个 `id` 的含义由 E10 应用的**账号映射规则**决定：

| E10 账号映射规则 | `/profile` 的 `id` 示例 | SmartTable 配置 |
| --- | --- | --- |
| 电子邮箱（推荐） | `zhangsan@corp.example.com` | 不需要额外配置 |
| 登录名 | `zhangsan` | `E10_EMAIL_DOMAIN=corp.example.com` |
| 工号 | `A10086` | `E10_EMAIL_DOMAIN=corp.example.com` 或 `E10_EMAIL_TEMPLATE={id}@corp.example.com` |
| 手机号 | `13800138000` | 建议用模板：`E10_EMAIL_TEMPLATE={id}@mobile.corp.example.com` |

匹配顺序：

1. 已存在的 `e10_sso_identities` 绑定记录；
2. 邮箱相同的既有 SmartTable 用户（`E10_MATCH_BY_EMAIL=true`，默认开启）；
3. 自动创建新用户（`E10_AUTO_CREATE_USERS=true`，默认开启）。

### 4.1 本环境（app.weaver.com.cn:20600）的映射

E10 账号映射规则为**人员id**，`/profile` 的自定义属性为：

| 属性 | 含义 |
| --- | --- |
| `username` | 姓名 |
| `job_num` | 工号 |
| `mobile` | 手机号 |
| `email` | 邮箱（可选；E10 返回时优先使用真实邮箱） |

推荐配置（见 `env.weaver.example`）：

```env
E10_BASE_URL=http://app.weaver.com.cn:20600
E10_ID_FIELD=id
E10_EMAIL_TEMPLATE={job_num}@e10.local
E10_EMAIL_FALLBACK_TEMPLATE={id}@e10.local
```

- `id`（人员id）用于 `e10_sso_identities.e10_user_id`，是稳定绑定键；
- `username` 作为 SmartTable 显示名；
- 如果 E10 返回自定义属性 `email`，优先使用真实邮箱；否则用 `job_num` 派生 `users.email`，工号缺失时回退到人员 id；
- `e10.local` 是内部标识域名，不会真的发信。如果需要站内信/邮件通知发到真实邮箱，优先让 E10 返回 `email` 属性，或者把模板改成公司的真实邮箱规则；
- `E10_ADMIN_IDS` 可以填人员id，也可以填工号。

自动创建规则：

- `email_verified=true`（身份由 E10 保证）；
- 本地密码写入随机不可猜测值，E10 用户无法用密码登录；
- 默认角色 `E10_DEFAULT_ROLE=editor`；
- `owner/admin/workspace_admin` 不能通过默认角色获得，管理员只能通过 `E10_ADMIN_IDS` 显式指定；
- `E10_ADMIN_IDS` 中的 id 在每次登录时会被提升为 `admin`（从白名单移除后不会自动降级，需管理员手工调整）。

如果需要“先由管理员建好用户，再允许 E10 登录”，设置：

```env
E10_AUTO_CREATE_USERS=false
```

此时 E10 用户必须能通过邮箱匹配到已有 SmartTable 用户，否则会返回“尚未开通访问权限”。

---

## 5. SmartTable 侧配置

把 `env.example` 复制到 `config/.env`（或 Docker 环境变量），至少配置：

```env
E10_SSO_ENABLED=true
E10_BASE_URL=https://oa.example.com
E10_CLIENT_ID=...
E10_CLIENT_SECRET=...
E10_REDIRECT_URI=https://smarttable.example.com/api/integrations/e10/callback
E10_FRONTEND_BASE_URL=https://smarttable.example.com
E10_EMAIL_DOMAIN=corp.example.com
```

### 5.1 必填项

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `E10_SSO_ENABLED` | 是 | `true` 才显示登录按钮、注册路由 |
| `E10_BASE_URL` | 是 | E10 根地址，不带尾部 `/` |
| `E10_CLIENT_ID` | 是 | E10 应用标识 |
| `E10_CLIENT_SECRET` | 是 | E10 应用密钥 |
| `E10_REDIRECT_URI` | 强烈建议 | 必须与 E10 登记的业务系统 URL 完全一致 |
| `E10_FRONTEND_BASE_URL` | 建议 | 登录完成后的前端 origin |
| `E10_EMAIL_DOMAIN` / `E10_EMAIL_TEMPLATE` / `E10_EMAIL_FALLBACK_TEMPLATE` | 视映射规则 | `id` 不是邮箱时必填；模板支持 `{id}`、`{job_num}`、`{username}`、`{mobile}`、`{domain}` |

### 5.2 常用可选项

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `E10_PASSWORD_LOGIN_ENABLED` | `true` | 设为 `false` 则登录页只显示 E10 登录 |
| `E10_ENFORCE_SSO` | `false` | 设为 `true` 则在服务端禁用本地 `/api/auth/login` 与 `/api/auth/register` |
| `E10_AUTO_CREATE_USERS` | `true` | 首次登录自动建用户 |
| `E10_DEFAULT_ROLE` | `editor` | 自动建用户的角色 |
| `E10_ADMIN_IDS` | 空 | E10 id 白名单，映射为 SmartTable admin |
| `E10_MATCH_BY_EMAIL` | `true` | 按邮箱匹配既有用户 |
| `E10_SYNC_PROFILE` | `true` | 同步姓名/头像 |
| `E10_LOGOUT_WITH_E10` | `true` | SmartTable 退出时注销 E10 会话 |
| `E10_TOKEN_PARAM_STYLE` | `auto` | `query` / `form` / `auto` |
| `E10_SEND_STATE` | `true` | 是否在授权 URL 中携带 `state`；E10 严格校验参数时可设 `false`（Cookie 仍会校验） |
| `E10_VERIFY_SSL` | `true` | 内网自签证书可设 `false` 或配 `E10_CA_BUNDLE` |
| `E10_STATE_TTL` | `600` | OAuth state 有效期（秒） |
| `E10_TICKET_TTL` | `120` | 一次性票据有效期（秒） |
| `E10_COOKIE_SAMESITE` | `Lax` | `Lax` / `Strict` / `None`；仅 iframe 嵌入 E10 门户时考虑 `None`（必须 HTTPS）。注意上游默认 `X-Frame-Options: DENY`，iframe 嵌入还需调整安全头策略 |
| `E10_AUTO_CREATE_SCHEMA` | `true` | 自动创建身份映射表 |

> 修改环境变量后需要重启后端（配置在启动时读取）。

### 5.3 只允许 E10 登录

确认已经存在可用管理员账号后，再设置：

```env
E10_PASSWORD_LOGIN_ENABLED=false
# 如需在服务端彻底禁用本地登录/注册 API（确认 E10 登录可用后再开启）
E10_ENFORCE_SSO=true
```

并建议在 SmartTable 的「系统配置」中关闭自助注册，避免绕过 E10 创建本地账号。

> 关闭密码登录前，请确认至少存在一个可用的 SmartTable `admin` 账号（例如先执行
> `python run.py create-admin <email> <password> <name>`），否则将无法进入系统管理页面。

---

## 6. 启动与验证

### 6.1 源码开发

后端：

```bash
cd smarttable-backend
python run.py
```

前端：

```bash
cd smart-table
pnpm install
pnpm dev
```

开发环境示例：

```env
E10_REDIRECT_URI=http://localhost:5000/api/integrations/e10/callback
E10_FRONTEND_BASE_URL=http://localhost:3000
```

同时把 `http://localhost:5000/api/integrations/e10/callback` 登记到 E10 应用（或使用内网穿透地址），并确保 E10 能访问该地址。

### 6.2 Docker

> **重要**：`.dockerignore` 已经排除了 `config/` 和 `**/.env`，宿主机的 `config/.env` **不会自动进入镜像或容器**；`docker-compose.full.yml` 默认也没有传 `E10_*` 环境变量。因此容器内 `E10_SSO_ENABLED` 是默认值 `false`，登录页不会显示泛微 E10 按钮。

#### 方式 2：在 docker-compose.full.yml 的 environment 中显式配置（Docker 部署推荐）

编辑 `docker-compose.full.yml`，在 `smarttable` 服务的 `environment` 下加入：

```yaml
services:
  smarttable:
    environment:
      E10_SSO_ENABLED: "true"
      E10_BASE_URL: "http://app.weaver.com.cn:20600"
      E10_CLIENT_ID: "<E10应用标识>"
      E10_CLIENT_SECRET: "<E10应用密钥>"
      E10_REDIRECT_URI: "http://192.168.1.100:5000/api/integrations/e10/callback"
      E10_FRONTEND_BASE_URL: "http://192.168.1.100:5000"
      E10_ID_FIELD: "id"
      E10_EMAIL_TEMPLATE: "{job_num}@e10.local"
      E10_EMAIL_FALLBACK_TEMPLATE: "{id}@e10.local"
      # 若 E10 返回自定义属性 email，会优先使用真实邮箱；以上两条仅作兜底
      E10_AUTO_CREATE_USERS: "true"
      E10_DEFAULT_ROLE: "editor"
      E10_PASSWORD_LOGIN_ENABLED: "true"
      E10_ENFORCE_SSO: "false"
      E10_LOGOUT_WITH_E10: "true"
```

说明：

- **不要把真实的 `client_secret` 提交到 Git**；上面用占位符，实际部署时在部署机的 compose 文件或 `.env` 中填写；
- `E10_REDIRECT_URI` 必须是浏览器访问的 Docker 对外地址，并且与 E10 应用登记的“业务系统 URL 地址”完全一致；
- 端口映射是 `80:80` 时用 `http://192.168.1.100/...`；是 `5000:80` 时用 `http://192.168.1.100:5000/...`；
- 回调地址不能带 `#`；
- `E10_EMAIL_TEMPLATE` 适用于“人员id + 工号”的映射；如果 E10 账号映射直接返回邮箱，可去掉模板并配置 `E10_EMAIL_DOMAIN` 或不配置；
- `E10_BASE_URL` 按实际 E10 地址填写，不要带尾部 `/`。

修改后必须重新构建镜像，`docker compose up -d` 本身不会自动重建：

```bash
docker compose -f docker-compose.full.yml build --no-cache
docker compose -f docker-compose.full.yml up -d --force-recreate
```

验证容器内配置：

```bash
docker exec smarttable env | grep E10_
docker exec smarttable curl -s http://127.0.0.1:5000/api/integrations/e10/config
```

期望返回：

```json
{"data":{"enabled":true,"ready":true,"login_url":"/api/integrations/e10/login",...}}
```

- 如果 `/api/integrations/e10/config` 返回 404：镜像不是从 `feat/e10-sso` 分支构建的，检查 `git branch --show-current` 后重新构建；
- 如果 `enabled=false`：`E10_*` 环境变量没有进入容器，检查 `docker exec smarttable env | grep E10_`；
- 如果接口正常但页面没有按钮：浏览器强制刷新 `Ctrl + F5`，避免旧 `index.html` 缓存。

#### 方式 1：挂载 config/.env（备选）

如果希望复用宿主机上的 `config/.env`，也可以在 `smarttable` 服务下增加：

```yaml
services:
  smarttable:
    env_file:
      - ./config/.env
```

`environment` 中的同名变量优先级高于 `env_file`，因此 `DATABASE_URL`、`REDIS_URL` 仍会使用 compose 中的容器地址。

如果 SmartTable 在反向代理/负载均衡后面，确保：

- `X-Forwarded-Proto: https` 被正确传递（state Cookie 的 `Secure` 自动判断依赖它）；
- 会话保持不是必须的（state/ticket 存在 Redis 中），但多进程部署必须保证 Redis 可用。

如果构建镜像时 apt 镜像返回 403（例如清华源偶发限流），可在 `.env` 中切换 Debian 镜像后重建：

```env
DEBIAN_MIRROR=https://mirrors.aliyun.com
DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com
```

```bash
docker compose -f docker-compose.full.yml build --no-cache
docker compose -f docker-compose.full.yml up -d
```

可选镜像：`https://mirrors.aliyun.com`（默认）、`https://mirrors.cloud.tencent.com`、`https://mirrors.huaweicloud.com`。如果 pip 也被限流，可同时设置 `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/`。

### 6.3 验证清单

1. 打开 `/#/login`，能看到“使用泛微 E10 登录”按钮；
2. 点击后跳转到 E10 登录页；
3. E10 登录后回到 `/#/e10-callback?ticket=...`，短暂 loading 后进入首页；
4. 浏览器地址栏不出现 SmartTable JWT；
5. 退出登录后，若 `E10_LOGOUT_WITH_E10=true`，会跳转 E10 注销并回到登录页；
6. 再次点击 E10 登录，能重新进入（E10 会话已注销时需要重新输入密码）。

---

## 7. 故障排查

| 现象 / 错误码 | 原因 | 处理 |
| --- | --- | --- |
| 登录页没有 E10 按钮 | `E10_SSO_ENABLED=false` 或必填项缺失 | 看后端启动日志中的 `[E10]` 警告；访问 `/api/integrations/e10/config` 确认 `enabled` |
| E10 提示 `80013` | 授权请求的 `redirect_uri` 与 E10 登记值不一致 | 检查 `E10_REDIRECT_URI`，协议、域名、路径、末尾 `/` 必须完全一致 |
| E10 提示 `1005` | `redirect_uri` 未注册 | 在 E10 应用管理中登记回调地址 |
| E10 提示 `80014` | 用户不在适用对象范围 | 调整 E10 应用的适用对象 |
| E10 提示 `80006/80009` | 账号映射字段未维护 | 在 E10 人员信息中补齐登录名/邮箱 |
| 回调报 `e10_state_missing` | 浏览器/代理丢弃了 state Cookie | 确认回调与登录同域、HTTPS、`X-Forwarded-Proto` 正确；不要用两个不同域名交替访问。若 SmartTable 被嵌入 E10 门户 iframe，第三方 Cookie 限制会导致 Cookie 不发送，此时可尝试 `E10_COOKIE_SAMESITE=None` + HTTPS，或改为新窗口打开 |
| 回调报 `e10_code_expired` | code 已使用或超过有效期 | 重新点击登录；不要在浏览器里刷新回调 URL |
| 回调报 `e10_redirect_not_registered` | E10 未登记回调地址 | 同 `1005` |
| 回调报 `e10_user_not_provisioned` | 自动开通关闭且邮箱未匹配到用户 | 先创建用户，或开启 `E10_AUTO_CREATE_USERS` |
| 回调报 `e10_email_not_configured` | `/profile` 的 id 不是邮箱，且模板渲染失败 | 配置 `E10_EMAIL_TEMPLATE` / `E10_EMAIL_FALLBACK_TEMPLATE`，或 `E10_EMAIL_DOMAIN` |
| 回调报 `e10_network_error` | SmartTable 无法访问 E10 | 检查网络、DNS、防火墙、`E10_VERIFY_SSL` |
| 登录后立刻回到登录页 | JWT 未保存/被清除 | 看浏览器控制台与 `/api/integrations/e10/exchange` 响应；确认前端与后端同源 |
| 多进程下偶发 `e10_ticket_used` | 未使用共享 Redis，票据落在不同进程 | 配置 `REDIS_URL`，确保所有 worker 共用 Redis |

### 7.1 调试接口

```bash
# 查看开关（不返回密钥）
curl https://smarttable.example.com/api/integrations/e10/config

# 直接触发登录（浏览器打开）
https://smarttable.example.com/api/integrations/e10/login?redirect=/base/1
```

后端日志中搜索 `[E10]`，会记录失败阶段（token/profile/user mapping）和 E10 错误码，但不会记录 `client_secret`、`code`、`access_token` 或 JWT。

---

## 8. 安全说明

- `client_secret` 只存在于后端环境变量，不下发前端；
- state 使用 `SECRET_KEY` 签名，HttpOnly + SameSite=Lax Cookie 双检；
- 一次性 ticket 使用独立 salt 签名，默认 120 秒过期且只能消费一次；
- ticket 通过 HttpOnly `e10_login_binding` Cookie 绑定到发起回调的浏览器，防止把 ticket 链接发给他人造成登录 CSRF；
- JWT 通过 POST 返回，不进入 URL、Referer 或 Nginx access log；
- 按邮箱匹配已有用户（`E10_MATCH_BY_EMAIL=true`）意味着信任 E10 返回的邮箱/账号映射；请确保 E10 中该字段可信且唯一，否则可关闭此选项，仅依赖 `e10_sso_identities` 绑定；
- 自动开通用户写入随机密码，E10 用户无法通过本地密码登录；
- 默认不允许自动获得管理角色，管理员需通过 `E10_ADMIN_IDS` 显式配置；
- 回调只接受站内相对路径作为 `redirect`，拒绝 `//evil.com`、反斜杠、CRLF 等开放重定向载荷；
- 建议全站 HTTPS，并在 E10 与 SmartTable 两侧都开启 HTTPS。

---

## 9. 与 E10 文档的对应关系

| E10 文档 | 本实现 |
| --- | --- |
| `GET /papi/sso/oauth2.0/authorize` | `E10Client.build_authorize_url()` |
| `POST /papi/sso/oauth2.0/accessToken` | `E10Client.exchange_code()` |
| `POST /papi/sso/oauth2.0/profile` | `E10Client.fetch_profile()` |
| `GET /sp/integration/oauth2.0/logout` | `E10Client.build_logout_url()` |
| `status=200 && code=0` | `E10Client._is_success()` |
| `id` 为账号映射值 | `E10UserService.resolve_email()` / `resolve_user()` |
| 错误码 1002~1022、80006~80026 | `client.py` 中的 `_REASON_BY_UPSTREAM_CODE` |

E10 文档地址：<https://weapp.eteams.cn/sp/ebdpage/view/freepass/1152863419640021002/page/1152863419640021002?id=1177708516831125564&space_id=1158011075224911873&freepass_doc=1>

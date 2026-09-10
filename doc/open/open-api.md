# 开放 API（/api/open/v1）

本文档描述第三方应用通过 OAuth2 客户端凭证获取的 Bearer 令牌，调用 SmartTable 开放 API 进行数据访问的接口清单。

> 所有接口前缀为 `/api/open/v1`，需携带 `Authorization: Bearer <access_token>`（由 `/api/oauth/token` 签发）。

---

## 1. 通用约定

### 认证

```
Authorization: Bearer <access_token>
```

服务端校验：
1. JWT 签名有效且未过期；
2. 令牌的 `token_type == app`（应用令牌，用户令牌会被拒绝）；
3. 令牌未被撤销（Redis 黑名单）；
4. 目标 Base 在应用的 `allowed_bases` 白名单内；
5. 请求所需的 scope 在应用的授予范围内。

任意一步不满足将返回对应错误。

### 限流

开放 API 使用独立限流（默认每应用 600 次/分钟，`record:write` 类写接口 300 次/分钟），与用户 API 配额隔离。超出后返回 `429`。

### 统一响应格式

成功：

```json
{
  "code": 0,
  "message": "操作成功",
  "data": { },
  "request_id": "req_xxx"
}
```

分页列表（`paginated_response`）：

```json
{
  "code": 0,
  "message": "获取成功",
  "data": [ ... ],
  "pagination": { "page": 1, "per_page": 20, "total": 135, "pages": 7 },
  "request_id": "req_xxx"
}
```

错误：

```json
{
  "code": 403,
  "message": "应用未获得访问该 Base 的授权",
  "error": "forbidden",
  "request_id": "req_xxx"
}
```

### 错误码

| HTTP | error | 含义 |
| --- | --- | --- |
| 401 | `unauthorized` | 令牌缺失 / 无效 / 应用不存在 |
| 403 | `forbidden` | 应用已停用 / 无 Base 授权 / 缺 scope |
| 404 | `not_found` | Base / 表 / 记录不存在 |
| 429 | `rate_limit` | 触发开放 API 限流 |

---

## 2. 接口清单

### 2.1 Base

| 方法 | 路径 | 所需 scope |
| --- | --- | --- |
| GET | `/bases` | `base:read` |
| GET | `/bases/{base_id}` | `base:read` |

#### 列出授权 Base

```bash
curl "https://your-domain/api/open/v1/bases" \
  -H "Authorization: Bearer <access_token>"
```

返回当前应用 `allowed_bases` 内的全部 Base 摘要（id / name / 字段等）。

#### 获取 Base 详情

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111" \
  -H "Authorization: Bearer <access_token>"
```

---

### 2.2 表（Table）

| 方法 | 路径 | 所需 scope |
| --- | --- | --- |
| GET | `/bases/{base_id}/tables` | `table:read` |
| GET | `/bases/{base_id}/tables/{table_id}` | `table:read` |

#### 列出表

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables" \
  -H "Authorization: Bearer <access_token>"
```

#### 获取表详情

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222" \
  -H "Authorization: Bearer <access_token>"
```

---

### 2.3 字段（Field）

| 方法 | 路径 | 所需 scope |
| --- | --- | --- |
| GET | `/bases/{base_id}/tables/{table_id}/fields` | `field:read` |

#### 列出字段结构

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/fields" \
  -H "Authorization: Bearer <access_token>"
```

返回该表所有字段的元数据结构（字段名、类型、配置等）。

---

### 2.4 记录（Record）

| 方法 | 路径 | 所需 scope |
| --- | --- | --- |
| GET | `/bases/{base_id}/tables/{table_id}/records` | `record:read` |
| GET | `/bases/{base_id}/tables/{table_id}/records/search?q=` | `record:read` |
| GET | `/bases/{base_id}/tables/{table_id}/records/{record_id}` | `record:read` |
| POST | `/bases/{base_id}/tables/{table_id}/records` | `record:write` |
| PUT | `/bases/{base_id}/tables/{table_id}/records/{record_id}` | `record:write` |
| DELETE | `/bases/{base_id}/tables/{table_id}/records/{record_id}` | `record:write` |

#### 列出记录（分页）

查询参数：`page`（默认 1）、`per_page`（默认 20，最大 200）。

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records?page=1&per_page=20" \
  -H "Authorization: Bearer <access_token>"
```

#### 搜索记录

查询参数：`q`（关键词，必填）。

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records/search?q=关键词" \
  -H "Authorization: Bearer <access_token>"
```

#### 获取单条记录

```bash
curl "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records/33333333-3333-3333-3333-333333333333" \
  -H "Authorization: Bearer <access_token>"
```

#### 创建记录

请求体为字段值对象（也可包裹在 `{"values": {...}}` 中）。

```bash
curl -X POST "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "名称": "示例记录",
    "状态": "进行中",
    "数量": 42
  }'
```

> 字段名需与 `/fields` 返回的字段标识一致。记录的操作人自动记为应用 ID，便于审计。

#### 更新记录

```bash
curl -X PUT "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records/33333333-3333-3333-3333-333333333333" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "状态": "已完成"
  }'
```

#### 删除记录

```bash
curl -X DELETE "https://your-domain/api/open/v1/bases/11111111-1111-1111-1111-111111111111/tables/22222222-2222-2222-2222-222222222222/records/33333333-3333-3333-3333-333333333333" \
  -H "Authorization: Bearer <access_token>"
```

---

## 3. 端到端示例

```bash
# 1. 换取令牌
TOKEN=$(curl -s -X POST "https://your-domain/api/oauth/token" \
  -u "oa_client_id:os_client_secret" \
  -d "grant_type=client_credentials" \
  -d "scope=base:read table:read record:read record:write" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. 读取授权的 Base 列表
curl "https://your-domain/api/open/v1/bases" \
  -H "Authorization: Bearer $TOKEN"

# 3. 在指定表中创建一条记录
curl -X POST "https://your-domain/api/open/v1/bases/$BASE_ID/tables/$TABLE_ID/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"任务名": "通过开放 API 创建", "优先级": 1}'
```

---

## 4. 说明与限制

- 应用以授权 Base 的「所有者视角」读写数据；跨 `allowed_bases` 的访问会被拒绝（`403`）。
- 记录写操作的操作人记为应用 ID，所有写操作均写入应用审计日志。
- 当前版本**仅**支持 Client Credentials 模式，未开放用户授权（授权码 / PKCE）相关端点。
- 字段名（key）以 `/fields` 返回的标识为准；类型校验由底层记录服务负责，非法值将返回 `400`。

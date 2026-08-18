# 第三方应用接入实践案例

本文档演示第三方应用如何通过 **OAuth2 客户端凭证（Client Credentials）** 模式接入 SmartTable 开放 API，拉取指定 Base/Table 的全部记录。提供了 **Python** 与 **Java** 两套完整的实现样例。

> 前置阅读：[OAuth2 接入文档](./oauth2-integration.md)（令牌端点、scope 与令牌管理）、[开放 API 文档](./open-api.md)（接口清单）。

---

## 1. 场景说明

第三方应用持有管理员分配的 `client_id` / `client_secret`，以**应用自身服务账号**身份调用开放 API，无需终端用户参与。

**本次演示的目标**：
- 获取访问令牌：`POST /api/oauth/token`（`grant_type=client_credentials`）
- 分页拉取记录：`GET /api/open/v1/bases/{base_id}/tables/{table_id}/records`

### 1.1 示例凭据

```
Client ID:     oa_6075240dd4d58c1cb19271eb621f08d2
Client Secret: os_TO_-UfHRPgKIltQapi9U2wYG8iGakGAUY2uzxwGfNM0
```

> ⚠️ **安全提醒**：以上仅为演示凭据。请勿在代码/文档中硬编码真实密钥，生产环境应通过环境变量或密钥管理服务注入。

### 1.2 演示资源

```
Base ID:  5e6ab2ad-d45b-4535-a4c9-fe7af69cbe8b
Table ID: d57618ce-6942-4d9a-b7f2-3144e35f704f
```

### 1.3 调用流程

```
① POST /api/oauth/token
   请求：Basic Auth (client_id:client_secret) + grant_type=client_credentials
   响应：{ "access_token": "...", "token_type": "Bearer", "expires_in": 7200, ... }

② GET /api/open/v1/bases/{base_id}/tables/{table_id}/records?page=1&per_page=200
   请求头：Authorization: Bearer <access_token>
   响应：{ "success": true, "data": [ ...记录... ], "meta": { "pagination": { ... } } }
```

分页参数说明：

| 参数 | 说明 |
|------|------|
| `page` | 页码，从 1 开始 |
| `per_page` | 每页条数，默认 20，**上限 200** |
| `meta.pagination` | 含 `total`（总条数）与 `total_pages`（总页数），用于判断翻页结束 |

---

## 2. Python 实现

**源文件**：`tools/fetch_open_table_data.py`（仅依赖 Python 标准库，无需安装第三方包）

### 2.1 运行方式

```bash
# 方式一：直接传参
python fetch_open_table_data.py \
  --base-id 5e6ab2ad-d45b-4535-a4c9-fe7af69cbe8b \
  --table-id d57618ce-6942-4d9a-b7f2-3144e35f704f \
  --client-id oa_6075240dd4d58c1cb19271eb621f08d2 \
  --client-secret "os_TO_-UfHRPgKIltQapi9U2wYG8iGakGAUY2uzxwGfNM0"

# 方式二：凭据走环境变量（推荐，避免泄露进命令历史）
export OAUTH_CLIENT_ID="oa_6075240dd4d58c1cb19271eb621f08d2"
export OAUTH_CLIENT_SECRET="os_TO_-UfHRPgKIltQapi9U2wYG8iGakGAUY2uzxwGfNM0"
python fetch_open_table_data.py --base-id 5e6ab2ad-... --table-id d57618ce-...
```

### 2.2 参数说明

| 参数 / 环境变量 | 说明 | 默认值 |
|----------------|------|--------|
| `--base-url` / `SMART_TABLE_BASE_URL` | 服务地址 | `http://localhost:5000` |
| `--client-id` / `OAUTH_CLIENT_ID` | 应用 ID | 必填 |
| `--client-secret` / `OAUTH_CLIENT_SECRET` | 应用密钥 | 必填 |
| `--page-size` | 每页条数 | 200（上限 200） |
| `--out` | 导出 JSON 文件路径 | 不导出 |
| `--verbose` | 打印每页请求详情 | 关闭 |

### 2.3 完整源码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟第三方应用调用开放 API（OAuth2 Client Credentials）拉取指定 Base/Table 的全部记录。

用法:
    python fetch_open_table_data.py --base-id 5e6ab2ad-... --table-id d57618ce-...

可选参数（也可通过环境变量提供）:
    --base-url     服务地址，默认 http://localhost:5000
    --client-id    OAuth client_id（默认读环境变量 OAUTH_CLIENT_ID）
    --client-secret OAuth client_secret（默认读环境变量 OAUTH_CLIENT_SECRET）
    --page-size    每页大小，默认 200（服务端上限 200）
    --out          导出 JSON 文件路径（可选）
    --verbose      打印详细请求日志

环境变量:
    OAUTH_CLIENT_ID
    OAUTH_CLIENT_SECRET
    SMART_TABLE_BASE_URL
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import base64


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def request_json(url: str, method: str = "GET", headers: dict | None = None,
                 body: dict | None = None) -> dict:
    """发送 HTTP 请求并解析 JSON 响应"""
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {url}\n{detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 {url}: {e.reason}") from e


def get_access_token(base_url: str, client_id: str, client_secret: str) -> str:
    """使用 Client Credentials 模式换取访问令牌"""
    # 使用 Basic Auth 携带客户端凭据（RFC 6749 推荐方式）
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_url = f"{base_url}/api/oauth/token"
    payload = "grant_type=client_credentials"
    req = urllib.request.Request(token_url, data=payload.encode(), method="POST")
    req.add_header("Authorization", f"Basic {basic}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"换取令牌失败 HTTP {e.code}:\n{detail}") from e
    if "access_token" not in data:
        raise RuntimeError(f"换取令牌失败，响应缺少 access_token: {data}")
    return data["access_token"]


def fetch_all_records(base_url: str, token: str, base_id: str, table_id: str,
                      page_size: int = 200, verbose: bool = False) -> list:
    """分页拉取指定表的所有记录"""
    records: list = []
    page = 1
    while True:
        url = (
            f"{base_url}/api/open/v1/bases/{base_id}/tables/{table_id}/records"
            f"?page={page}&per_page={page_size}"
        )
        if verbose:
            print(f"[GET] {url}")
        resp = request_json(url, headers={"Authorization": f"Bearer {token}"})
        if not isinstance(resp.get("data"), list):
            raise RuntimeError(f"响应格式异常: {resp}")
        records.extend(resp["data"])
        pagination = resp.get("meta", {}).get("pagination", {})
        total = pagination.get("total", 0)
        total_pages = pagination.get("total_pages", 0)
        if verbose:
            print(f"  第 {page} 页: 累计 {len(records)}/{total} 条")
        if page >= total_pages:
            break
        page += 1
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="拉取 SmartTable 开放 API 的表格全部记录")
    parser.add_argument("--base-id", required=True, help="Base ID")
    parser.add_argument("--table-id", required=True, help="Table ID")
    parser.add_argument("--base-url", default=get_env("SMART_TABLE_BASE_URL", "http://localhost:5000"),
                        help="服务地址（默认 http://localhost:5000）")
    parser.add_argument("--client-id", default=get_env("OAUTH_CLIENT_ID"), help="OAuth client_id")
    parser.add_argument("--client-secret", default=get_env("OAUTH_CLIENT_SECRET"), help="OAuth client_secret")
    parser.add_argument("--page-size", type=int, default=200, help="每页大小，默认 200，最大 200")
    parser.add_argument("--out", help="导出 JSON 文件路径（可选）")
    parser.add_argument("--verbose", action="store_true", help="打印详细日志")
    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        print("错误：需要提供 client-id/client-secret（或设置环境变量 OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET）")
        return 2

    if args.page_size < 1:
        args.page_size = 1
    if args.page_size > 200:
        args.page_size = 200

    try:
        print(f"[1/3] 使用 Client Credentials 换取访问令牌 ...")
        token = get_access_token(args.base_url, args.client_id, args.client_secret)
        print("[2/3] 令牌获取成功")

        print(f"[3/3] 拉取 base={args.base_id} table={args.table_id} 的全部记录 ...")
        records = fetch_all_records(
            args.base_url, token, args.base_id, args.table_id,
            page_size=args.page_size, verbose=args.verbose,
        )

        print(f"完成：共获取 {len(records)} 条记录")
        if records:
            print(f"示例（第 1 条）: {json.dumps(records[0], ensure_ascii=False)}")

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump({"base_id": args.base_id, "table_id": args.table_id,
                           "total": len(records), "records": records}, f,
                          ensure_ascii=False, indent=2)
            print(f"已导出到: {args.out}")
        return 0
    except RuntimeError as e:
        print(f"失败：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## 3. Java 实现

**源文件**：`tools/FetchOpenTableData.java`（JDK 11+ 标准库 `java.net.http.HttpClient`，零第三方依赖）

### 3.1 运行方式

```bash
# JDK 11+ 可直接运行单文件源码
java FetchOpenTableData.java \
  --base-id 5e6ab2ad-d45b-4535-a4c9-fe7af69cbe8b \
  --table-id d57618ce-6942-4d9a-b7f2-3144e35f704f \
  --client-id oa_6075240dd4d58c1cb19271eb621f08d2 \
  --client-secret os_TO_-UfHRPgKIltQapi9U2wYG8iGakGAUY2uzxwGfNM0
```

同样支持通过环境变量注入凭据：`OAUTH_CLIENT_ID`、`OAUTH_CLIENT_SECRET`、`SMART_TABLE_BASE_URL`。

### 3.2 完整源码

> 说明：响应 JSON 解析采用**占位实现**（`JsonHelper`），用于演示翻页与字段提取逻辑；生产环境建议接入 **Jackson / Gson** 等成熟 JSON 库解析 `data` 数组与 `meta.pagination.total_pages`。

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

/**
 * 模拟第三方应用调用 SmartTable 开放 API（OAuth2 Client Credentials）
 * 拉取指定 Base/Table 的全部记录。
 *
 * 仅作为代码逻辑样例，不依赖任何第三方库，使用 JDK 11+ 标准库 HttpClient。
 * 说明：
 *   - 响应 JSON 的解析用占位方法 parseJsonRecords() 表达，生产环境请接入
 *     Jackson/Gson 等 JSON 库解析出 data 数组与 meta.pagination.total_pages；
 *   - 翻页逻辑完整（while page <= totalPages），样例中 totalPages 从响应 meta 读取。
 *
 * 用法（示例）:
 *   java FetchOpenTableData.java \
 *     --base-id 5e6ab2ad-... \
 *     --table-id d57618ce-... \
 *     --client-id oa_xxx \
 *     --client-secret os_xxx \
 *     [--base-url http://localhost:5000] \
 *     [--page-size 200] \
 *     [--out records.json]
 */
public class FetchOpenTableData {

    // -------------------- 参数模型 --------------------
    static class Args {
        String baseUrl = System.getenv().getOrDefault("SMART_TABLE_BASE_URL", "http://localhost:5000");
        String clientId = System.getenv().getOrDefault("OAUTH_CLIENT_ID", "");
        String clientSecret = System.getenv().getOrDefault("OAUTH_CLIENT_SECRET", "");
        String baseId;
        String tableId;
        int pageSize = 200;
        String outFile;

        static Args parse(String[] argv) {
            Args a = new Args();
            for (int i = 0; i < argv.length; i++) {
                switch (argv[i]) {
                    case "--base-url": a.baseUrl = argv[++i]; break;
                    case "--client-id": a.clientId = argv[++i]; break;
                    case "--client-secret": a.clientSecret = argv[++i]; break;
                    case "--base-id": a.baseId = argv[++i]; break;
                    case "--table-id": a.tableId = argv[++i]; break;
                    case "--page-size": a.pageSize = Integer.parseInt(argv[++i]); break;
                    case "--out": a.outFile = argv[++i]; break;
                    default: throw new IllegalArgumentException("未知参数: " + argv[i]);
                }
            }
            if (a.clientId.isEmpty() || a.clientSecret.isEmpty() || a.baseId == null || a.tableId == null) {
                throw new IllegalArgumentException(
                        "必须提供 --client-id / --client-secret / --base-id / --table-id");
            }
            a.pageSize = Math.min(200, Math.max(1, a.pageSize)); // 服务端上限 200
            return a;
        }
    }

    // -------------------- 客户端封装 --------------------
    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30)).build();
    private final String baseUrl;
    private String accessToken;

    public FetchOpenTableData(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    /** 发送 JSON 请求，返回响应体字符串；非 2xx 抛异常 */
    private String send(HttpRequest.Builder builder) throws Exception {
        HttpRequest req = builder.build();
        HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() / 100 != 2) {
            throw new RuntimeException("HTTP " + resp.statusCode() + ": " + resp.body());
        }
        return resp.body();
    }

    /** 换取访问令牌（Basic Auth + grant_type=client_credentials） */
    public String getAccessToken(String clientId, String clientSecret) throws Exception {
        String basic = Base64.getEncoder().encodeToString(
                (clientId + ":" + clientSecret).getBytes(StandardCharsets.UTF_8));
        String body = send(HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/oauth/token"))
                .header("Authorization", "Basic " + basic)
                .header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString("grant_type=client_credentials")));
        String token = JsonHelper.extractString(body, "access_token");
        if (token == null) {
            throw new RuntimeException("换取令牌失败，响应缺少 access_token: " + body);
        }
        this.accessToken = token;
        return token;
    }

    /** 分页拉取指定表的所有记录 */
    public List<String> fetchAllRecords(String baseId, String tableId, int pageSize) throws Exception {
        List<String> records = new ArrayList<>();
        int page = 1;
        int totalPages = 1;

        do {
            String url = baseUrl + "/api/open/v1/bases/" + baseId + "/tables/" + tableId
                    + "/records?page=" + page + "&per_page=" + pageSize;
            String json = send(HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Bearer " + accessToken)
                    .GET());

            // data: 当前页记录数组；meta.pagination.total_pages: 总页数
            List<String> pageRecords = JsonHelper.parseJsonArray(json, "data");
            records.addAll(pageRecords);
            totalPages = JsonHelper.extractInt(json, "total_pages", totalPages);
            System.out.printf("  第 %d 页: 累计 %d 条%n", page, records.size());

            page++;
        } while (page <= totalPages);

        return records;
    }

    public static void main(String[] args) {
        try {
            Args a = Args.parse(args);
            FetchOpenTableData fetcher = new FetchOpenTableData(a.baseUrl);

            System.out.println("[1/3] 使用 Client Credentials 换取访问令牌 ...");
            fetcher.getAccessToken(a.clientId, a.clientSecret);
            System.out.println("[2/3] 令牌获取成功");

            System.out.println("[3/3] 拉取 base=" + a.baseId + " table=" + a.tableId + " 的全部记录 ...");
            List<String> records = fetcher.fetchAllRecords(a.baseId, a.tableId, a.pageSize);

            System.out.println("完成：共获取 " + records.size() + " 条记录");
            if (!records.isEmpty()) {
                System.out.println("示例（第 1 条）: " + records.get(0));
            }
            if (a.outFile != null) {
                java.nio.file.Files.writeString(
                        java.nio.file.Path.of(a.outFile),
                        "{\"total\":" + records.size() + ",\"records\":" + records + "}",
                        StandardCharsets.UTF_8);
                System.out.println("已导出到: " + a.outFile);
            }
        } catch (Exception e) {
            System.err.println("失败：" + e.getMessage());
            System.exit(1);
        }
    }

    // -------------------- 极简 JSON 工具（样例占位，生产请用 Jackson/Gson） --------------------
    static class JsonHelper {
        /** 提取字符串字段值（含引号自动去除） */
        static String extractString(String json, String field) {
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return null;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return null;
            int s = skipWs(json, colon + 1);
            if (s >= json.length() || json.charAt(s) != '"') return null;
            StringBuilder sb = new StringBuilder();
            boolean esc = false;
            for (int j = s + 1; j < json.length(); j++) {
                char c = json.charAt(j);
                if (esc) { sb.append(c); esc = false; }
                else if (c == '\\') esc = true;
                else if (c == '"') return sb.toString();
                else sb.append(c);
            }
            return null;
        }

        /** 提取整数字段值 */
        static int extractInt(String json, String field, int def) {
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return def;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return def;
            int s = skipWs(json, colon + 1);
            int e = s;
            while (e < json.length() && Character.isDigit(json.charAt(e))) e++;
            if (e == s) return def;
            try { return Integer.parseInt(json.substring(s, e)); }
            catch (NumberFormatException ex) { return def; }
        }

        /**
         * 提取 JSON 数组并切分为字符串元素（样例占位实现）。
         * 注意：此处为演示简化，实际应使用 JSON 库解析成对象列表；
         * 本方法假设数组元素均为简单 JSON 对象，按逗号切分后返回原始片段。
         */
        static List<String> parseJsonArray(String json, String field) {
            List<String> out = new ArrayList<>();
            String key = "\"" + field + "\"";
            int i = json.indexOf(key);
            if (i < 0) return out;
            int colon = json.indexOf(':', i + key.length());
            if (colon < 0) return out;
            int s = skipWs(json, colon + 1);
            if (s >= json.length() || json.charAt(s) != '[') return out;
            // 括号配对切分顶层数组元素（忽略嵌套 {} 内的逗号）
            int depth = 0, start = s + 1;
            for (int j = s + 1; j < json.length(); j++) {
                char c = json.charAt(j);
                if (c == '{' || c == '[') depth++;
                else if (c == '}' || c == ']') {
                    if (depth == 0 && c == ']') { // 数组结束
                        if (j > start) out.add(json.substring(start, j).trim());
                        break;
                    }
                    depth--;
                } else if (c == ',' && depth == 0) {
                    out.add(json.substring(start, j).trim());
                    start = j + 1;
                }
            }
            return out;
        }

        private static int skipWs(String json, int i) {
            while (i < json.length() && Character.isWhitespace(json.charAt(i))) i++;
            return i;
        }
    }
}
```

---

## 4. 两种实现对照

| 维度 | Python | Java |
|------|--------|------|
| 运行环境 | Python 3.10+（`dict | None` 语法） | JDK 11+ |
| 依赖 | 仅标准库（urllib） | 仅标准库（HttpClient） |
| 换令牌方式 | Basic Auth + `grant_type=client_credentials` | 同左 |
| 分页策略 | `while` 循环按 `total_pages` 判断结束 | `do-while` 循环按 `total_pages` 判断结束 |
| JSON 解析 | 标准库 `json` | 样例占位 `JsonHelper`，生产建议 Jackson/Gson |
| 凭据管理 | 命令行参数或环境变量 | 同左 |
| 输出 | 控制台打印 + 可选导出 JSON | 同左 |

---

## 5. 常见错误与排查

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| `HTTP 401`（换令牌失败） | client_id/secret 错误、应用已停用 | 检查凭据与应用状态 |
| `HTTP 403`（拉取记录失败） | 应用未授权该 Base，或缺少 `record:read` scope | 在后台为应用补充授权与 scope |
| `HTTP 404` | base_id / table_id 不在授权范围或不存在 | 核对资源 ID |
| 令牌过期 | access_token 有效期（默认 7200s） | 脚本每次运行重新换令牌；长期任务建议按 `expires_in` 缓存并自动续期 |

> 提示：所有通过开放 API 的调用（含读操作 `api_read`）都会记录到应用审计日志（`ApiAppAuditLog`），可结合后台「审计日志」排查调用记录。

---

## 6. 相关文件索引

- 实践文档：`doc/oauth2-practice-examples.md`（本文档）
- Python 脚本：`tools/fetch_open_table_data.py`
- Java 脚本：`tools/FetchOpenTableData.java`
- 接入说明：`doc/oauth2-integration.md`
- 开放 API 清单：`doc/open-api.md`

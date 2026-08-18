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

"""
调试 401 认证问题
"""
import requests
import json

BASE = "http://localhost:5000/api"

# 1. 登录 - 详细输出
print("=" * 60)
print("1. 登录测试")
print("=" * 60)
resp = requests.post(f"{BASE}/auth/login", json={
    "email": "ldengbin@126.com",
    "password": "LDengBin@126.com",
    "captcha": "TEST",
}, timeout=10)

print(f"  状态码: {resp.status_code}")
body = resp.json()
print(f"  响应体: {json.dumps(body, ensure_ascii=False, indent=2)[:500]}")

if resp.status_code != 200:
    print("  登录失败，中止测试")
    exit()

token = body.get("data", {}).get("tokens", {}).get("access_token", "")
print(f"\n  Token 前20位: {token[:20]}...")
print(f"  Token 长度: {len(token)}")

# 2. 用 token 调用 verify-token
print("\n" + "=" * 60)
print("2. 验证令牌有效性")
print("=" * 60)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
resp = requests.get(f"{BASE}/auth/verify-token", headers=headers, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  响应体: {json.dumps(resp.json(), ensure_ascii=False, indent=2)[:500]}")

# 3. 获取 bases
print("\n" + "=" * 60)
print("3. 获取 Bases")
print("=" * 60)
resp = requests.get(f"{BASE}/bases", headers=headers, timeout=10)
print(f"  状态码: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json().get("data", [])
    if data:
        print(f"  第一个 base ID: {data[0]['id']}")
    else:
        print("  没有base数据")
else:
    print(f"  响应体: {json.dumps(resp.json(), ensure_ascii=False, indent=2)[:500]}")

# 4. 用完全相同的 headers 测试 batch 接口
print("\n" + "=" * 60)
print("4. 测试 batch 接口（用小数据量）")
print("=" * 60)

# 先获取一个表格
resp = requests.get(f"{BASE}/bases", headers=headers, timeout=10)
if resp.status_code == 200:
    data = resp.json().get("data", [])
    if data:
        base_id = data[0]["id"]
        resp = requests.get(f"{BASE}/bases/{base_id}/tables", headers=headers, timeout=10)
        print(f"  获取表格状态码: {resp.status_code}")
        tables = resp.json().get("data", [])
        if tables:
            table_id = tables[0]["id"]
            # 测试 batch 接口
            test_records = {"records": [{"values": {"test": "value"}}]}
            resp = requests.post(f"{BASE}/tables/{table_id}/records/batch", headers=headers, json=test_records, timeout=10)
            print(f"  Batch 接口状态码: {resp.status_code}")
            print(f"  响应体: {json.dumps(resp.json(), ensure_ascii=False, indent=2)[:500]}")
        else:
            print("  没有表格数据")
    else:
        print("  没有base数据")
else:
    print(f"  获取bases失败")
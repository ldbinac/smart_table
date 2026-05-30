"""
验证批量接口优化效果
对比：批量 bulk insert vs 逐条 ORM
"""
import requests
import json
import time

BASE = "http://localhost:5000/api"

# 1. 登录
resp = requests.post(f"{BASE}/auth/login", json={
    "email": "ldengbin@126.com",
    "password": "LDengBin@126.com",
    "captcha": "TEST",
}, timeout=10)
token = resp.json()["data"]["tokens"]["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("1. 登录成功")

# 2. 获取 base
resp = requests.get(f"{BASE}/bases", headers=headers, timeout=10)
base_id = resp.json()["data"][0]["id"]
print(f"2. base: {base_id[:8]}...")

# 3. 获取测试表格
resp = requests.get(f"{BASE}/bases/{base_id}/tables", headers=headers, timeout=10)
tables = resp.json().get("data", [])
ts_id = None
for t in tables:
    if "测试" in t.get("name", ""):
        ts_id = t["id"]
        break
if not ts_id:
    print("  创建测试表格...")
    resp = requests.post(f"{BASE}/bases/{base_id}/tables", headers=headers, json={
        "name": "性能测试表格", "description": "批量导入测试"
    })
    ts_id = resp.json()["data"]["id"]
    requests.post(f"{BASE}/tables/{ts_id}/fields", headers=headers, json={"name": "姓名", "type": "text", "isSystem": False})
    requests.post(f"{BASE}/tables/{ts_id}/fields", headers=headers, json={"name": "年龄", "type": "number", "isSystem": False})
print(f"3. 测试表格: {ts_id[:8]}...")

# 4. 获取字段映射
resp = requests.get(f"{BASE}/tables/{ts_id}/fields", headers=headers, timeout=10)
data = resp.json()
fields = data.get("data", data.get("items", []))
fmap = {}
for f in fields:
    fmap[f.get("name", "")] = f.get("id", "")
print(f"4. 字段: {list(fmap.keys())}")

print()
print("=" * 60)
print("对比测试：批量 bulk_insert  vs  逐条 ORM")
print("=" * 60)

# ===== 测试 1: 批量 100 条 =====
name_field = fmap.get("姓名") or fmap.get("文本") or list(fmap.values())[0]
age_field = fmap.get("年龄") or list(fmap.values())[1] if len(fmap) > 1 else name_field
recs = [{"values": {name_field: f"批量100_{i}", age_field: 20 + i % 30}} for i in range(100)]
start = time.time()
resp = requests.post(f"{BASE}/tables/{ts_id}/records/batch", headers=headers, json={"records": recs}, timeout=60)
t1 = time.time() - start
d = resp.json()
resp_body = json.dumps(d, ensure_ascii=False)
if resp.status_code != 200:
    print(f"  [ERROR] body: {resp_body[:300]}")
print(f"\n批量 100条: {t1*1000:.0f}ms  ({100/t1:.0f} 条/秒)  state={resp.status_code}")

# ===== 测试 2: 批量 1000 条 =====
recs2 = [{"values": {name_field: f"批量1k_{i}", age_field: 20 + i % 30}} for i in range(1000)]
start = time.time()
resp2 = requests.post(f"{BASE}/tables/{ts_id}/records/batch", headers=headers, json={"records": recs2}, timeout=120)
t2 = time.time() - start
data2 = resp2.json()
if resp2.status_code != 200:
    print(f"  [ERROR] body: {json.dumps(data2, ensure_ascii=False)[:300]}")
print(f"批量 1000条: {t2*1000:.0f}ms  ({1000/t2:.0f} 条/秒)  state={resp2.status_code}")

# ===== 测试 3: 逐条 50 条 =====
recs3 = [{"values": {name_field: f"逐条_{i}", age_field: 20 + i % 30}} for i in range(50)]
start = time.time()
for r in recs3:
    requests.post(f"{BASE}/tables/{ts_id}/records", headers=headers, json=r, timeout=10)
t3 = time.time() - start
print(f"逐条 50条:   {t3*1000:.0f}ms  ({50/t3:.0f} 条/秒)")

# ===== 对比结果 =====
print()
print("=" * 60)
print("结果对比:")
print(f"  批量 100条  -> {100/t1:.0f} 条/秒")
print(f"  批量 1000条 -> {1000/t2:.0f} 条/秒")
print(f"  逐条 50条   -> {50/t3:.0f} 条/秒")
print()
print(f"  提升倍数:")
per_sec_batch = 1000 / t2
per_sec_single = 50 / t3
print(f"    批量1000条 vs 逐条50条: {per_sec_batch/per_sec_single:.1f}x")
print("=" * 60)
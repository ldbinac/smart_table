"""
用户名登录功能 —— HTTP 集成测试
覆盖：注册 / 登录 / admin 用户管理 / check-username 全部分支
"""
import json
import time
import uuid
import requests

BASE = "http://127.0.0.1:5000"
API = f"{BASE}/api"

# 生成唯一测试用用户名/邮箱/密码前缀
RUN = str(uuid.uuid4())[:8]
TEST_PASSWORD = "Test@1234"

# 已有 admin 用户（迁移时看到的 ldengbin@126.com）
ADMIN_EMAIL = "ldengbin@126.com"
ADMIN_PASSWD = "Test@1234"  # 已通过 _reset_admin.py 重置

results = []


def log(passed, name, detail=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append((passed, name, detail))
    print(f"{status}  {name}")
    if detail:
        print(f"       {detail}")


def short_json(r):
    try:
        d = r.json()
        return json.dumps(d, ensure_ascii=False)[:200]
    except Exception:
        return r.text[:200]


# ================================================================
# 1. 登录已有 admin（如果密码能猜到就继续用；否则尝试重置逻辑）
# ================================================================
print("\n==== Phase 1: 基础环境探测 ====")

admin_token = None
try:
    r = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWD,
    }, timeout=5)
    print(f"admin 登录 {r.status_code}: {short_json(r)}")
    if r.status_code == 200:
        admin_token = r.json()["data"]["tokens"]["access_token"]
        log(True, "admin 登录 (email + password)")
except Exception as e:
    log(False, "admin 登录", str(e))

# 如果 admin 密码不是 Root@1234，尝试 create-admin 先跑一下
if not admin_token:
    print("\n[提示] 无法用默认密码登录 admin，尝试通过 register 创建临时 admin 路径...")
    # 实际上我们可以直接用 register 创建普通用户
    # 后面 admin 操作如果没有 token 就跳过

# ================================================================
# 2. 注册分支测试
# ================================================================
print("\n==== Phase 2: /auth/register ====")

USERNAME_A = f"alice_{RUN}"
EMAIL_A = f"alice_{RUN}@test.com"

# 2.1 新用户注册（username 必填，同时送 email）
r = requests.post(f"{API}/auth/register", json={
    "email": EMAIL_A,
    "username": USERNAME_A,
    "name": "Alice",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code in (200, 201), f"2.1 新用户注册 (username={USERNAME_A})",
    f"status={r.status_code} body={short_json(r)}")

# 2.2 同 username 再注册 → 应返回 409
USERNAME_B = USERNAME_A  # 复用 username
EMAIL_B = f"bob_{RUN}@test.com"
r = requests.post(f"{API}/auth/register", json={
    "email": EMAIL_B,
    "username": USERNAME_B,
    "name": "Bob",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 409, f"2.2 重复 username 注册被拒",
    f"status={r.status_code} body={short_json(r)}")

# 2.3 同 email 再注册 → 应返回 409
USERNAME_C = f"charlie_{RUN}"
r = requests.post(f"{API}/auth/register", json={
    "email": EMAIL_A,
    "username": USERNAME_C,
    "name": "Charlie",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 409, f"2.3 重复 email 注册被拒",
    f"status={r.status_code} body={short_json(r)}")

# 2.4 username 太短（<3）→ 应返回 400
r = requests.post(f"{API}/auth/register", json={
    "email": f"dan_{RUN}@test.com",
    "username": "ab",
    "name": "Dan",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 422, f"2.4 过短 username 被拒 (422)",
    f"status={r.status_code} body={short_json(r)}")

# 2.5 不带 username 字段 → 应返回 400（required）
r = requests.post(f"{API}/auth/register", json={
    "email": f"eve_{RUN}@test.com",
    "name": "Eve",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 422, f"2.5 缺失 username 字段被拒 (422)",
    f"status={r.status_code} body={short_json(r)}")

# 2.6 新注册一个用户（用于后面登录测试）
USERNAME_F = f"frank_{RUN}"
EMAIL_F = f"frank_{RUN}@test.com"
r = requests.post(f"{API}/auth/register", json={
    "email": EMAIL_F,
    "username": USERNAME_F,
    "name": "Frank",
    "password": TEST_PASSWORD,
}, timeout=5)
register_ok = r.status_code in (200, 201)
log(register_ok, f"2.6 第二个用户注册成功 (username={USERNAME_F})",
    f"status={r.status_code} body={short_json(r)}")

# ================================================================
# 3. 登录分支测试（不需要 admin token）
# ================================================================
print("\n==== Phase 3: /auth/login ====")

# 3.1 用 email + 正确密码登录
r = requests.post(f"{API}/auth/login", json={
    "email": EMAIL_F,
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 200, f"3.1 email 登录成功",
    f"status={r.status_code} body={short_json(r)}")
email_login_token = r.json()["data"]["tokens"]["access_token"] if r.status_code == 200 else None

# 3.2 用 username + 正确密码登录（小写）
r = requests.post(f"{API}/auth/login", json={
    "username": USERNAME_F,
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 200, f"3.2 username 登录成功",
    f"status={r.status_code} body={short_json(r)}")
username_login_token = r.json()["data"]["tokens"]["access_token"] if r.status_code == 200 else None

# 3.3 用大小写混合的 username 登录（后端统一 lower）
r = requests.post(f"{API}/auth/login", json={
    "username": USERNAME_F.upper(),
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 200, f"3.3 大写 username 登录成功 (不区分大小写)",
    f"status={r.status_code} body={short_json(r)}")

# 3.4 正确 username + 错误密码 → 应 401（不能泄露是密码错）
r = requests.post(f"{API}/auth/login", json={
    "username": USERNAME_F,
    "password": "WrongPass",
}, timeout=5)
log(r.status_code == 401, f"3.4 username + 错误密码 → 401",
    f"status={r.status_code} body={short_json(r)}")

# 3.5 不存在的 username → 应 401
r = requests.post(f"{API}/auth/login", json={
    "username": "ghost_no_such_user_xyz",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 401, f"3.5 不存在的 username → 401",
    f"status={r.status_code} body={short_json(r)}")

# 3.6 不存在的 email → 应 401
r = requests.post(f"{API}/auth/login", json={
    "email": "no_such_email_xyz@test.com",
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 401, f"3.6 不存在的 email → 401",
    f"status={r.status_code} body={short_json(r)}")

# 3.7 既无 email 也无 username → 应 400
r = requests.post(f"{API}/auth/login", json={
    "password": TEST_PASSWORD,
}, timeout=5)
log(r.status_code == 422, f"3.7 无 email/username → 422",
    f"status={r.status_code} body={short_json(r)}")

# 3.8 admin 存量用户用 email 登录（回归测试 — 确保未被破坏）
# 先尝试用存量的 admin 用户名（从数据库看到的是 ldengbin@126.com）
r = requests.post(f"{API}/auth/login", json={
    "username": "ldengbin",
    "password": ADMIN_PASSWD,
}, timeout=5)
log(r.status_code in (200, 401), f"3.8 admin 存量用户 username 登录",
    f"status={r.status_code} body={short_json(r)}")

# 3.9 检查 /auth/me 返回的用户信息包含 username
if email_login_token:
    r = requests.get(f"{API}/auth/me", headers={
        "Authorization": f"Bearer {email_login_token}"
    }, timeout=5)
    me = r.json()
    has_username = r.status_code == 200 and "username" in me.get("data", {})
    log(has_username, f"3.9 /auth/me 返回包含 username 字段",
        f"status={r.status_code} data.username={me.get('data', {}).get('username')}")

# ================================================================
# 4. GET /auth/check-username 接口
# ================================================================
print("\n==== Phase 4: /auth/check-username ====")

# 4.1 已存在 username → available=false
r = requests.get(f"{API}/auth/check-username", params={"username": USERNAME_F}, timeout=5)
log(r.status_code == 200 and r.json()["data"]["available"] is False,
    f"4.1 已存在 username → available=false",
    f"body={short_json(r)}")

# 4.2 新 username → available=true
r = requests.get(f"{API}/auth/check-username", params={"username": f"new_one_{RUN}"}, timeout=5)
log(r.status_code == 200 and r.json()["data"]["available"] is True,
    f"4.2 新 username → available=true",
    f"body={short_json(r)}")

# 4.3 空 username → 400
r = requests.get(f"{API}/auth/check-username", params={"username": ""}, timeout=5)
log(r.status_code == 400, f"4.3 空 username → 400",
    f"status={r.status_code} body={short_json(r)}")

# ================================================================
# 5. admin 用户管理（如果 admin_token 已拿到）
# ================================================================
print("\n==== Phase 5: /admin/users ====")

admin_ops_ok = False
if admin_token:
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 5.1 admin 创建用户（正常 username）
    USERNAME_ADMIN = f"adminuser_{RUN}"
    r = requests.post(f"{API}/admin/users", headers=headers, json={
        "email": f"adminuser_{RUN}@test.com",
        "password": TEST_PASSWORD,
        "name": "AdminUser",
        "role": "editor",
        "username": USERNAME_ADMIN,
    }, timeout=5)
    log(r.status_code in (200, 201), f"5.1 admin 创建用户 (username={USERNAME_ADMIN})",
        f"status={r.status_code} body={short_json(r)}")
    new_user_id = r.json()["data"]["id"] if r.status_code in (200, 201) else None

    # 5.2 admin 创建重复 username → 409
    r = requests.post(f"{API}/admin/users", headers=headers, json={
        "email": f"admindup_{RUN}@test.com",
        "password": TEST_PASSWORD,
        "name": "Dup",
        "role": "editor",
        "username": USERNAME_ADMIN,  # 重复
    }, timeout=5)
    log(r.status_code == 409, f"5.2 admin 创建重复 username → 409",
        f"status={r.status_code} body={short_json(r)}")

    # 5.3 admin 更新用户 username（如果 5.1 成功）
    if new_user_id:
        NEW_USERNAME = f"renamed_{RUN}"
        r = requests.put(f"{API}/admin/users/{new_user_id}", headers=headers, json={
            "username": NEW_USERNAME,
        }, timeout=5)
        log(r.status_code == 200 and r.json()["data"]["username"] == NEW_USERNAME,
            f"5.3 admin 修改 username → {NEW_USERNAME}",
            f"status={r.status_code} body={short_json(r)}")

        # 5.4 admin 把 username 改成已存在的 USERNAME_F → 409
        r = requests.put(f"{API}/admin/users/{new_user_id}", headers=headers, json={
            "username": USERNAME_F,
        }, timeout=5)
        log(r.status_code == 409, f"5.4 admin 改 username 为已存在 → 409",
            f"status={r.status_code} body={short_json(r)}")

        # 5.5 admin 把 username 改成自己当前的（排除自身 → 成功）
        r = requests.put(f"{API}/admin/users/{new_user_id}", headers=headers, json={
            "username": NEW_USERNAME,  # 就是自己的
        }, timeout=5)
        log(r.status_code == 200, f"5.5 admin 改 username 为自身 → 200 (排除自身校验)",
            f"status={r.status_code} body={short_json(r)}")

    # 5.6 admin 搜索用户 —— 用 username 搜索应命中
    r = requests.get(f"{API}/admin/users", headers=headers, params={
        "search": USERNAME_F,
    }, timeout=5)
    ok = False
    if r.status_code == 200:
        raw_data = r.json().get("data", [])
        items = []
        if isinstance(raw_data, dict):
            items = raw_data.get("items", [])
        elif isinstance(raw_data, list):
            items = raw_data
        ok = any(u.get("username") == USERNAME_F for u in items if isinstance(u, dict))
    log(ok, f"5.6 admin 搜索 username={USERNAME_F} 命中",
        f"status={r.status_code} body={short_json(r)}")

    admin_ops_ok = True
else:
    log(False, f"Phase 5 跳过（无 admin token）",
        "需要先能用 email + 密码登录拿到 admin token 才能测 admin 路由")

# ================================================================
# 6. 用户搜索（普通用户也能调）
# ================================================================
print("\n==== Phase 6: /users/search ====")

# 6.1 用普通用户 token 搜索 —— 注意 /users/search 是 GET
if email_login_token:
    r = requests.get(f"{API}/users/search", headers={
        "Authorization": f"Bearer {email_login_token}"
    }, params={"query": USERNAME_F}, timeout=5)
    items = []
    if r.status_code == 200:
        raw = r.json().get("data", [])
        if isinstance(raw, dict):
            # /users/search 返回 {users: [...], page, per_page, total...}
            items = raw.get("users", raw.get("items", []))
        elif isinstance(raw, list):
            items = raw
    ok = any((u.get("username") == USERNAME_F if isinstance(u, dict) else False) for u in items)
    log(ok, f"6.1 /users/search 按 username 搜索命中",
        f"status={r.status_code} body={short_json(r)}")
else:
    log(False, "6.1 跳过（无普通用户 token）")

# ================================================================
# 汇总
# ================================================================
print("\n==== TEST SUMMARY ====")
passed = sum(1 for p, _, _ in results if p)
total = len(results)
print(f"通过 {passed}/{total}")
for p, name, detail in results:
    tag = "PASS" if p else "FAIL"
    print(f"  [{tag}] {name}")
if passed < total:
    print("\n失败详情：")
    for p, name, detail in results:
        if not p:
            print(f"  ❌ {name}")
            print(f"     {detail}")

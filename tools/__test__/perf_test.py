"""
SmartTable 导入功能性能测试脚本
对比测试：批量导入 vs 逐条导入
"""
import json
import time
import random
import string
import sys
import os
import requests
from datetime import datetime

API_BASE = "http://localhost:5000/api"
ADMIN_EMAIL = "ldengbin@126.com"
ADMIN_PASSWORD = "LDengBin@126.com"

TEST_RECORD_COUNT = 5000
BATCH_SIZE = 100
DYNAMIC_DELAY = 600

COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "GREEN": "\033[92m",
    "WARNING": "\033[93m",
    "RED": "\033[91m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

token = None
test_table_id = None


def log(msg, color=""):
    print(f"{color}{msg}{COLORS['RESET']}")


def make_request(method, path, **kwargs):
    global token
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API_BASE}{path}"

    try:
        resp = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        return resp
    except requests.exceptions.Timeout:
        log(f"  [超时] {method} {path}", COLORS["RED"])
        return None
    except requests.exceptions.RequestException as e:
        log(f"  [请求失败] {method} {path}: {e}", COLORS["RED"])
        return None


def get_captcha():
    """获取验证码"""
    resp = make_request("GET", "/auth/captcha?key=login")
    if resp and resp.status_code == 200:
        data = resp.json()
        return data.get("data", {}).get("image", "")
    return None


def login():
    """登录获取 token"""
    global token
    log("正在登录管理员账号...", COLORS["BLUE"])

    resp = make_request("POST", "/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "captcha": "TEST",
    })

    if resp and resp.status_code == 200:
        data = resp.json()
        token = data["data"]["tokens"]["access_token"]
        log(f"  [成功] 登录成功, 用户: {data['data']['user']['name']}", COLORS["GREEN"])
        return True

    body = resp.json() if resp else {"message": "无响应"}
    log(f"  [失败] 登录失败: {body}", COLORS["RED"])
    return False


def find_or_create_test_table():
    """查找或创建测试表格"""
    global test_table_id
    log("\n查找已有的 base...", COLORS["BLUE"])
    bases_resp = make_request("GET", "/bases")
    base_id = None
    if bases_resp and bases_resp.status_code == 200:
        bases = bases_resp.json().get("data", [])
        if bases:
            base_id = bases[0]["id"]
            log(f"  [成功] 找到 base: {base_id[:8]}...", COLORS["GREEN"])

    if not base_id:
        log("  [失败] 无法获取 base_id", COLORS["RED"])
        return False

    log("查找已有的测试表格...", COLORS["BLUE"])
    resp = make_request("GET", f"/bases/{base_id}/tables")
    if resp and resp.status_code == 200:
        data = resp.json()
        tables = data.get("data", [])
        for table in tables:
            name = table.get("name", "")
            if "测试" in name or name == "绩效数据":
                test_table_id = table["id"]
                log(f"  [成功] 找到测试表格: {name} (ID: {test_table_id[:8]}...)", COLORS["GREEN"])
                return True

    log("未找到测试表格，尝试创建...", COLORS["WARNING"])

    resp = make_request("POST", f"/bases/{base_id}/tables", json={
        "base_id": base_id,
        "name": "性能测试表格",
        "description": "用于批量导入性能测试",
    })

    if resp and resp.status_code in (200, 201):
        data = resp.json()
        test_table_id = data.get("data", {}).get("id", data.get("id"))
        log(f"  [成功] 创建测试表格, ID: {str(test_table_id)[:8]}...", COLORS["GREEN"])

        field_resp = make_request("POST", f"/tables/{test_table_id}/fields", json={
            "name": "姓名",
            "type": "text",
            "isSystem": False,
        })
        if field_resp and field_resp.status_code in (200, 201):
            log("  [成功] 创建字段: 姓名", COLORS["GREEN"])

        field_resp2 = make_request("POST", f"/tables/{test_table_id}/fields", json={
            "name": "年龄",
            "type": "number",
            "isSystem": False,
        })
        if field_resp2 and field_resp2.status_code in (200, 201):
            log("  [成功] 创建字段: 年龄", COLORS["GREEN"])

        field_resp3 = make_request("POST", f"/tables/{test_table_id}/fields", json={
            "name": "部门",
            "type": "text",
            "isSystem": False,
        })
        if field_resp3 and field_resp3.status_code in (200, 201):
            log("  [成功] 创建字段: 部门", COLORS["GREEN"])

        return True

    log(f"  [失败] 创建表格失败", COLORS["RED"])
    return False


def generate_test_data(count):
    """生成测试数据"""
    log(f"\n生成 {count} 条测试数据...", COLORS["BLUE"])
    departments = ["技术部", "市场部", "销售部", "人事部", "财务部", "研发中心", "客服部", "行政部"]
    data = []
    for i in range(count):
        data.append({
            "姓名": f"测试用户_{i+1:05d}",
            "年龄": random.randint(22, 55),
            "部门": random.choice(departments),
        })
    log(f"  [完成] 已生成 {len(data)} 条测试数据", COLORS["GREEN"])
    return data


def get_field_map(table_id):
    """获取表格字段映射"""
    resp = make_request("GET", f"/tables/{table_id}/fields")
    if not resp or resp.status_code != 200:
        log("  [失败] 无法获取字段信息", COLORS["RED"])
        return {}

    data = resp.json()
    fields = data.get("data", data.get("items", []))
    if isinstance(fields, dict):
        fields = fields.get("fields", [])

    field_map = {}
    for f in fields:
        field_map[f.get("name", "")] = f.get("id", "")
    return field_map


def single_record_import(table_id, records, field_map):
    """逐条导入（原方式）"""
    log("\n" + "=" * 60)
    log("测试方式一：逐条导入（原始方式）", COLORS["HEADER"] + COLORS["BOLD"])
    log("=" * 60)

    success = 0
    failed = 0
    errors = []
    start_time = time.time()

    for i, record in enumerate(records):
        values = {}
        for key, val in record.items():
            if key in field_map and field_map[key]:
                values[field_map[key]] = val

        resp = make_request("POST", f"/tables/{table_id}/records", json={"values": values})

        if resp and resp.status_code in (200, 201):
            success += 1
        else:
            failed += 1
            status_code = resp.status_code if resp else "N/A"
            errors.append(f"  行 {i+1}: HTTP {status_code}")

        if (i + 1) % 500 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            log(f"  进度: {i+1}/{len(records)} 耗时: {elapsed:.1f}s 速率: {rate:.1f}条/s", COLORS["BLUE"])

    total_time = time.time() - start_time
    rate = len(records) / total_time if total_time > 0 else 0

    result = {
        "total": len(records),
        "success": success,
        "failed": failed,
        "total_time": total_time,
        "rate": rate,
        "errors": errors[:5],
    }
    return result


def batch_import(table_id, records, field_map, batch_size=100, delay=600):
    """批量导入（新方式）"""
    log("\n" + "=" * 60)
    log("测试方式二：批量导入（优化后）", COLORS["HEADER"] + COLORS["BOLD"])
    log("=" * 60)

    batches = []
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_records = []
        for record in batch:
            values = {}
            for key, val in record.items():
                if key in field_map and field_map[key]:
                    values[field_map[key]] = val
            batch_records.append({"values": values})
        batches.append(batch_records)

    total_batches = len(batches)
    log(f"  总记录数: {len(records)}, 分 {total_batches} 批次, 每批 {batch_size} 条", COLORS["BLUE"])
    log(f"  批次间隔延迟: {delay}ms, 动态调整: 启用", COLORS["BLUE"])
    log(f"  超时设置: 30000ms, 最大重试: 3 次", COLORS["BLUE"])

    success = 0
    failed = 0
    batch_errors = []
    response_times = []
    current_delay = delay
    start_time = time.time()
    retry_count = 0

    for batch_idx, batch in enumerate(batches):
        if retry_count >= 3:
            log(f"  [严重] 连续失败达到上限，导入终止", COLORS["RED"])
            remaining = sum(len(b) for b in batches[batch_idx:])
            failed += remaining
            break

        batch_size_actual = len(batch)
        batch_start = time.time()
        batch_succeeded = False

        for attempt in range(4):
            resp = make_request(
                "POST",
                f"/tables/{table_id}/records/batch",
                json={"records": batch},
            )

            if resp and resp.status_code in (200, 201):
                data = resp.json().get("data", {})
                created_count = data.get("created_count", 0)
                success += created_count
                response_time = (time.time() - batch_start) * 1000
                response_times.append(response_time)
                batch_succeeded = True
                retry_count = 0

                if response_time > (sum(response_times) / len(response_times)) * 1.5:
                    current_delay = min(current_delay * 1.3, 5000)
                elif response_time < (sum(response_times) / len(response_times)) * 0.5 and len(response_times) > 3:
                    current_delay = max(current_delay * 0.9, 200)

                elapsed = time.time() - start_time
                progress = (batch_idx + 1) / total_batches * 100
                avg_time = sum(response_times) / len(response_times) if response_times else 0
                remaining_batches = total_batches - batch_idx - 1
                eta = (remaining_batches * (avg_time + current_delay)) / 1000

                log(
                    f"  批次 {batch_idx+1}/{total_batches} "
                    f"[{'#' * int(progress // 5)}{' ' * (20 - int(progress // 5))}] "
                    f"{progress:.0f}% | "
                    f"成功: {success} | "
                    f"耗时: {elapsed:.1f}s | "
                    f"响应: {response_time:.0f}ms | "
                    f"延迟: {current_delay:.0f}ms | "
                    f"ETA: {eta:.0f}s",
                    COLORS["GREEN"] if response_time < 1000 else COLORS["WARNING"],
                )
                break
            else:
                status_code = resp.status_code if resp else "无响应"
                if status_code == 429:
                    wait_time = (2 ** (attempt + 2)) * 1000
                    log(f"  批次 {batch_idx+1}: 触发限流(429)，等待 {wait_time/1000:.0f}s 后重试 ({attempt+1}/3)", COLORS["WARNING"])
                    time.sleep(wait_time / 1000)
                    continue
                elif attempt < 3:
                    wait_time = (2 ** (attempt + 1)) * 1000
                    log(f"  批次 {batch_idx+1}: 失败(HTTP {status_code})，{wait_time/1000:.0f}s 后重试 ({attempt+1}/3)", COLORS["WARNING"])
                    time.sleep(wait_time / 1000)
                    continue
                else:
                    failed += batch_size_actual
                    batch_errors.append({
                        "batch": batch_idx + 1,
                        "count": batch_size_actual,
                        "status": status_code,
                    })
                    log(f"  批次 {batch_idx+1}: 失败(HTTP {status_code})，已跳过", COLORS["RED"])
                    retry_count += 1

        if batch_succeeded and batch_idx < total_batches - 1:
            time.sleep(current_delay / 1000)

    total_time = time.time() - start_time
    rate = (success + failed) / total_time if total_time > 0 else 0
    avg_response = sum(response_times) / len(response_times) if response_times else 0

    result = {
        "total": len(records),
        "success": success,
        "failed": failed,
        "total_time": total_time,
        "rate": rate,
        "total_batches": total_batches,
        "avg_response_time": avg_response,
        "final_delay": current_delay,
        "errors": batch_errors[:5],
    }
    return result


def clear_test_records(table_id):
    """清理测试数据"""
    log("\n清理测试数据...", COLORS["BLUE"])
    resp = make_request("GET", f"/tables/{table_id}/records?per_page=5000")
    if not resp or resp.status_code != 200:
        log("  [跳过] 无法获取记录列表", COLORS["WARNING"])
        return

    data = resp.json()
    records = []
    if isinstance(data, dict):
        d = data.get("data", data)
        if isinstance(d, dict):
            records = d.get("items", d.get("data", data.get("items", [])))
        elif isinstance(d, list):
            records = d

    if not records:
        log("  没有需要清理的记录", COLORS["GREEN"])
        return

    ids = [r.get("id", r.get("_id", "")) for r in records if r.get("id", r.get("_id", ""))]
    if not ids:
        log("  [跳过] 无法获取记录ID", COLORS["WARNING"])
        return

    batch_size_del = 500
    deleted_total = 0
    for i in range(0, len(ids), batch_size_del):
        batch_ids = ids[i:i + batch_size_del]
        resp = make_request("DELETE", "/records/batch", json={"record_ids": batch_ids})
        if resp and resp.status_code in (200, 204):
            deleted_total += len(batch_ids)

    log(f"  [完成] 已清理 {deleted_total} 条记录", COLORS["GREEN"])


def print_comparison_report(single_result, batch_result):
    """打印对比报告"""
    log("\n", "")
    log("=" * 70, COLORS["HEADER"] + COLORS["BOLD"])
    log("           批量导入性能对比测试报告", COLORS["HEADER"] + COLORS["BOLD"])
    log("=" * 70, COLORS["HEADER"] + COLORS["BOLD"])

    log(f"\n📋 测试环境", COLORS["BOLD"])
    log(f"  • 测试记录数: {TEST_RECORD_COUNT:,} 条")
    log(f"  • 每批大小: {BATCH_SIZE} 条")
    log(f"  • 批次间隔: {DYNAMIC_DELAY}ms (动态调整)")
    log(f"  • 数据库: PostgreSQL")
    log(f"  • 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    log(f"\n📊 性能指标对比", COLORS["BOLD"])
    log(f"  {'指标':<20} {'逐条导入(旧)':<20} {'批量导入(新)':<20} {'提升':<15}")
    log(f"  {'-'*70}")

    single_rate = single_result["rate"]
    batch_rate = batch_result["rate"]
    speedup = batch_rate / single_rate if single_rate > 0 else float('inf')

    single_time = f"{single_result['total_time']:.1f}s"
    batch_time = f"{batch_result['total_time']:.1f}s"
    speedup_time = f"{single_result['total_time']/batch_result['total_time']:.1f}x"
    log(f"  {'总耗时':<20} {single_time:<20} {batch_time:<20} {speedup_time:<15}")

    single_rate_str = f"{single_rate:.1f}条/s"
    batch_rate_str = f"{batch_rate:.1f}条/s"
    speedup_str = f"{speedup:.1f}x"
    log(f"  {'导入速率':<20} {single_rate_str:<20} {batch_rate_str:<20} {speedup_str:<15}")

    single_success = f"{single_result['success']:,}"
    batch_success = f"{batch_result['success']:,}"
    log(f"  {'成功数':<20} {single_success:<20} {batch_success:<20}")
    single_failed = f"{single_result['failed']:,}"
    batch_failed = f"{batch_result['failed']:,}"
    log(f"  {'失败数':<20} {single_failed:<20} {batch_failed:<20}")

    if batch_result.get("avg_response_time"):
        avg_resp = f"{batch_result['avg_response_time']:.0f}ms"
        log(f"  {'平均响应时间':<20} {'N/A':<20} {avg_resp:<20}")

    if batch_result.get("total_batches"):
        single_total = f"{single_result['total']:,}"
        batch_total = str(batch_result['total_batches'])
        req_reduction = f"{single_result['total']/batch_result['total_batches']:.0f}x"
        log(f"  {'HTTP请求次数':<20} {single_total:<20} {batch_total:<20} {req_reduction:<15}")

    log(f"\n🏆 结论", COLORS["BOLD"])
    if speedup > 1:
        log(f"  ✅ 批量导入比逐条导入快了 {speedup:.1f} 倍", COLORS["GREEN"] + COLORS["BOLD"])
    else:
        log(f"  ⚠️ 批量导入性能有待进一步优化", COLORS["WARNING"])

    log(f"\n📈 流量分析", COLORS["BOLD"])
    log(f"  • 逐条导入: {single_result['total']} 次 HTTP 请求")
    log(f"  • 批量导入: {batch_result.get('total_batches', 'N/A')} 次 HTTP 请求")
    if batch_result.get("total_batches"):
        log(f"  • 请求流量降低: {single_result['total'] / batch_result['total_batches']:.0f} 倍", COLORS["GREEN"])

    if single_result.get("errors"):
        log(f"\n⚠️ 逐条导入错误示例:", COLORS["WARNING"])
        for err in single_result["errors"][:3]:
            log(f"  {err}")

    if batch_result.get("errors"):
        log(f"\n⚠️ 批量导入错误示例:", COLORS["WARNING"])
        for err in batch_result["errors"][:3]:
            log(f"  批次 {err.get('batch', '?')}: HTTP {err.get('status', '?')}")

    log("\n" + "=" * 70, COLORS["HEADER"] + COLORS["BOLD"])
    log("", "")


def run_test():
    """运行完整测试"""
    log("=" * 70, COLORS["HEADER"] + COLORS["BOLD"])
    log("     SmartTable 导入功能性能测试", COLORS["HEADER"] + COLORS["BOLD"])
    log("=" * 70, COLORS["HEADER"] + COLORS["BOLD"])

    if not login():
        log("\n[失败] 请确认后端服务已在 http://localhost:5000 上运行", COLORS["RED"])
        sys.exit(1)

    if not find_or_create_test_table():
        log("\n[失败] 请手动创建一个测试表格", COLORS["RED"])
        sys.exit(1)

    field_map = get_field_map(test_table_id)
    if not field_map:
        log("[失败] 无法获取字段映射", COLORS["RED"])
        sys.exit(1)
    log(f"  字段映射: {list(field_map.keys())}", COLORS["GREEN"])

    test_data = generate_test_data(TEST_RECORD_COUNT)

    single_result = single_record_import(test_table_id, test_data[:100], field_map)

    log(f"\n等待 5 秒后开始批量导入测试...", COLORS["WARNING"])
    time.sleep(5)

    clear_test_records(test_table_id)
    time.sleep(2)

    batch_result = batch_import(test_table_id, test_data, field_map, BATCH_SIZE, DYNAMIC_DELAY)

    print_comparison_report(single_result, batch_result)

    log(f"\n💾 保存测试报告到文件...", COLORS["BLUE"])
    report = {
        "test_time": datetime.now().isoformat(),
        "environment": {
            "record_count": TEST_RECORD_COUNT,
            "batch_size": BATCH_SIZE,
            "base_delay_ms": DYNAMIC_DELAY,
            "database": "PostgreSQL",
        },
        "single_record_import": {
            "total_records": single_result["total"],
            "success": single_result["success"],
            "failed": single_result["failed"],
            "total_time_seconds": round(single_result["total_time"], 2),
            "rate_per_second": round(single_result["rate"], 2),
        },
        "batch_import": {
            "total_records": batch_result["total"],
            "success": batch_result["success"],
            "failed": batch_result["failed"],
            "total_time_seconds": round(batch_result["total_time"], 2),
            "rate_per_second": round(batch_result["rate"], 2),
            "total_batches": batch_result.get("total_batches"),
            "avg_response_time_ms": round(batch_result.get("avg_response_time", 0), 1),
            "final_delay_ms": round(batch_result.get("final_delay", DYNAMIC_DELAY)),
        },
        "comparison": {
            "speedup_factor": round(batch_result["rate"] / single_result["rate"], 2) if single_result["rate"] > 0 else float('inf'),
            "http_requests_single": single_result["total"],
            "http_requests_batch": batch_result.get("total_batches", 0),
            "request_reduction_factor": round(single_result["total"] / batch_result.get("total_batches", 1), 1) if batch_result.get("total_batches", 0) > 0 else 0,
        },
    }

    report_path = os.path.join(os.path.dirname(__file__), "perf_test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  [完成] 报告已保存到: {report_path}", COLORS["GREEN"])

    return report


if __name__ == "__main__":
    run_test()
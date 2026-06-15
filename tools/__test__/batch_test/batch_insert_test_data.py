#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量插入测试数据脚本
用于 SmartTable 平台性能测试
支持自动创建 Base、Table、字段，以及批量插入记录
"""

import requests
import json
import random
import string
import uuid
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class SmartTableDataGenerator:
    """SmartTable 测试数据生成器"""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        table_id: str = "",
        auth_token: str = "",
        batch_size: int = 1000,
    ):
        """
        初始化数据生成器

        Args:
            base_url: API 基础地址（后端地址，不含 /api 前缀）
            table_id: 目标表格 ID
            auth_token: 认证 token
            batch_size: 每批插入的记录数（最大 1000）
        """
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api"
        self.table_id = table_id
        self.auth_token = auth_token
        self.batch_size = min(batch_size, 1000)  # API 限制最大 1000

        # 字段配置（创建字段后自动填充）
        self.field_mapping = {}

        # 随机数据池
        self.task_names = [
            "完成周报", "阅读技术文章", "健身锻炼", "购买生活用品", "准备会议材料",
            "学习新框架", "代码审查", "项目评审", "客户沟通", "文档编写",
            "数据分析", "系统优化", "Bug修复", "功能开发", "需求分析",
            "架构设计", "性能测试", "安全审计", "数据库优化", "接口开发",
            "移动端适配", "前端优化", "后端重构", "部署上线", "运维监控"
        ]
        self.users = ["j83fh0ues", "gidza6m7q", "z01omdn5o", "x8etxkuj6", "eokp36qej"]
        self.teams = ["b3lh6gh0v", "sfz1lcuvz", "dz9o3exmu", "k4pd2mtn8", "w7qf5hrz9"]
        self.priorities = [1, 2, 3, 4, 5]

        # 公共请求头
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json, text/plain, */*",
        }

        # 记录计数器（用于生成顺序号）
        self.record_counter = 0

    def _request(self, method: str, path: str, data: dict = None, max_retries: int = 3) -> Optional[dict]:
        """发送 HTTP 请求的通用方法"""
        url = f"{self.api_base}{path}"
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method, url, headers=self.headers, json=data, timeout=30
                )
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    print(f"  ✗ 请求失败 [{method} {path}]: 状态码 {response.status_code}")
                    print(f"    响应: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        print(f"    重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(1)
                    else:
                        return None
            except Exception as e:
                print(f"  ✗ 请求异常 [{method} {path}]: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"    重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(1)
                else:
                    return None
        return None

    # ==================== 自动创建资源 ====================

    def create_base(self, name: str = "性能测试数据集", description: str = "用于批量性能测试的 Base") -> Optional[str]:
        """创建 Base，返回 base_id"""
        print(f"创建 Base: {name}")
        result = self._request("POST", "/bases", {
            "name": name,
            "description": description,
            "icon": "folder",
            "color": "#6366f1",
        })
        if result:
            base_id = result.get("data", {}).get("id")
            print(f"  ✓ Base 创建成功: {base_id}")
            return base_id
        else:
            print("  ✗ Base 创建失败")
            return None

    def create_table(self, base_id: str, name: str = "批量测试任务表",
                     description: str = "批量性能测试任务表") -> Optional[str]:
        """在 Base 中创建 Table，返回 table_id（不创建默认字段）"""
        print(f"创建 Table: {name}")
        result = self._request("POST", f"/bases/{base_id}/tables", {
            "name": name,
            "description": description,
            "create_default_fields": False,
        })
        if result:
            table_id = result.get("data", {}).get("id")
            print(f"  ✓ Table 创建成功: {table_id}")
            return table_id
        else:
            print("  ✗ Table 创建失败")
            return None

    def _create_field(self, table_id: str, name: str, field_type: str,
                      options: dict = None) -> Optional[str]:
        """创建单个字段，返回 field_id"""
        data = {"name": name, "type": field_type}
        if options:
            data["options"] = options
        result = self._request("POST", f"/tables/{table_id}/fields", data)
        if result:
            field_id = result.get("data", {}).get("id")
            print(f"  ✓ 字段创建成功: {name} ({field_type}) -> {field_id}")
            return field_id
        else:
            print(f"  ✗ 字段创建失败: {name} ({field_type})")
            return None

    def create_fields(self, table_id: str, field_config: str = "default") -> Dict[str, str]:
        """
        创建预设字段，返回 field_id 映射字典
        映射: { field_id: field_type, ... }
        
        Args:
            table_id: 表格ID
            field_config: 字段配置类型，可选值:
                - "default": 默认配置（任务名称、负责人、创建人、截止日期、所属团队、优先级）
                - "simple": 简单配置（2文本+2数字+2日期）
        """
        print("创建字段...")
        mapping = {}

        if field_config == "simple":
            # 简单配置：2个文本 + 2个数字 + 2个日期
            text1_field = self._create_field(table_id, "文本1", "single_line_text")
            text2_field = self._create_field(table_id, "文本2", "single_line_text")
            num1_field = self._create_field(table_id, "数字1", "number", {"min": 1, "max": 1000, "precision": 0})
            num2_field = self._create_field(table_id, "数字2", "number", {"min": 0, "max": 100, "precision": 2})
            date1_field = self._create_field(table_id, "日期1", "date")
            date2_field = self._create_field(table_id, "日期2", "date")

            if text1_field:
                mapping[text1_field] = "text"
            if text2_field:
                mapping[text2_field] = "text"
            if num1_field:
                mapping[num1_field] = "number"
            if num2_field:
                mapping[num2_field] = "number"
            if date1_field:
                mapping[date1_field] = "date"
            if date2_field:
                mapping[date2_field] = "date"

        else:
            # 默认配置
            task_field = self._create_field(table_id, "任务名称", "single_line_text")
            assignee_field = self._create_field(table_id, "负责人", "single_line_text")
            creator_field = self._create_field(table_id, "创建人", "single_line_text")
            date_field = self._create_field(table_id, "截止日期", "date")
            team_field = self._create_field(table_id, "所属团队", "multi_select", {
                "choices": [
                    {"value": t, "color": random.choice(["blue", "green", "yellow", "red", "purple"])}
                    for t in self.teams
                ]
            })
            priority_field = self._create_field(table_id, "优先级", "number", {
                "min": 1, "max": 5, "precision": 0
            })

            if task_field:
                mapping[task_field] = "task_name"
            if assignee_field:
                mapping[assignee_field] = "assignee"
            if creator_field:
                mapping[creator_field] = "creator"
            if date_field:
                mapping[date_field] = "date"
            if team_field:
                mapping[team_field] = "team"
            if priority_field:
                mapping[priority_field] = "priority"

        self.field_mapping = mapping
        return mapping

    def auto_setup(self, base_name: str = "性能测试数据集",
                   table_name: str = "批量测试任务表",
                   field_config: str = "default") -> bool:
        """
        自动创建 Base -> Table -> Fields
        返回是否全部创建成功
        
        Args:
            base_name: Base名称
            table_name: 表格名称
            field_config: 字段配置类型 ("default" 或 "simple")
        """
        print("\n" + "=" * 60)
        print("开始自动创建资源...")
        print("=" * 60)

        base_id = self.create_base(base_name)
        if not base_id:
            return False

        table_id = self.create_table(base_id, table_name)
        if not table_id:
            return False
        self.table_id = table_id

        mapping = self.create_fields(table_id, field_config)
        if not mapping:
            return False

        print("=" * 60)
        print("资源创建完成！")
        print(f"  Base ID:  {base_id}")
        print(f"  Table ID: {table_id}")
        print(f"  字段映射: {json.dumps(mapping, indent=2)}")
        print("=" * 60)
        return True

    # ==================== 数据生成 ====================

    def _reset_counters(self):
        """重置计数器（每批次开始时调用）"""
        self.text_field_index = 0
        self.number_field_index = 0

    def _generate_text(self, min_len: int = 5, max_len: int = 20, record_num: int = None) -> str:
        """生成随机文本，可选在开头添加顺序号"""
        length = random.randint(min_len, max_len)
        random_part = "".join(random.choices(string.ascii_letters + string.digits, k=length))
        if record_num is not None:
            # 在开头添加顺序号，格式: "1_xxxx"
            return f"{record_num}_{random_part}"
        return random_part

    def _generate_number(self, min_val: int = 1, max_val: int = 100, record_num: int = None) -> float:
        """生成数字，支持顺序号+随机小数位"""
        if record_num is not None:
            # 顺序号 + 随机小数位（0.1-0.9）
            decimal = round(random.uniform(0.1, 0.9), 1)
            return round(record_num + decimal, 1)
        return random.randint(min_val, max_val)

    def _generate_date(self, days_range: int = 30) -> str:
        """生成随机日期时间"""
        base_date = datetime.now()
        random_days = random.randint(-days_range, days_range)
        random_seconds = random.randint(0, 86400)
        date = base_date + timedelta(days=random_days, seconds=random_seconds)
        return date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _generate_select(self, options: List[str]) -> List[str]:
        """生成选择项（多选）"""
        return [random.choice(options)]

    def _generate_single_text(self, record_num: int = None) -> str:
        """从预设任务名中选择，可选添加顺序号前缀"""
        task = random.choice(self.task_names)
        if record_num is not None:
            return f"{record_num}_{task}"
        return task

    def _generate_single_user(self) -> str:
        """从预设用户中选择"""
        return random.choice(self.users)

    def _generate_priority(self) -> int:
        """生成优先级"""
        return random.choice(self.priorities)

    def generate_record_values(self, field_mapping: Dict[str, str] = None, record_num: int = None) -> Dict[str, Any]:
        """
        生成单条记录的字段值

        Args:
            field_mapping: 字段类型映射，如 {"field_uuid": "task_name", ...}
            record_num: 记录序号（用于生成顺序号数据）

        Returns:
            记录值字典
        """
        values = {}

        # 按字段类型分组，用于生成顺序号
        text_fields = []
        number_fields = []
        other_fields = []

        mapping_to_use = field_mapping if field_mapping else self.field_mapping
        
        for field_id, ftype in mapping_to_use.items():
            if ftype == "text":
                text_fields.append((field_id, ftype))
            elif ftype == "number":
                number_fields.append((field_id, ftype))
            else:
                other_fields.append((field_id, ftype))

        # 生成文本字段（带顺序号）
        for i, (field_id, ftype) in enumerate(text_fields):
            if record_num is not None:
                # 每个文本字段用不同的序号后缀
                values[field_id] = self._generate_text(record_num=record_num + i * 100000)
            else:
                values[field_id] = self._generate_text()

        # 生成数字字段（顺序号+随机小数）
        for i, (field_id, ftype) in enumerate(number_fields):
            if record_num is not None:
                # 每个数字字段用不同的序号后缀
                values[field_id] = self._generate_number(record_num=record_num + i * 100000)
            else:
                values[field_id] = self._generate_number()

        # 生成其他类型字段
        for field_id, ftype in other_fields:
            if ftype == "task_name":
                values[field_id] = self._generate_single_text(record_num)
            elif ftype == "assignee":
                values[field_id] = self._generate_single_user()
            elif ftype == "creator":
                values[field_id] = self._generate_single_user()
            elif ftype == "date":
                values[field_id] = self._generate_date()
            elif ftype == "team":
                values[field_id] = self._generate_select(self.teams)
            elif ftype == "priority":
                values[field_id] = self._generate_priority()

        return values

    def generate_batch_records(
        self,
        count: int,
        field_mapping: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        生成批量记录数据

        Args:
            count: 记录数量
            field_mapping: 字段类型映射

        Returns:
            记录列表
        """
        records = []
        for i in range(count):
            # 使用全局计数器生成唯一序号
            self.record_counter += 1
            records.append({
                "values": self.generate_record_values(field_mapping, self.record_counter)
            })
        return records

    def insert_batch(self, records: List[Dict[str, Any]], max_retries: int = 3) -> bool:
        """
        批量插入记录

        Args:
            records: 记录列表
            max_retries: 最大重试次数

        Returns:
            是否成功
        """
        url = f"{self.api_base}/tables/{self.table_id}/records/batch"
        data = {"records": records}

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=self.headers, json=data, timeout=300)
                if response.status_code in [200, 201]:
                    result = response.json()
                    created_count = result.get("data", {}).get("created_count", len(records))
                    print(f"  ✓ 成功插入 {created_count} 条记录")
                    return True
                else:
                    print(f"  ✗ 插入失败，状态码: {response.status_code}")
                    print(f"    响应: {response.text[:300]}")
                    if attempt < max_retries - 1:
                        print(f"    重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        return False
            except Exception as e:
                print(f"  ✗ 请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"    重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    return False
        return False

    def run(
        self,
        total_count: int,
        field_mapping: Dict[str, str] = None,
        delay_seconds: float = 0.5
    ) -> None:
        """
        执行批量插入

        Args:
            total_count: 总记录数
            field_mapping: 字段类型映射
            delay_seconds: 批次间延迟（秒）
        """
        if not self.table_id:
            print("错误: 未指定 table_id，无法插入数据")
            return

        # 如果没有提供 field_mapping，使用自动创建的字段映射
        actual_mapping = field_mapping or self.field_mapping

        print(f"\n开始批量插入数据...")
        print(f"目标表格: {self.table_id}")
        print(f"目标总数: {total_count} 条")
        print(f"每批数量: {self.batch_size} 条")
        print(f"预计批次: {(total_count + self.batch_size - 1) // self.batch_size}")
        print("-" * 60)

        start_time = time.time()
        success_count = 0
        failed_batches = 0

        remaining = total_count
        batch_num = 1

        while remaining > 0:
            batch_count = min(remaining, self.batch_size)
            print(f"\n批次 {batch_num}: 准备插入 {batch_count} 条记录...")

            records = self.generate_batch_records(batch_count, actual_mapping)

            if self.insert_batch(records):
                success_count += batch_count
            else:
                failed_batches += 1
                if failed_batches >= 3:
                    print("连续失败次数过多，停止插入")
                    break

            remaining -= batch_count
            batch_num += 1

            if remaining > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)

        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"插入完成!")
        print(f"成功: {success_count} 条")
        print(f"失败: {total_count - success_count} 条")
        print(f"耗时: {elapsed_time:.2f} 秒")
        print(f"平均速度: {success_count / elapsed_time:.2f} 条/秒")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="SmartTable 批量插入测试数据脚本")
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="API 基础地址 (默认: http://localhost:5000)"
    )
    parser.add_argument(
        "--table-id",
        default="",
        help="目标表格 ID（使用 --auto 时自动创建，无需指定）"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="认证 Token (Bearer token)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="要插入的总记录数 (默认: 100000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="每批插入记录数 (最大 1000, 默认: 1000)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="批次间延迟秒数 (默认: 0.5)"
    )
    parser.add_argument(
        "--field-config",
        type=str,
        help="字段配置 JSON 文件路径（可选，与 --auto 互斥）"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动创建 Base、Table 和字段，无需提前准备表格"
    )
    parser.add_argument(
        "--base-name",
        default="性能测试数据集",
        help="自动创建的 Base 名称（与 --auto 配合使用）"
    )
    parser.add_argument(
        "--table-name",
        default="批量测试任务表",
        help="自动创建的 Table 名称（与 --auto 配合使用）"
    )
    parser.add_argument(
        "--field-type",
        default="default",
        choices=["default", "simple"],
        help="字段配置类型（与 --auto 配合使用）: default-默认配置, simple-2文本+2数字+2日期"
    )

    args = parser.parse_args()

    # 校验参数
    if not args.auto and not args.table_id:
        parser.error("请指定 --table-id，或使用 --auto 自动创建表格")
    if args.auto and args.field_config:
        parser.error("--auto 和 --field-config 不能同时使用")

    # 加载字段配置（仅非 auto 模式使用）
    field_mapping = None
    if args.field_config:
        try:
            with open(args.field_config, "r", encoding="utf-8") as f:
                field_mapping = json.load(f)
            print(f"已加载字段配置: {args.field_config}")
        except Exception as e:
            print(f"警告: 无法加载字段配置文件: {e}")

    generator = SmartTableDataGenerator(
        base_url=args.url,
        table_id=args.table_id,
        auth_token=args.token,
        batch_size=args.batch_size
    )

    # 自动创建资源
    if args.auto:
        if not generator.auto_setup(
            base_name=args.base_name,
            table_name=args.table_name,
            field_config=args.field_type
        ):
            print("自动创建资源失败，脚本终止")
            return

    generator.run(
        total_count=args.count,
        field_mapping=field_mapping,
        delay_seconds=args.delay
    )


if __name__ == "__main__":
    main()
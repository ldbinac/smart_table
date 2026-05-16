#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量插入测试数据脚本
用于 SmartTable 平台性能测试
"""

import requests
import json
import random
import string
import uuid
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any


class SmartTableDataGenerator:
    """SmartTable 测试数据生成器"""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        table_id: str = "",
        auth_token: str = "",
        batch_size: int = 1000,
    ):
        """
        初始化数据生成器

        Args:
            base_url: API 基础地址
            table_id: 目标表格 ID
            auth_token: 认证 token
            batch_size: 每批插入的记录数（最大 1000）
        """
        self.base_url = base_url.rstrip("/")
        self.table_id = table_id
        self.auth_token = auth_token
        self.batch_size = min(batch_size, 1000)  # API 限制最大 1000

        # 预设的字段配置（可根据实际表格调整）
        self.field_configs = {}

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

    def _generate_text(self, min_len: int = 5, max_len: int = 20) -> str:
        """生成随机文本"""
        length = random.randint(min_len, max_len)
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def _generate_number(self, min_val: int = 1, max_val: int = 100) -> int:
        """生成随机数字"""
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

    def _generate_single_text(self) -> str:
        """从预设任务名中选择"""
        return random.choice(self.task_names)

    def _generate_single_user(self) -> str:
        """从预设用户中选择"""
        return random.choice(self.users)

    def _generate_priority(self) -> int:
        """生成优先级"""
        return random.choice(self.priorities)

    def generate_record_values(self, field_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """
        生成单条记录的字段值

        Args:
            field_mapping: 字段类型映射，如 {"field_uuid": "task_name", ...}

        Returns:
            记录值字典
        """
        values = {}

        if field_mapping:
            for field_id, field_type in field_mapping.items():
                if field_type == "task_name":
                    values[field_id] = self._generate_single_text()
                elif field_type == "user":
                    values[field_id] = self._generate_single_user()
                elif field_type == "date":
                    values[field_id] = self._generate_date()
                elif field_type == "team":
                    values[field_id] = self._generate_select(self.teams)
                elif field_type == "priority":
                    values[field_id] = self._generate_priority()
                elif field_type == "text":
                    values[field_id] = self._generate_text()
        else:
            values = {
                "d696b7eb-d374-4373-bc43-7020a89b7801": self._generate_single_text(),
                "7dff744b-d472-4af1-8fd8-8020a6b5e363": self._generate_single_user(),
                "f913338a-3b38-4028-8ad1-327acf2b91cd": self._generate_single_user(),
                "2e5ddc17-096e-4344-8383-e5f497c47f1a": self._generate_date(),
                "e3c44e48-6fe8-4620-bf4f-759f57869e28": self._generate_select(self.teams),
                "3df39e49-c204-47b7-9cab-0e94c0e49ded": self._generate_priority(),
            }

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
        for _ in range(count):
            records.append({
                "values": self.generate_record_values(field_mapping)
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
        url = f"{self.base_url}/api/tables/{self.table_id}/records/batch"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json, text/plain, */*",
        }
        data = {"records": records}

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=300)
                if response.status_code in [200, 201]:
                    result = response.json()
                    created_count = result.get("data", {}).get("created_count", len(records))
                    print(f"✓ 成功插入 {created_count} 条记录")
                    return True
                else:
                    print(f"✗ 插入失败，状态码: {response.status_code}")
                    print(f"  响应: {response.text}")
                    if attempt < max_retries - 1:
                        print(f"  重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        return False
            except Exception as e:
                print(f"✗ 请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"  重试 ({attempt + 1}/{max_retries})...")
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
        print(f"开始批量插入数据...")
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

            records = self.generate_batch_records(batch_count, field_mapping)

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


def main():
    parser = argparse.ArgumentParser(description="SmartTable 批量插入测试数据脚本")
    parser.add_argument(
        "--url",
        default="http://localhost:3000",
        help="API 基础地址 (默认: http://localhost:3000)"
    )
    parser.add_argument(
        "--table-id",
        required=True,
        help="目标表格 ID"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="认证 Token (Bearer token)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100000,
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
        help="字段配置 JSON 文件路径（可选）"
    )

    args = parser.parse_args()

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

    generator.run(
        total_count=args.count,
        field_mapping=field_mapping,
        delay_seconds=args.delay
    )


if __name__ == "__main__":
    main()

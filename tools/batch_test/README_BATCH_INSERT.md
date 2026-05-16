# SmartTable 批量插入测试数据脚本

## 简介

这是一个用于向 SmartTable 平台批量插入测试数据的 Python 脚本，方便进行性能测试和压力测试。

## 功能特点

- 支持批量插入 10万、100万 甚至更多条测试数据
- 自动分批处理（每批最多 1000 条，符合 API 限制）
- 可配置字段映射，灵活生成不同类型的数据
- 显示插入进度和统计信息
- 支持批次间延迟，避免触发限流

## 前置要求

- Python 3.7+
- `requests` 库

## 安装依赖

```bash
pip install requests
```

## 使用方法

### 基本用法

```bash
cd tools/batch_test
python batch_insert_test_data.py \
  --table-id "你的表格ID" \
  --token "你的认证Token" \
  --count 100000
```

### 完整参数示例

```bash
python batch_insert_test_data.py \
  --url "http://localhost:3000" \
  --table-id "44e3457e-57e4-4929-a8f8-18a3c8908bb4" \
  --token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  --count 100000 \
  --batch-size 1000 \
  --delay 0.5 \
  --field-config field_config_example.json
```

## 参数说明

| 参数 | 说明 | 默认值 | 是否必需 |
|------|------|--------|----------|
| `--url` | API 基础地址 | http://localhost:3000 | 否 |
| `--table-id` | 目标表格 ID | - | 是 |
| `--token` | 认证 Token（Bearer Token） | - | 是 |
| `--count` | 要插入的总记录数 | 100000 | 否 |
| `--batch-size` | 每批插入记录数（最大 1000） | 1000 | 否 |
| `--delay` | 批次间延迟秒数 | 0.5 | 否 |
| `--field-config` | 字段配置 JSON 文件路径 | - | 否 |

## 如何获取必要参数

### 1. 获取 Table ID

在浏览器中打开你的表格，URL 中可以看到表格 ID：
```
http://localhost:3000/base/xxx/table/44e3457e-57e4-4929-a8f8-18a3c8908bb4
```

### 2. 获取 Auth Token

1. 打开浏览器开发者工具（F12）
2. 切换到 Network（网络）标签
3. 在 SmartTable 中进行任意操作
4. 找到任意 API 请求，在 Headers 中找到 `Authorization`
5. 复制 Bearer 后面的 token 部分

### 3. 获取字段 ID

1. 在浏览器开发者工具中，查看表格数据的 API 响应
2. 或使用浏览器的 Elements 面板查看字段元素
3. 或者在批量插入请求中查看示例数据的字段 ID

## 字段配置

你可以通过 JSON 文件配置字段映射，支持的字段类型：

- `task_name`: 任务名称（从预设列表随机选择）
- `user`: 用户 ID（从预设列表随机选择）
- `date`: 日期时间
- `team`: 团队（多选）
- `priority`: 优先级（数字 1-5）
- `text`: 随机文本

### 配置文件示例

```json
{
  "你的字段ID1": "task_name",
  "你的字段ID2": "user",
  "你的字段ID3": "date",
  "你的字段ID4": "team",
  "你的字段ID5": "priority"
}
```

## 注意事项

1. **API 限制**: 单次批量最多 1000 条记录，脚本会自动处理分批
2. **限流保护**: 建议设置适当的延迟时间，避免触发 API 限流
3. **数据格式**: 请确保字段类型与表格定义匹配
4. **认证**: Token 有过期时间，过期后需要重新获取

## 常见问题

### Q: 如何插入 100 万条数据？

A: 只需将 `--count` 参数设置为 1000000：
```bash
python batch_insert_test_data.py --table-id "xxx" --token "xxx" --count 1000000
```

### Q: 插入速度慢怎么办？

A: 可以尝试：
- 减小 `--delay` 参数（如 0.1 或 0）
- 确保网络连接良好
- 在服务端本地运行脚本

### Q: 如何自定义数据生成逻辑？

A: 可以修改 `SmartTableDataGenerator` 类中的 `_generate_*` 方法来定制数据生成规则。

## 输出示例

```
开始批量插入数据...
目标总数: 100000 条
每批数量: 1000 条
预计批次: 100
------------------------------------------------------------

批次 1: 准备插入 1000 条记录...
✓ 成功插入 1000 条记录

批次 2: 准备插入 1000 条记录...
✓ 成功插入 1000 条记录

...

============================================================
插入完成!
成功: 100000 条
失败: 0 条
耗时: 125.68 秒
平均速度: 795.68 条/秒
```

# 工作流循环体功能指南

---

## 第一章：循环体概述与基本概念

### 1.1 什么是循环节点

循环节点（Loop Node）是工作流系统中用于批量处理数据的控制节点。它能够从一个数据源中获取数组数据，然后对数组中的每一项依次执行一组子节点（即循环体），从而实现批量通知、批量归档、批量调用外部接口等自动化场景。

循环节点在工作流画布中以容器形式呈现，其内部包含的子节点即为每次迭代时执行的循环体节点链。

### 1.2 循环节点与循环体节点的关系

循环节点是一个容器型节点，其核心结构如下：

- **循环节点本身**：负责数据源解析、迭代控制、错误处理和循环上下文管理。
- **循环体节点（loop_body_nodes）**：嵌套在循环节点内部的子节点链，每次迭代时按顺序依次执行。

两者是父子关系。循环节点通过 `config.loop_body_nodes` 字段持有循环体子节点列表，子节点通过 `order` 字段排序，并通过 `next_nodes` 字段形成执行链。

### 1.3 支持的循环体节点类型

循环体内允许添加的节点类型如下（不包含条件分支节点 `condition`）：

| 节点类型 | 中文名称 | 说明 |
|----------|----------|------|
| `webhook` | Webhook | 调用外部 HTTP 接口 |
| `send_email` | 发送邮件 | 向指定收件人发送邮件 |
| `update_record` | 更新记录 | 更新数据表中的记录 |
| `create_record` | 创建记录 | 在目标数据表中创建新记录 |
| `find_records` | 查找记录 | 查询数据表中的记录 |
| `loop` | 循环 | 嵌套循环（支持最多 3 层嵌套） |

> **注意**：`condition`（条件分支）节点不允许出现在循环体内。如果尝试添加，系统将在工作流创建/更新时拒绝并返回校验错误。

### 1.4 系统约束

| 约束项 | 限制值 | 说明 |
|--------|--------|------|
| 单工作流最大循环节点数 | 5 | 包含嵌套循环体内的所有循环节点 |
| 最大嵌套深度 | 3 | 循环节点最多嵌套 3 层 |
| 循环执行模式 | 顺序执行（sequential） | 当前仅支持顺序模式，不支持并行 |

---

## 第二章：循环体的详细使用方式

### 2.1 语法结构

#### 2.1.1 模板变量语法

循环体节点在配置中可以使用模板变量来引用循环上下文数据。模板变量使用双花括号语法：

```
{{变量路径}}
```

例如：

```
{{loop.current_data}}
{{loop.current_data.field_abc123}}
{{loop.round}}
```

#### 2.1.2 点号路径解析

模板变量的路径采用点号分隔，系统通过 `_resolve_path()` 方法逐层解析：

1. 以点号 `.` 分割路径为多个部分
2. 从渲染上下文字典中逐层取值
3. 若中间层为 `dict`，使用 `.get(part)` 取值
4. 若中间层为 `list`/`tuple` 且路径部分为数字，按索引取值
5. 任意一层解析为 `None` 时，整体返回 `None`

示例：

```
{{loop.current_data.field_id}}  → context["loop"]["current_data"]["field_id"]
{{record.name}}                 → context["record"]["name"]
{{trigger.record.status}}       → context["trigger"]["record"]["status"]
```

#### 2.1.3 模板渲染方法

`render_template()` 方法的渲染规则：

- 若输入值非字符串，原样返回
- 若整个字符串恰好是一个 `{{...}}}` 表达式（full match），直接返回解析后的原始值（保留类型）
- 若字符串中包含多个或混合了 `{{...}}` 与普通文本，逐个替换为字符串拼接结果（`None` 转为空串）

### 2.2 数据源配置

循环节点通过 `data_source` 配置项决定待迭代的数据来源。支持以下四种类型：

#### 2.2.1 find_records_all

遍历查找记录节点返回的所有记录。每次迭代的 `current_data` 为完整的记录字典（包含所有字段值）。

```json
{
  "type": "find_records_all",
  "node_id": "<find_records 节点 ID>"
}
```

- 数据来源：指定 `find_records` 节点的输出结果中的 `records` 数组
- `current_data` 类型：`dict`（完整记录，键为字段 ID，值为字段值）
- 支持字段下钻：是（可通过 `{{loop.current_data.field_id}}` 访问具体字段）

#### 2.2.2 find_records_column

从查找记录的结果中提取指定字段的值并扁平化。适用于人员、群组、附件、关联等字段类型，自动对具有 `id` 属性的列表项去重。

```json
{
  "type": "find_records_column",
  "node_id": "<find_records 节点 ID>",
  "field_id": "<字段 ID>"
}
```

- 数据来源：从 `find_records` 节点的记录列表中，提取每条记录的指定字段值
- 扁平化逻辑：若字段值为列表，逐项展开；对包含 `id` 的字典项自动去重
- `current_data` 类型：取决于字段类型（如人员字段为 `{id, name, email}` 字典）
- 支持字段下钻：否（数据已是单值）

#### 2.2.3 trigger_field

从触发记录中获取指定字段的值。若字段值为列表直接返回，否则包装为单元素列表。

```json
{
  "type": "trigger_field",
  "field_id": "<字段 ID>"
}
```

- 数据来源：触发事件中的 `record` 对象的指定字段值
- 列表字段（如多人协作）：直接返回列表
- 单值字段：包装为 `[value]` 单元素列表
- 支持字段下钻：否

#### 2.2.4 webhook_array

从 Webhook 节点的返回结果中读取 JSON 数组。

```json
{
  "type": "webhook_array",
  "node_id": "<webhook 节点 ID>"
}
```

- 数据来源：上下文中 `{node_id}_result.json.array` 路径
- `current_data` 类型：取决于 Webhook 返回的数据结构
- 支持字段下钻：否（数据结构未知）

### 2.3 执行流程

循环节点的完整执行流程如下：

```
1. 循环节点开始执行
   │
2. 解析 data_source，获取 data_array
   │
3. 若 data_array 为空
   ├─ empty_result_action = "skip" → 记录日志，返回 {next_nodes}，继续主链
   └─ empty_result_action = "error" → 抛出异常
   │
4. 计算 total = min(len(data_array), max_iterations)
   │
5. 创建执行日志（status: running）
   │
6. 依次迭代 index = 0, 1, ..., total-1
   │
   ├─ a. 保存外层 loop_context（用于嵌套循环恢复）
   ├─ b. 设置当前 loop_context = {
   │       current_data: data_array[index],
   │       index: index,
   │       round: index + 1,
   │       total: total
   │    }，写入 instance.context
   ├─ c. 执行循环体节点链
   │   └─ 若某节点抛出异常：
   │       ├─ error_handling = "skip" → 记录失败，继续下一次迭代
   │       └─ error_handling = "terminate" → 标记提前终止，向上抛出异常
   └─ d. 恢复外层 loop_context（finally 保证执行）
   │
7. 更新执行日志（status: success/error，记录统计信息）
   │
8. 返回 {next_nodes: node.next_nodes}，继续主链
```

执行完成后的输出结果包含以下统计字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_iterations` | int | 实际执行的总迭代次数 |
| `success_count` | int | 成功次数 |
| `failure_count` | int | 失败次数 |
| `early_terminated` | bool | 是否提前终止 |
| `skipped_reason` | string | 跳过原因（仅数据为空时存在，值为 `data_array_empty`） |

---

## 第三章：循环体的配置方式

### 3.1 基本配置

循环节点的完整配置参数如下：

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|----------|------|
| `data_source.type` | string | `"find_records_all"` | `find_records_all`, `find_records_column`, `trigger_field`, `webhook_array` | 数据源类型 |
| `data_source.node_id` | string | - | 引用节点的 UUID | 数据源引用的上游节点 ID（find_records_all / find_records_column / webhook_array 时必填） |
| `data_source.field_id` | string | - | 字段的 UUID | 提取的目标字段 ID（find_records_column 时必填） |
| `data_source.trigger_field_id` | string | - | 字段的 UUID | 触发记录的字段 ID（trigger_field 时使用，兼容 `field_id`） |
| `max_iterations` | number | `100` | 1 - 1000 | 单次执行最大迭代次数 |
| `error_handling` | string | `"skip"` | `skip`, `terminate` | 循环体执行出错时的处理方式 |
| `empty_result_action` | string | `"skip"` | `skip`, `error` | 数据数组为空时的处理方式 |
| `loop_body_nodes` | array | `[]` | - | 循环体子节点列表（不可为空） |
| `loop_mode` | string | `"sequential"` | `sequential` | 循环执行模式（当前仅支持顺序执行） |

#### 3.1.1 错误处理方式

- **`skip`（跳过当次继续）**：当某次迭代的循环体抛出异常时，跳过该次迭代的剩余节点，记录失败计数，继续执行下一次迭代。循环结束后正常返回主链。
- **`terminate`（终止流程）**：当某次迭代抛出异常时，标记 `early_terminated = True`，向上抛出异常，终止整个工作流实例。

#### 3.1.2 空结果处理

- **`skip`（跳过循环）**：数据数组为空时，记录诊断日志（含 `skipped_reason: "data_array_empty"`），返回 `{next_nodes}` 继续主链。
- **`error`（报错）**：数据数组为空时，抛出 `ValueError('循环数据源为空')`，终止工作流实例。

### 3.2 高级配置

#### 3.2.1 嵌套循环支持

循环体中可以嵌套另一个循环节点，形成多层循环结构。系统约束如下：

- **最大嵌套深度**：3 层（即最外层为第 1 层，最内层为第 3 层）
- 超过 3 层嵌套的配置在创建/更新工作流时将被拒绝，返回错误信息：`循环嵌套深度不能超过 3 层`

嵌套循环的上下文隔离机制：

- 进入内层循环前，保存外层 `loop_context` 到临时变量
- 设置内层 `loop_context` 后执行内层循环体
- 无论内层循环成功或失败，`finally` 块中恢复外层 `loop_context`

#### 3.2.2 循环节点数量限制

单个工作流中所有循环节点总数（含嵌套循环体内的）不超过 5 个。超过限制时，创建/更新工作流将返回错误信息：`单个工作流最多 5 个循环节点`。

#### 3.2.3 循环上下文结构

每次迭代时，系统在工作流实例上下文（`instance.context`）中设置 `loop_context` 字段，结构如下：

```json
{
  "current_data": "<当前迭代的数据项>",
  "index": 0,
  "round": 1,
  "total": 10
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `current_data` | Any | 当前迭代的数据项（类型取决于数据源） |
| `index` | int | 当前迭代的索引（从 0 开始） |
| `round` | int | 当前迭代的轮数（从 1 开始，即 `index + 1`） |
| `total` | int | 本次循环的总迭代次数 |

---

## 第四章：典型使用场景分析

### 4.1 批量通知

**场景**：查找状态为"进行中"的所有任务，提取负责人字段中的成员列表，逐个发送邮件通知。

**流程**：

```
触发器 → 查找记录（进行中任务） → 循环（find_records_column，负责人字段） → 发送邮件
```

**要点**：
- 数据源使用 `find_records_column`，指定人员类型字段
- `find_records_column` 会自动对人员列表去重，避免同一人收到多封邮件
- 邮件模板中使用 `{{loop.current_data.name}}` 和 `{{loop.current_data.email}}` 引用收件人信息

### 4.2 批量归档

**场景**：从需求进度表中查找所有"已上线"的需求，逐条复制到归档表中。

**流程**：

```
触发器 → 查找记录（已上线需求） → 循环（find_records_all） → 创建记录
```

**要点**：
- 数据源使用 `find_records_all`，每次迭代的 `current_data` 为完整记录字典
- 创建记录的字段映射使用 `{{loop.current_data.field_id}}` 逐字段引用源记录值

### 4.3 嵌套循环

**场景**：外层循环遍历在职员工，内层循环遍历该员工负责的任务，为每个员工-任务组合创建明细记录。

**流程**：

```
触发器
  → 查找记录（在职员工）
  → 外层循环（find_records_all，员工）
    → 查找记录（该员工的任务）
    → 内层循环（find_records_all，任务）
      → 创建记录
```

**要点**：
- 嵌套深度为 2，在限制范围内
- 内层循环体可通过 `{{loop.current_data}}` 访问内层数据，外层上下文在内层循环结束后自动恢复

### 4.4 批量 Webhook 调用

**场景**：查找符合条件的记录，逐条调用外部 API 进行数据同步。

**流程**：

```
触发器 → 查找记录 → 循环（find_records_all） → Webhook
```

**要点**：
- Webhook 的 Body 模板可使用 `{{loop.current_data}}`、`{{loop.round}}` 等变量
- 系统在构建 Webhook 事件数据时，自动将 `loop_context` 传入渲染上下文

---

## 第五章：详细案例说明

### 5.1 案例一：批量邮件通知

#### 场景描述

当任务表中新增记录时，查找所有状态为"进行中"的任务，提取这些任务的负责人字段中的成员，向每位唯一成员发送一封邮件提醒。

#### 配置代码

```json
{
  "name": "任务提醒工作流",
  "nodes_config": [
    {
      "node_type": "trigger",
      "name": "记录创建触发",
      "config": {},
      "order": 0
    },
    {
      "node_type": "find_records",
      "name": "查找进行中任务",
      "config": {
        "target_table_id": "tbl_tasks",
        "conditions": [
          {
            "field_id": "fld_status",
            "operator": "equals",
            "value": "进行中"
          }
        ],
        "conjunction": "and",
        "result_variable": "records"
      },
      "order": 1
    },
    {
      "node_type": "loop",
      "name": "按负责人循环",
      "config": {
        "loop_mode": "sequential",
        "data_source": {
          "type": "find_records_column",
          "node_id": "<find_records 节点 ID>",
          "field_id": "fld_member"
        },
        "max_iterations": 100,
        "error_handling": "skip",
        "empty_result_action": "skip",
        "loop_body_nodes": [
          {
            "id": "body-send-email-1",
            "node_type": "send_email",
            "name": "发送任务提醒",
            "config": {
              "to_email": "{{loop.current_data.email}}",
              "to_name": "{{loop.current_data.name}}",
              "template_key": "task_reminder",
              "template_data": {
                "user_name": "{{loop.current_data.name}}",
                "task_count": "{{loop.total}}"
              }
            },
            "order": 0,
            "next_nodes": []
          }
        ]
      },
      "order": 2,
      "next_nodes": []
    }
  ]
}
```

#### 执行流程

1. 触发器触发，工作流实例启动
2. `find_records` 节点执行，查询状态为"进行中"的记录，结果存入 `instance.context["records"]`
3. `loop` 节点执行：
   - 数据源类型为 `find_records_column`，从记录列表中提取 `fld_member` 字段值
   - 对人员列表自动去重（按 `id` 字段），得到 3 位唯一成员
   - `data_array = [{id:"u1", name:"张三", email:"zhang@example.com"}, {id:"u2", name:"李四", email:"li@example.com"}, {id:"u3", name:"王五", email:"wang@example.com"}]`
   - 依次迭代 3 次，每次设置 `loop_context` 并执行 `send_email` 节点
4. 循环结束，返回 `{next_nodes: []}`，工作流完成

#### 输出结果

执行日志记录：

```json
{
  "total_iterations": 3,
  "success_count": 3,
  "failure_count": 0,
  "early_terminated": false
}
```

邮件发送结果：张三、李四、王五各收到 1 封任务提醒邮件。

---

### 5.2 案例二：批量记录归档

#### 场景描述

从需求进度表中查找所有状态为"已上线"的需求记录，逐条复制到归档表中，映射需求名称、负责人和来源等字段。

#### 配置代码

```json
{
  "name": "需求归档工作流",
  "nodes_config": [
    {
      "node_type": "trigger",
      "name": "触发",
      "config": {},
      "order": 0
    },
    {
      "node_type": "find_records",
      "name": "查找已上线需求",
      "config": {
        "target_table_id": "tbl_progress",
        "conditions": [
          {
            "field_id": "fld_req_status",
            "operator": "equals",
            "value": "已上线"
          }
        ],
        "conjunction": "and",
        "result_variable": "records"
      },
      "order": 1
    },
    {
      "node_type": "loop",
      "name": "逐条归档",
      "config": {
        "loop_mode": "sequential",
        "data_source": {
          "type": "find_records_all",
          "node_id": "<find_records 节点 ID>"
        },
        "max_iterations": 100,
        "error_handling": "skip",
        "empty_result_action": "skip",
        "loop_body_nodes": [
          {
            "id": "body-create-1",
            "node_type": "create_record",
            "name": "创建归档记录",
            "config": {
              "target_table_id": "tbl_archive",
              "field_mappings": [
                {
                  "target_field_id": "fld_arc_name",
                  "source_field_id": "",
                  "value_template": "{{loop.current_data.fld_req_name}}"
                },
                {
                  "target_field_id": "fld_arc_owner",
                  "source_field_id": "",
                  "value_template": "{{loop.current_data.fld_req_owner}}"
                },
                {
                  "target_field_id": "fld_arc_source",
                  "source_field_id": "",
                  "value_template": "需求进度表"
                }
              ]
            },
            "order": 0,
            "next_nodes": []
          }
        ]
      },
      "order": 2,
      "next_nodes": []
    }
  ]
}
```

#### 执行流程

1. 触发器触发，工作流实例启动
2. `find_records` 节点执行，查询状态为"已上线"的 5 条需求记录
3. `loop` 节点执行：
   - 数据源类型为 `find_records_all`，直接使用记录数组
   - `data_array` 包含 5 条完整记录字典
   - 第 1 轮：`loop_context = {current_data: records[0], index: 0, round: 1, total: 5}`
     - 创建归档记录，名称取自 `{{loop.current_data.fld_req_name}}`，负责人取自 `{{loop.current_data.fld_req_owner}}`，来源固定为"需求进度表"
   - 第 2-5 轮：同上，逐条创建归档记录
4. 循环结束，共创建 5 条归档记录

#### 输出结果

执行日志记录：

```json
{
  "total_iterations": 5,
  "success_count": 5,
  "failure_count": 0,
  "early_terminated": false
}
```

归档表中新增 5 条记录，字段值与进度表中的需求一一对应。

---

### 5.3 案例三：循环体中的 Webhook 调用

#### 场景描述

查找待同步的记录，逐条调用外部 API 将数据推送至第三方系统。Webhook 的请求体需要包含当前记录数据以及循环轮次信息。

#### 配置代码

```json
{
  "name": "数据同步工作流",
  "nodes_config": [
    {
      "node_type": "trigger",
      "name": "触发",
      "config": {},
      "order": 0
    },
    {
      "node_type": "find_records",
      "name": "查找待同步记录",
      "config": {
        "target_table_id": "tbl_orders",
        "conditions": [
          {
            "field_id": "fld_sync_status",
            "operator": "equals",
            "value": "待同步"
          }
        ],
        "conjunction": "and",
        "result_variable": "records"
      },
      "order": 1
    },
    {
      "node_type": "loop",
      "name": "逐条推送",
      "config": {
        "loop_mode": "sequential",
        "data_source": {
          "type": "find_records_all",
          "node_id": "<find_records 节点 ID>"
        },
        "max_iterations": 50,
        "error_handling": "skip",
        "empty_result_action": "skip",
        "loop_body_nodes": [
          {
            "id": "body-webhook-1",
            "node_type": "webhook",
            "name": "推送至外部系统",
            "config": {
              "inline_webhook": {
                "url": "https://api.example.com/orders/sync",
                "method": "POST",
                "headers": [
                  {"key": "Content-Type", "value": "application/json"},
                  {"key": "X-Auth-Token", "value": "secret-token"}
                ],
                "body_template": "{\"order_id\": \"{{loop.current_data.fld_order_id}}\", \"amount\": {{loop.current_data.fld_amount}}, \"sync_round\": {{loop.round}}, \"sync_index\": {{loop.index}}, \"total_batches\": {{loop.total}}}"
              }
            },
            "order": 0,
            "next_nodes": []
          }
        ]
      },
      "order": 2,
      "next_nodes": []
    }
  ]
}
```

#### 执行流程

1. 触发器触发，工作流实例启动
2. `find_records` 节点执行，查找到 3 条待同步记录
3. `loop` 节点执行：
   - 数据源类型为 `find_records_all`，`data_array` 包含 3 条记录
   - 系统在构建 Webhook 事件数据时，自动将 `loop_context` 传入渲染上下文，确保 `{{loop.current_data}}` 等模板变量可用
   - 第 1 轮（`index=0, round=1`）：发送 POST 请求，请求体包含当前记录数据及轮次信息
   - 第 2 轮（`index=1, round=2`）：处理下一条记录
   - 第 3 轮（`index=2, round=3`）：处理最后一条记录
4. 循环结束，3 条记录均推送完成

#### 输出结果

第 1 轮 Webhook 请求体（模板渲染后）：

```json
{
  "order_id": "ORD-2026-001",
  "amount": 1500.00,
  "sync_round": 1,
  "sync_index": 0,
  "total_batches": 3
}
```

执行日志记录：

```json
{
  "total_iterations": 3,
  "success_count": 3,
  "failure_count": 0,
  "early_terminated": false
}
```

---

## 第六章：常见问题与解决方案

### 6.1 循环体未执行

**现象**：工作流执行到循环节点后，循环体子节点未执行，日志中 `total_iterations` 为 0。

**常见原因**：数据源类型配置错误。例如，期望遍历所有记录却使用了 `find_records_column` 类型，而该类型仅提取指定字段值。若字段值提取后为空（字段无数据或字段 ID 错误），`data_array` 将为空。

**解决方案**：

- 若需要遍历完整记录，将 `data_source.type` 改为 `find_records_all`
- 若使用 `find_records_column`，确认 `field_id` 正确且对应字段确实有值
- 检查诊断日志中的 `skipped_reason` 字段，确认是否为 `data_array_empty`

### 6.2 循环数据为空

**现象**：循环节点日志中 `output_result` 包含 `skipped_reason: "data_array_empty"`。

**常见原因**：

- 上游 `find_records` 节点未查到记录
- `data_source.node_id` 指向的节点 ID 不存在或不正确
- `data_source.field_id` 指向的字段在记录中不存在或值为空
- `trigger_field` 类型的触发记录字段值为空

**解决方案**：

- 检查上游 `find_records` 节点的过滤条件是否过于严格
- 确认 `node_id` 和 `field_id` 的正确性
- 若数据为空属于正常情况，将 `empty_result_action` 设为 `"skip"` 以跳过循环继续主链

### 6.3 模板变量未解析

**现象**：Webhook 请求体或创建记录的字段值中，`{{loop.current_data.xxx}}` 未被替换，保留了原始模板字符串。

**常见原因**：

- 当前节点不在循环体内（非循环节点的子节点），`loop_context` 不存在
- `loop_context` 未正确传递到渲染上下文中

**解决方案**：

- 确认使用模板变量的节点确实位于某个循环节点的 `loop_body_nodes` 中
- 在前端配置面板中，只有循环体内的节点会显示"插入循环变量"按钮（`LoopVarInserter` 组件），若未显示说明当前不在循环体内
- 检查 `instance.context` 中是否包含 `loop_context` 字段

### 6.4 嵌套循环上下文覆盖

**现象**：嵌套循环中，内层循环执行后，外层循环的模板变量解析为内层数据。

**常见原因**：此问题在当前实现中已通过 `finally` 块中的上下文恢复机制解决。

**机制说明**：

`_execute_loop_body()` 方法在进入循环体前保存外层 `loop_context`，在 `finally` 块中恢复：

```python
context = instance.context or {}
outer_loop_context = context.get('loop_context')  # 保存外层上下文

context['loop_context'] = { ... }  # 设置内层上下文

try:
    # 执行循环体
finally:
    context['loop_context'] = outer_loop_context  # 恢复外层上下文
```

若仍出现上下文覆盖，可能是异常被吞没导致 `finally` 未正确执行，需检查异常处理链路。

### 6.5 达到最大迭代次数

**现象**：实际数据量大于 `max_iterations`，部分数据未被处理。

**常见原因**：`max_iterations` 默认值为 100，若数据源返回的数组长度超过该值，循环将在达到上限后停止。

**解决方案**：

- 根据实际数据量调整 `max_iterations`（取值范围 1-1000）
- 注意：系统会将 `max_iterations` 限制在 `[1, 1000]` 范围内，超出范围自动截断

### 6.6 循环体节点类型不被允许

**现象**：创建或更新工作流时返回校验错误：`循环体不支持条件分支节点`。

**常见原因**：在 `loop_body_nodes` 中添加了 `condition` 类型的节点。

**解决方案**：

- 移除循环体中的 `condition` 节点
- 若需要条件判断逻辑，考虑在工作流主链中（循环体外）使用条件分支，或使用 Webhook 节点的条件回调机制

---

## 附录：循环体模板变量速查表

| 变量 | 类型 | 说明 | 适用数据源 |
|------|------|------|------------|
| `{{loop.current_data}}` | Any | 当前迭代的完整数据项 | 所有类型 |
| `{{loop.current_data.field_id}}` | Any | 当前记录的指定字段值（字段下钻） | 仅 `find_records_all` |
| `{{loop.index}}` | int | 当前迭代索引（从 0 开始） | 所有类型 |
| `{{loop.round}}` | int | 当前迭代轮数（从 1 开始） | 所有类型 |
| `{{loop.total}}` | int | 本次循环总迭代次数 | 所有类型 |
| `{{record}}` | dict | 触发记录的完整字段值 | 所有类型 |
| `{{record.field_id}}` | Any | 触发记录的指定字段值 | 所有类型 |
| `{{event}}` | dict | 触发事件数据 | 所有类型 |
| `{{workflow}}` | dict | 当前工作流信息 | 所有类型 |
| `{{instance}}` | dict | 当前工作流实例信息 | 所有类型 |

> **字段下钻说明**：`{{loop.current_data.field_id}}` 仅在数据源为 `find_records_all` 时可用，因为此时 `current_data` 为包含所有字段的完整记录字典。其他数据源类型（`find_records_column`、`trigger_field`、`webhook_array`）的 `current_data` 为单值，不支持下钻。前端 `LoopVarInserter` 组件会根据数据源类型自动控制字段下钻选项的显示。

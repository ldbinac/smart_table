# 工作流机制功能验证操作手册

本文档用于逐项验证 SmartTable 工作流（Workflow）机制的核心能力，覆盖待办审批、自动化任务、Webhook 通知、模板复用、权限控制与执行审计等场景。

## 目录

- [一、前置条件](#一前置条件)
- [二、工作流基础管理](#二工作流基础管理)
- [三、触发器配置验证](#三触发器配置验证)
- [四、待办审批系统](#四待办审批系统)
- [五、自动化任务引擎](#五自动化任务引擎)
- [六、Webhook 通知](#六webhook-通知)
- [七、工作流模板](#七工作流模板)
- [八、执行日志与审计](#八执行日志与审计)
- [九、权限控制](#九权限控制)
- [十、测试命令速查](#十测试命令速查)
- [十一、常见问题排查](#十一常见问题排查)
- [十二、验证完成 checklist](#十二验证完成-checklist)

## 一、前置条件

### 1.1 环境启动

| 步骤 | 命令 | 验证点 |
|------|------|--------|
| 启动后端 | `cd smarttable-backend && python run.py` 或等价启动命令 | 服务监听在配置端口（默认 5000） |
| 启动前端 | `cd smart-table && npm run dev` | 浏览器可访问 `http://localhost:5173` |
| 准备测试数据 | 登录并创建一个 Base，至少添加一张表和两个字段 | 表中存在可用于触发工作流的数据 |

### 1.2 测试用户准备

- **所有者 / 管理员（Owner / Admin）**：可创建、编辑、发布、删除工作流。
- **编辑者（Editor）**：可创建和编辑工作流，但受 Base 权限约束。
- **浏览者（Viewer）**：仅可查看，无法创建工作流或 Webhook。
- **非审批人**：无法处理不属于自己的审批任务。

### 1.3 术语说明

| 中文术语 | 英文术语 | 说明 |
|----------|----------|------|
| 工作流 | Workflow | 由触发器（Trigger）和若干节点（Node）组成的自动化流程 |
| 触发器 | Trigger | 定义工作流何时启动，例如记录创建、字段变更 |
| 节点 | Node | 工作流中的单个执行步骤，例如条件判断、审批、更新记录 |
| 工作流实例 | Workflow Instance | 工作流被触发后产生的一次执行记录 |
| 审批任务 | Approval Task | 审批节点分配给具体用户的待办事项 |
| Webhook | Webhook | 向外部系统发送 HTTP 通知的机制 |
| Base | Base | SmartTable 中的多维表格空间 |

## 二、工作流基础管理

### 2.1 工作流列表查看

- **前端路径**：`Base` → 左侧菜单「工作流」→ `/base/{base_id}/workflows`
- **预期结果**：
  - 页面加载后显示当前 Base 下的工作流列表。
  - 草稿状态显示「草稿」标签，已发布状态显示「已发布」标签。
- **后端验证**：
  ```bash
  curl -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/bases/{base_id}/workflows"
  ```
- **自动化测试**：
  ```bash
  cd smarttable-backend
  python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_get_workflows_list -v
  ```

### 2.2 创建工作流

- **前端操作**：在工作流页面点击「新建工作流」，填写名称、选择关联表、配置触发器。
- **预期结果**：
  - 创建成功后在列表中显示。
  - 默认状态为 `draft`。
- **后端验证**：
  ```bash
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"name":"测试工作流","table_id":"{table_id}","trigger_config":{"trigger_type":"record_created","filter_config":{}},"nodes_config":[{"node_type":"trigger","name":"记录创建","order":0}]}' \
    "http://localhost:5000/api/bases/{base_id}/workflows"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_create_workflow -v
  ```

### 2.3 编辑与发布工作流

- **前端操作**：点击工作流进入设计器，添加/删除/拖拽节点，配置节点参数，点击「保存」或「发布」。
- **预期结果**：
  - 保存后草稿内容更新。
  - 发布后工作流状态变为 `active`，触发器生效。
  - 已发布工作流不能继续编辑节点配置，需要先暂停或创建新版本。
- **后端验证**：
  ```bash
  # 发布
  curl -X POST -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflows/{workflow_id}/publish"

  # 暂停
  curl -X POST -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflows/{workflow_id}/pause"

  # 恢复
  curl -X POST -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflows/{workflow_id}/resume"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_update_workflow \
    tests/test_workflow_routes.py::TestWorkflowRoutes::test_publish_workflow \
    tests/test_workflow_routes.py::TestWorkflowRoutes::test_pause_and_resume_workflow -v
  ```

### 2.4 删除工作流

- **前端操作**：在工作流列表中点击「删除」。
- **预期结果**：工作流被软删除，列表中不再显示。
- **后端验证**：
  ```bash
  curl -X DELETE -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflows/{workflow_id}"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_delete_workflow -v
  ```

## 三、触发器配置验证

### 3.1 触发类型

| 触发类型 | 说明 | 验证方式 |
|----------|------|----------|
| `record_created` | 记录创建时触发 | 新增一条记录，观察实例是否生成 |
| `record_updated` | 记录更新时触发 | 修改记录字段，观察实例是否生成 |
| `field_changed` | 指定字段变更时触发 | 修改监听字段，观察实例是否生成 |
| `manual` | 手动触发 | 点击「手动触发」按钮 |

### 3.2 过滤条件

- **前端操作**：在触发器配置区域添加过滤条件，例如「状态 等于 待审批」。
- **预期结果**：
  - 满足条件的记录才触发工作流。
  - 不满足条件的记录不生成实例。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_service.py::TestMatchTriggers -v
  ```

## 四、待办审批系统

### 4.1 审批节点配置

- **前端操作**：在工作流设计器中添加「审批节点」，配置：
  - 审批人选择方式：固定用户 / 字段指定 / 角色。
  - 审批模式：或签（任意一人通过即可）/ 会签（所有人都需通过）/ 串行（按顺序审批）。
  - 超时时间与超时动作（可选）。
- **预期结果**：配置保存后，发布工作流，触发时生成对应审批任务。

### 4.2 审批任务处理

- **前端路径**：`Base` → 左侧菜单「审批中心」→ `/base/{base_id}/approvals`
- **预期结果**：
  - 审批人能看到自己的待办任务。
  - 点击任务可查看详情并执行「同意」「拒绝」「转交」。
  - 非审批人无法处理任务。
- **后端验证**：
  ```bash
  # 获取我的审批列表
  curl -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/bases/{base_id}/approvals?status=pending"

  # 同意
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"comment":"同意"}' \
    "http://localhost:5000/api/approvals/{task_id}/approve"

  # 拒绝
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"comment":"拒绝"}' \
    "http://localhost:5000/api/approvals/{task_id}/reject"

  # 转交
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"assignee_id":"{user_id}","comment":"转交给你"}' \
    "http://localhost:5000/api/approvals/{task_id}/transfer"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_approval_service.py -v
  python -m pytest tests/test_workflow_routes.py::TestApprovalRoutes -v
  ```

### 4.3 审批状态流转

| 场景 | 预期结果 |
|------|----------|
| 或签模式下任意审批人同意 | 任务通过，实例继续执行 |
| 会签模式下所有审批人同意 | 任务通过，实例继续执行 |
| 串行模式下前一审批人未处理 | 后续审批人看不到任务 |
| 任意审批人拒绝 | 实例状态变为 `rejected`，流程终止 |
| 超时未处理 | 按配置执行自动通过 / 自动拒绝 / 发送提醒 |

## 五、自动化任务引擎

### 5.1 条件节点

- **前端操作**：添加「条件节点」，设置字段判断条件（如「金额 > 1000」）。
- **预期结果**：满足条件走「是」分支，不满足走「否」分支。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_execution.py::TestExecuteConditionNode -v
  ```

### 5.2 更新记录节点

- **前端操作**：添加「更新记录」节点，配置字段映射（如将「审批状态」更新为「已通过」）。
- **预期结果**：审批通过后，自动更新触发记录的字段值。
- **验证重点**：更新字段不应再次触发工作流，避免死循环。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_execution.py::TestExecuteUpdateRecord -v
  ```

### 5.3 创建记录节点

- **前端操作**：添加「创建记录」节点，选择目标表并配置字段映射。
- **预期结果**：工作流执行到该节点时，在目标表创建新记录。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_execution.py::TestStartInstance::test_start_instance_creates_record -v
  ```

### 5.4 循环保护

- **验证方式**：创建一个「记录更新触发 → 更新记录」的工作流，更新同一个字段。
- **预期结果**：工作流只执行一次，不会无限循环。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_execution.py::TestLoopProtection -v
  ```

## 六、Webhook 通知

### 6.1 Webhook 配置

- **前端操作**：在工作流页面切换到「Webhook」标签，点击「新建 Webhook」，配置：
  - 名称、请求 URL、请求方法（GET / POST / PUT）。
  - 自定义 Headers。
  - 请求体模板（可选）。
  - 签名密钥（可选）。
- **预期结果**：配置保存后，可在工作流中添加「Webhook」节点调用该配置。
- **后端验证**：
  ```bash
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"name":"测试Webhook","url":"https://httpbin.org/post","method":"POST","headers":{"X-Custom":"value"}}' \
    "http://localhost:5000/api/bases/{base_id}/webhooks"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWebhookRoutes::test_create_webhook \
    tests/test_workflow_routes.py::TestWebhookRoutes::test_get_webhooks_list -v
  ```

### 6.2 Webhook 触发与重试

- **验证方式**：
  1. 配置一个指向无效地址的 Webhook。
  2. 在工作流中添加 Webhook 节点并发布。
  3. 触发工作流，观察投递日志。
- **预期结果**：
  - 首次投递失败。
  - 系统按指数退避策略进行重试。
  - 投递日志中记录每次尝试的状态和响应。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_webhook_service.py::TestDeliver \
    tests/test_webhook_service.py::TestRetryPending -v
  ```

### 6.3 签名验证

- **验证方式**：配置带有 `secret` 的 Webhook，触发后检查请求头中的 `X-Signature`。
- **预期结果**：签名为 `HMAC-SHA256(secret, payload)` 的十六进制字符串。
- **自动化测试**：
  ```bash
  python -m pytest tests/test_webhook_service.py::TestComputeSignature \
    tests/test_webhook_service.py::TestBuildHeaders -v
  ```

## 七、工作流模板

### 7.1 系统模板

- **前端操作**：在工作流设计器中点击「从模板创建」。
- **预期结果**：弹出模板库，显示系统预设模板（如「请假审批」）。
- **后端验证**：
  ```bash
  curl -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflow-templates"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowTemplateRoutes::test_list_templates -v
  ```

### 7.2 保存为模板

- **前端操作**：在已发布工作流上点击「保存为模板」。
- **预期结果**：模板库中新增自定义模板。
- **后端验证**：
  ```bash
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"workflow_id":"{workflow_id}","name":"我的模板","category":"custom"}' \
    "http://localhost:5000/api/workflow-templates"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowTemplateRoutes::test_save_as_template -v
  ```

### 7.3 从模板实例化

- **前端操作**：在模板库中选择模板，点击「使用模板」。
- **预期结果**：基于模板创建新的工作流草稿。
- **后端验证**：
  ```bash
  curl -X POST -H "Authorization: Bearer {token}" \
    -H "Content-Type: application/json" \
    -d '{"base_id":"{base_id}","table_id":"{table_id}","name":"从模板创建"}' \
    "http://localhost:5000/api/workflow-templates/{template_id}/instantiate"
  ```

## 八、执行日志与审计

### 8.1 实例列表

- **前端路径**：工作流页面 → 「执行历史」标签。
- **预期结果**：
  - 显示每次触发产生的工作流实例。
  - 包含触发类型、状态、开始时间、完成时间。
- **后端验证**：
  ```bash
  curl -H "Authorization: Bearer {token}" \
    "http://localhost:5000/api/workflows/{workflow_id}/instances"
  ```
- **自动化测试**：
  ```bash
  python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_get_workflow_instances -v
  ```

### 8.2 节点执行日志

- **前端操作**：在执行历史中点击某个实例，查看节点执行详情。
- **预期结果**：
  - 每个节点的执行状态（成功 / 失败 / 跳过）。
  - 输入上下文和输出结果。
  - 失败时显示错误信息。

## 九、权限控制

### 9.1 角色权限验证

| 角色 | 可执行操作 | 不可执行操作 |
|------|------------|--------------|
| 所有者 / 管理员 | 创建、编辑、发布、删除工作流；创建 Webhook | 无 |
| 编辑者 | 创建和编辑工作流（受 Base 权限约束） | 无特殊限制 |
| 浏览者 | 查看工作流和审批任务 | 创建工作流、创建 Webhook、处理非自己的审批任务 |

### 9.2 验证用例

- **用例 1**：使用 VIEWER 角色调用创建工作流接口。
  - **预期结果**：返回 403。
  - **自动化测试**：
    ```bash
    python -m pytest tests/test_workflow_routes.py::TestWorkflowRoutes::test_viewer_cannot_create_workflow -v
    ```

- **用例 2**：使用 VIEWER 角色调用创建 Webhook 接口。
  - **预期结果**：返回 403。
  - **自动化测试**：
    ```bash
    python -m pytest tests/test_workflow_routes.py::TestWebhookRoutes::test_viewer_cannot_create_webhook -v
    ```

- **用例 3**：非审批人尝试同意审批任务。
  - **预期结果**：返回 403。
  - **自动化测试**：
    ```bash
    python -m pytest tests/test_approval_service.py::TestApprove::test_non_assignee_cannot_approve \
      tests/test_workflow_routes.py::TestApprovalRoutes::test_non_assignee_cannot_approve -v
    ```

## 十、测试命令速查

### 10.1 前端测试

```bash
cd smart-table

# 仅运行工作流相关单元测试
npx vitest run src/services/api/__tests__/workflowApiService.spec.ts \
  src/stores/__tests__/workflowStore.spec.ts \
  src/components/workflow/__tests__/WorkflowDesigner.spec.ts

# 运行全部测试
npm run test
```

### 10.2 后端测试

```bash
cd smarttable-backend

# 工作流核心测试
python -m pytest tests/test_workflow_service.py \
  tests/test_workflow_execution.py \
  tests/test_workflow_routes.py \
  tests/test_approval_service.py \
  tests/test_webhook_service.py -v

# 单个模块测试
python -m pytest tests/test_approval_service.py -v
```

## 十一、常见问题排查

| 现象 | 可能原因 | 排查方法 |
|------|----------|----------|
| 工作流未触发 | 工作流处于 `draft` 或未 `active` | 检查工作流状态，确认已发布 |
| 审批任务未生成 | 审批节点配置中审批人为空或字段类型不匹配 | 检查节点配置的 `assignee_type` 和 `assignee_value` |
| Webhook 投递失败无重试 | 重试调度线程未启动或 Webhook 被禁用 | 检查 `WebhookService` 日志和 `is_active` 字段 |
| 更新记录后触发循环 | 条件节点未正确排除系统更新或递归字段 | 检查条件节点是否过滤了自身更新的字段 |
| 枚举字段读写报错 | 数据库中存储的枚举值与模型不一致 | 确认模型使用 `values_callable=_enum_values`，并重新生成表 |

## 十二、验证完成 checklist

- [ ] 工作流基础 CRUD 正常
- [ ] 触发器（创建 / 更新 / 字段变更 / 手动）均可正常触发
- [ ] 审批流程（或签 / 会签 / 串行）流转正确
- [ ] 自动化任务（条件 / 更新记录 / 创建记录）执行正确
- [ ] Webhook 配置、触发、签名、重试均正常
- [ ] 工作流模板可保存、可复用
- [ ] 执行历史与节点日志可查看
- [ ] VIEWER 无法创建工作流和 Webhook
- [ ] 非审批人无法处理审批任务
- [ ] 前端单元测试 69 项全部通过
- [ ] 后端工作流相关集成测试 64 项全部通过

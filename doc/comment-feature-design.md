# 记录评论与 @提及 功能设计规格

> 版本：v0.1（设计稿）
> 整理日期：2026-10-21
> 适用范围：SmartTable 记录详情评论与 @提及讨论能力
> 说明：本文档为**功能设计规格**，仅规定接口、数据模型、权限、@提及解析、通知与前端交互，不包含实现代码。按规划，本次不修改任何现有文件，文档库中与现状不符的标注（协作文档、飞书对标清单 ✅、测试用例 TC-COL-002）留待后续统一修正。

---

## 1. 概述与目标

### 1.1 背景

SmartTable 协作文档（`docs/zh-CN/user-guide/collaboration.md` 与 `en-US` 版）已描述"记录评论"能力：在记录详情面板添加评论、使用 `@用户名` 提及成员并收到通知。飞书多维表格对标清单亦将其标记为已支持（✅）。

但经代码核查与 `SmartTable测试用例.md` 的 **TC-COL-002** 确认，当前版本实际**未实现**该功能：代码库仅存在孤立的 `RecordComment` 数据模型，缺少评论路由、评论服务、@提及解析、评论通知触发与前端 UI。Commenter 角色因此缺少落地的评论入口（见 TC-COL-004）。

### 1.2 目标

为 SmartTable 记录详情提供完整的评论与讨论能力：

- **记录评论**：成员可对单条记录发表评论，支持分页与时间排序。
- **回复层级**：评论可回复他人评论，复用 `RecordComment.parent_id` 形成讨论树。
- **@提及**：评论内容中 `@用户名 / @显示名` 匹配可访问该记录的成员，被提及者收到通知。
- **三类通知**：① @提及通知；② 回复通知（通知父评论作者）；③ 记录评论通知（通知记录关注者）。
- **权限控制**：Viewer 可读评论；Commenter 及以上可评论；作者可编辑/删除自身评论；Editor+ 可删除任意评论；表分享受限访问用户按加入角色判定。

### 1.3 非目标

- 不编写实现代码（本文档为规格）。
- 不修正现有文档中"已支持"的不实标注。
- 不包含富文本评论、表情回应、评论搜索、移动端独立 App 等扩展（见第 13 节）。

---

## 2. 术语

| 术语 | 说明 |
|---|---|
| 评论（Comment） | 针对单条记录发表的一条讨论内容，对应 `RecordComment` 实例。 |
| 回复（Reply） | `parent_id` 非空的评论，依附于某条父评论。 |
| @提及（Mention） | 评论内容中以 `@名称` 形式引用的成员，用于定向通知。 |
| 关注者（Follower） | 主动关注某条记录、希望在其被评论时收到通知的成员，存于 `record_followers`。 |
| Base 成员 | 通过成员管理加入 Base 的用户，拥有 5 级角色之一。 |
| 表分享成员 | 通过单表分享链接加入、受限访问单表的用户，仅拥有 `viewer/commenter/editor` 角色。 |

---

## 3. 现状与缺口分析

### 3.1 已有资产（应复用，避免重复建设）

| 资产 | 位置 | 说明 |
|---|---|---|
| `RecordComment` 模型 | `app/models/record.py` | 字段：`id(UUID PK)`、`record_id(FK→records, CASCADE)`、`user_id(FK→users, CASCADE)`、`content(Text)`、`parent_id(FK→record_comments, 自引用)`、`created_at`、`updated_at`。已含 `to_dict(include_user=True)` 与 `Record.comments` 关系（按 `created_at.desc()`）。 |
| `NotificationService.send_notification` | `app/services/notification_service.py` | 站内信 + 邮件发送，签名：`send_notification(recipient_user_id=, recipient_email=, template_key=, template_data=, source=, title=, content=, content_text=, send_email=True)`。 |
| `PermissionService.check_permission` | `app/services/permission_service.py` | `check_permission(base_id, user_id, MemberRole)` 做 Base 级 RBAC 校验。 |
| `TableShareService.get_members_role` | `app/services/table_share_service.py` | `get_members_role(table_id, user_id)` 返回表分享受限访问角色（`'viewer'/'commenter'/'editor'` 或 `None`）。 |
| `role_required` / `jwt_required` | `app/utils/decorators.py` | 路由装饰器；`@role_required(['owner','admin','editor','commenter','viewer'])` 用于只读，`['owner','admin','editor']` 用于写操作。 |
| `MemberRole` 枚举 | `app/models/base.py` | `owner / admin / editor / commenter / viewer`。 |
| 记录路由蓝图 | `app/routes/records.py` | `records_bp = Blueprint('records', __name__)`，注册前缀 `/api`，路由形如 `/api/records/<record_id>`。 |

### 3.2 缺口

| 缺口 | 现状 | 本文设计覆盖 |
|---|---|---|
| 评论路由 | 无 | 第 5 节新增 4 个 REST 路由 |
| 评论服务 | 无 | 第 5 节定义 `CommentService` 职责 |
| @提及解析 | 无 | 第 7 节定义解析与匹配算法 |
| 评论通知 | 无 | 第 8 节定义三类通知触发 |
| 前端 UI | 无 | 第 9 节定义评论区交互 |
| 关注者机制 | 无 | 第 4 节新增 `record_followers` 表 |
| 提及关联存储 | 无 | 第 4 节新增 `comment_mentions` 表 |

### 3.3 文档一致性（本次不修正）

- `collaboration.md`（中/英）与飞书对标清单将评论标为"已支持"，与 TC-COL-002（未实现）冲突。
- 本文档按"未实现 + 需补齐"的立场设计；待功能上线后，由文档维护方将 TC-COL-002 翻转为"已实现"验证，并统一协作/对标文档表述。

---

## 4. 数据模型设计

### 4.1 复用 `RecordComment`

直接复用现有模型，字段定义见 3.1。其回复层级（`parent_id` 自引用）与 `to_dict` 已满足基础需求，无需改动。

### 4.2 新增 `comment_mentions`（@提及关联）

**设计决策**：评论正文以纯文本存储原文（保留 `@名称` 字面量以便还原与编辑），同时新增关联表把"被提及成员"结构化存储，以支持通知触发与前端高亮，避免每次渲染都重新解析。

```text
comment_mentions
  id            UUID PK
  comment_id    UUID FK → record_comments.id  (ON DELETE CASCADE)
  mentioned_user_id  UUID FK → users.id       (ON DELETE CASCADE)
  mention_type  VARCHAR  ('mention' | 'reply_parent')  # 区分显式 @ 与回复指向
  created_at    DateTime UTC
  UNIQUE (comment_id, mentioned_user_id)
```

### 4.3 新增 `record_followers`（记录关注者）

支撑"记录评论通知"。用户对记录主动关注后，该记录新增顶层评论时其收到通知。

```text
record_followers
  id          UUID PK
  record_id   UUID FK → records.id   (ON DELETE CASCADE)
  user_id     UUID FK → users.id     (ON DELETE CASCADE)
  created_at  DateTime UTC
  UNIQUE (record_id, user_id)
```

关注入口建议：记录详情面板提供"关注/取消关注"按钮；字段级/数据级权限下仅对可见记录可关注。

### 4.4 评论删除策略（软删除标记）

**设计决策**：为保留回复树的连贯性，评论删除采用"软删除 + 占位"策略，而非依赖现有的 `ondelete='CASCADE'`（级联物理删除）直接硬删：

- 新增 `RecordComment.is_deleted`（`Boolean`，默认 `False`）与 `deleted_at`（`DateTime`，可空）。
- 删除评论时：
  - 若该评论**无任何回复** → 可硬删（或同样软删），级联删除其 `comment_mentions`。
  - 若该评论**含有回复** → 标记 `is_deleted=True`、清空 `content` 为占位文案（`[评论已删除]`）、清除 `comment_mentions`；其回复树保留并上移为原父评论层级（或直接以占位节点为锚点），保证讨论上下文不丢失。
- `to_dict` 对 `is_deleted` 评论输出 `content=null` 与 `deleted=true`，前端渲染占位。
- 记录整体删除仍走 `record_comments` 的 `ON DELETE CASCADE`，无需额外清理。

> 说明：若团队倾向简单硬删（接受回复树断裂），可去掉 `is_deleted`，复用现有级联。本文档推荐软删除以保体验，列为可选实现路径，但默认采用软删。

### 4.5 数据库迁移

仅当采纳 4.2 / 4.3 / 4.4 的新表与字段时，生成 Alembic 迁移版本（参照 `migrations/versions/` 现有命名 `YYYYMMDD_NNNN_*.py`）。若评论正文+提及解析方案改为"不落 `comment_mentions` 表、仅运行时解析"，则 4.2 可省略，迁移范围缩小。

---

## 5. 后端 API 设计

### 5.1 路由归属与前缀

新增路由挂载于现有 `records` 蓝图（前缀 `/api`）或独立 `comments` 蓝图，统一前缀 `/api`。本文以 `records` 蓝图扩展为例：

| 方法 | 路径 | 装饰器（角色） | 说明 |
|---|---|---|---|
| GET | `/api/records/<record_id>/comments` | `@jwt_required` + `@role_required([...viewer])` | 列出评论（分页 + 组装回复树） |
| POST | `/api/records/<record_id>/comments` | `@jwt_required` + `@role_required([...commenter])` | 发表评论 / 回复（含 `parent_id`） |
| PUT | `/api/comments/<comment_id>` | `@jwt_required` + `@role_required([...commenter])` | 编辑自己评论 |
| DELETE | `/api/comments/<comment_id>` | `@jwt_required` + `@role_required([...editor])` | 删除评论（作者或 Editor+） |
| POST | `/api/records/<record_id>/follow` | `@jwt_required` + `@role_required([...viewer])` | 关注 / 取消关注（toggle） |

> 角色装饰器仅做基础角色准入；细粒度"作者本人 / 表分享角色"判定在 handler 内用 `PermissionService` + `TableShareService` 完成（见第 6 节）。

### 5.2 请求与响应 Schema

**GET /comments（列表）**

```jsonc
// Query: page=1, per_page=20, (可选) include_replies=true
// 200 响应
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "record_id": "uuid",
        "content": "请 @张三 看一下这行数据",
        "parent_id": null,
        "created_at": "2026-10-21T08:00:00+00:00",
        "updated_at": "2026-10-21T08:00:00+00:00",
        "is_deleted": false,
        "user": { "id": "uuid", "name": "李四", "avatar": "url" },
        "mentions": [ { "user_id": "uuid", "name": "张三" } ],
        "replies": [ /* 同结构递归，受深度限制 */ ]
      }
    ],
    "total": 42,
    "page": 1,
    "per_page": 20
  }
}
```

**POST /comments（创建 / 回复）**

```jsonc
// Body
{ "content": "请 @张三 复核", "parent_id": "uuid 或 null" }
// 200 响应：返回新建评论（to_dict 结构）；自动触发 @提及/回复/记录评论通知
// parent_id 非空时，若对应父评论不存在或不属于同一 record，返回 400
```

**PUT /comments/\<comment_id\>（编辑）**

```jsonc
// Body: { "content": "更新后的内容" }
// 仅作者本人；返回更新后评论；重新解析 @提及并补充新增提及通知
```

**DELETE /comments/\<comment_id\>（删除）**

```jsonc
// 200: { "success": true }
// 作者本人或 Editor+；按 4.4 软删策略执行
```

### 5.3 错误码表

| 错误码 key | HTTP | 说明 |
|---|---|---|
| `record_does_not_exist` | 404 | 记录不存在或无访问权限 |
| `no_permission_comment` | 403 | 角色低于 `commenter`（含 Viewer、表分享 viewer） |
| `no_permission_delete_comment` | 403 | 非作者且非 Editor+ 尝试删除 |
| `comment_not_found` | 404 | 评论不存在或已删除 |
| `comment_content_empty` | 400 | 内容为空或全部为空白 |
| `comment_content_too_long` | 400 | 超过长度上限（默认 2000 字符） |
| `comment_parent_invalid` | 400 | `parent_id` 不存在 / 不属于同一记录 |
| `comment_edit_forbidden` | 403 | 非作者尝试编辑 |

### 5.4 `CommentService` 职责（伪代码）

```text
CommentService.list(record_id, user, page, per_page)
  - 校验记录可见（PermissionService / TableShareService）
  - 查顶层评论（parent_id IS NULL），分页（默认 20）
  - 递归载入 replies（深度上限 N，如 5），组装树
  - 返回 items + total

CommentService.create(record_id, user, content, parent_id)
  - 校验评论权限（≥commenter）
  - 校验 parent_id 归属（若提供）
  - 持久化 RecordComment
  - 解析 @提及 → 写 comment_mentions + 触发 @提及通知
  - 若 parent_id 非空 → 触发回复通知（父作者）
  - 若 parent_id 为空（顶层）→ 触发记录评论通知（关注者）
  - 返回新建评论

CommentService.update(comment_id, user, content)
  - 校验作者本人
  - 更新 content / updated_at
  - 重新解析 @提及，对新增提及补充通知（不撤回已移除）

CommentService.delete(comment_id, user)
  - 校验作者本人 或 Editor+
  - 按 4.4 软删策略执行
```

---

## 6. 权限模型

### 6.1 权限矩阵（角色 × 评论操作）

| 角色 | 读评论 | 发表评论 | 编辑自己评论 | 删除自己评论 | 删除任意评论 |
|---|:---:|:---:|:---:|:---:|:---:|
| Viewer | ✅ | — | — | — | — |
| Commenter | ✅ | ✅ | ✅ | ✅ | — |
| Editor | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Owner | ✅ | ✅ | ✅ | ✅ | ✅ |

### 6.2 表分享受限访问用户

通过单表分享链接加入的用户，其评论权限以 `TableShareService.get_members_role(table_id, user_id)` 返回的角色为准：

- 返回 `'commenter'` / `'editor'` → 等同 Base 的 Commenter / Editor。
- 返回 `'viewer'` / `None`（非分享成员）→ 等同 Viewer，无评论入口。

判定顺序（与现有记录路由一致）：

```text
can_comment = PermissionService.check_permission(base_id, user, COMMENTER)
            OR TableShareService.get_members_role(table_id, user) in ('commenter','editor')
```

### 6.3 记录可见性

评论读取权限跟随记录的可见性：`PermissionService.check_permission(..., VIEWER)` 或表分享角色非空即通过。高级权限（字段级 / 数据级）影响的是**字段值**可见性，不单独约束评论；只要用户对该记录可见，即可读其评论。

### 6.4 关注权限

关注操作要求记录可见（Viewer 及以上即可关注），避免对用户不可见的记录产生通知。

---

## 7. @提及解析与成员匹配

### 7.1 解析输入

评论 `content` 为纯文本（或经转义的安全富文本），@提及以字面量 `@名称` 出现。解析正则（示意）：

```text
@([^\s@]{1,32})      # 匹配 @ 后连续非空白、非 @ 字符，长度上限 32
```

### 7.2 成员匹配范围

被提及者限定为**能够访问该记录的人员集合**，避免提及无权限的外部用户：

```text
candidates = Base 成员（该 record 所属 base 的全部成员）
            ∪ 表分享成员（该 record 所属 table 的分享加入者）
```

匹配键：成员的 `name`（显示名）或 `username`（登录名），**精确匹配**（前端 autocomplete 保证所选即准确，避免歧义）。若同一名称命中多人，以 `username` 优先，并在前端 autocomplete 中展示全名/头像以消歧。

### 7.3 解析与存储流程

```text
mentions = []
for token in regex_find(content, @(.+)):
    user = candidates.match(name=token) or candidates.match(username=token)
    if user and user.id != current_user.id:   # 不允许自提及通知
        mentions.append(user.id)
mentions = unique(mentions)
for uid in mentions:
    upsert comment_mentions(comment_id, uid, 'mention')
```

### 7.4 前端高亮

前端按 `comment_mentions` 中的 `mentioned_user_id` 将正文对应 `@名称` 渲染为高亮、可点击（跳转成员主页/发消息）的片段；正文渲染统一做 HTML 转义（见 10.1），仅高亮 span 由前端受控生成，杜绝 XSS。

---

## 8. 通知设计（重点）

### 8.1 三类通知概览

| 通知类型 | 触发时机 | 接收人 | 模板键（建议） | source |
|---|---|---|---|---|
| @提及通知 | 创建/编辑评论解析出被提及成员 | 被提及且非作者本人的成员 | `comment_mention` | `comment` |
| 回复通知 | 以 `parent_id` 回复他人评论 | 父评论作者（≠当前用户） | `comment_reply` | `comment` |
| 记录评论通知 | 新增**顶层**评论（parent_id 为空） | 该记录关注者（≠作者本人） | `record_comment` | `comment` |

### 8.2 触发时机与去重

- 在评论写操作**事务提交后**触发通知（参考现有"站内信先于邮件写入"的语义），不阻塞评论返回；通知失败不影响评论已持久化。
- **去重**：同一评论对同一接收人只产生一条通知。
  - @提及：编辑评论重新解析时，仅对**新增**提及补充通知，已移除的提及不撤回历史通知。
  - 回复：每条回复对其父评论作者产生一条（父作者去重，同一父下多次回复各自通知）。
  - 记录评论：对每位关注者各一条；作者本人关注自己的记录不产生通知。
- 接收人若同时是被提及者又是父作者又是关注者，**分别按各类型触发**（不合并），避免漏通知；同一类型内去重。

### 8.3 与 `NotificationService` 集成

```text
NotificationService.send_notification(
    recipient_user_id = mentioned_user_id,
    template_key      = 'comment_mention',     # 需在邮件模板库新增
    source            = 'comment',
    title             = f'{actor.name} 在记录中提到了你',
    content           = render_comment_snippet(record, comment),  # 含记录名/Base/评论摘要
    content_text      = plain_snippet,
    send_email        = True
)
```

三类通知均经同一服务，复用站内信持久化 + 邮件发送链路；`record_comment` 通知建议附记录直达链接，`comment_mention` / `comment_reply` 附评论锚点链接。

### 8.4 通知偏好（呼应协作文档）

协作文档"通知设置"已列出"被 @提及时通知"。本文扩展为三项可配置偏好（默认开启），存储于用户通知偏好表（若现有通知系统已有关注/偏好表则复用，否则新增 `user_notification_prefs`）：

| 偏好项 | 控制的通知 | 默认 |
|---|---|---|
| `notify_on_mention` | @提及通知 | 开启 |
| `notify_on_reply` | 回复通知 | 开启 |
| `notify_on_record_comment` | 记录评论通知 | 开启 |

偏好为关闭时，对应类型通知不发送（站内信与邮件均抑制）；@提及在关闭偏好时仍建议保留站内信最低提示（产品可决策，本文默认"受偏好控制"）。

### 8.5 邮件模板

需在 `EmailTemplateService` 模板库新增三个模板键（`comment_mention` / `comment_reply` / `record_comment`），变量建议：`actor_name`、`base_name`、`table_name`、`record_title`、`comment_snippet`、`record_url`。模板风格与现有注册/分享/工作流通知保持一致。

---

## 9. 前端交互设计

### 9.1 入口与布局

- 记录详情面板（抽屉/侧栏）新增**「评论」**标签页或底部评论区，与字段、变更历史并列。
- 入口处展示评论计数（顶层评论数），与记录行/列表的评论数角标联动。

### 9.2 评论列表与回复树

- 顶层评论按 `created_at` 升序（或用户可切倒序）分页，默认每页 20 条；回复以内联缩进树展示，深度超限（如 >5 层）折叠为"查看更多回复"。
- 每条评论展示：头像、姓名、时间、正文（@提及高亮可点击）、操作区。

### 9.3 评论输入框与 @提及自动补全

- 评论区底部固定输入框（仅 Commenter+ 角色可见；Viewer 显示"无评论权限"提示）。
- 输入 `@` 触发**成员自动补全浮层**：拉取该记录可访问成员列表（Base 成员 + 表分享成员），按名称/用户名过滤，选中后以 `@显示名` 插入正文并记入待提及集合。
- 每条评论提供「回复」按钮 → 聚焦输入框并预置 `parent_id` 与目标引用。
- 发送前进行长度校验与空内容拦截；提交后乐观插入本地列表。

### 9.4 评论操作

- 作者本人可见「编辑」「删除」；Editor+ 对任一评论可见「删除」。
- 编辑以内联文本域完成，提交调 `PUT /comments/<id>`。
- 删除二次确认，调 `DELETE /comments/<id>`；含回复的评论删除后显示 `[评论已删除]` 占位。

### 9.5 关注入口

- 记录详情面板提供「关注 / 已关注」切换按钮，调 `POST /records/<id>/follow`，状态持久化于 `record_followers`。

### 9.6 通知中心联动

- 站内信（`/notifications`）展示三类评论通知，点击跳转记录详情并定位评论锚点。
- 铃铛角标计数含评论类通知。

### 9.7 实时策略（可选）

- 若后端 `ENABLE_REALTIME=true`，新评论经 WebSocket 广播给同记录在线成员，评论区实时刷新。
- 默认（HTTP 模式）：用户打开评论区时拉取最新；提供手动刷新；不强制轮询。

---

## 10. 边界与约束

### 10.1 内容安全（XSS）

- 后端以原文（纯文本/转义后安全片段）入库，**不信任客户端 HTML**。
- 前端渲染评论正文一律按纯文本转义（`textContent` / 框架自动转义）；仅 @提及高亮由前端受控生成 `<span>`，绝不将用户内容作为 HTML 注入。
- 禁止在评论中嵌入可执行脚本；若未来支持富文本，需经白名单 sanitizer。

### 10.2 内容校验

- 非空（去空白后长度 > 0），否则 `comment_content_empty`。
- 长度上限默认 **2000 字符**（可配置），超出 `comment_content_too_long`。
- 频率限制：复用现有 `@write_rate_limit` 装饰器约束发表频率，防止刷屏。

### 10.3 级联与生命周期

- 记录删除：现有 `record_comments.ondelete='CASCADE'` 物理删除评论；`comment_mentions` / `record_followers` 设 `ON DELETE CASCADE` 一并清理，无需额外逻辑。
- 用户删除：评论 `user_id` 设 `ON DELETE CASCADE`；但产品上用户删除通常软禁用，评论保留并展示"已注销用户"。

### 10.4 性能

- 评论列表分页，避免全量加载；回复树在后端组装时限制递归深度（默认 5 层）与每父回复数（如 50），超出折叠。
- @提及解析复杂度 O(提及数 × 候选成员数)，成员规模有限（单 Base 数百级），可接受；可预先构建 `name/username → user_id` 索引。
- 关注者通知批量发送，单次顶层评论关注者过多时（如 >50）可异步队列发送，避免请求阻塞。

### 10.5 并发与一致性

- 评论为追加式，无需乐观锁；编辑需校验作者身份与评论未删除。
- 通知与评论写入分离：评论事务先提交，通知后发，保证评论持久化成功不受邮件服务波动影响。

### 10.6 国际化

- 评论内容本身不翻译；UI 文案（按钮、占位、通知标题）走现有 `app/i18n` 体系（中/英）。

---

## 11. 测试用例设计

> 以下重写并扩展原 **TC-COL-002**（由"未实现验证"翻转为"已实现验证"），层级 P0/P1/P2。正式上线后，由文档维护方将上述用例并入 `SmartTable测试用例.md` 协作模块。

### TC-COMMENT-001 评论列表查看（P0，冒烟）
- **目标**：Viewer 及以上可读取记录评论与回复树。
- **前置**：多角色用户；记录含若干评论与回复。
- **步骤**：以 Viewer 打开记录详情评论区；翻页。
- **预期**：评论与回复树正确展示；分页生效；无评论入口的 Viewer 仅可读不可写。

### TC-COMMENT-002 发表评论（P0，冒烟）
- **目标**：Commenter 及以上可发表评论。
- **前置**：当前用户角色 ≥ Commenter。
- **步骤**：评论区输入内容发表。
- **预期**：评论出现于列表，作者与时间正确；写入 `record_comments`。

### TC-COMMENT-003 回复评论（P1）
- **目标**：以 `parent_id` 回复形成讨论树。
- **步骤**：对某评论点「回复」并提交。
- **预期**：新评论 `parent_id` 指向父评论；前端树状缩进；父评论 `replies` 增加。

### TC-COMMENT-004 编辑 / 删除自己的评论（P1）
- **目标**：作者可编辑、删除自身评论。
- **步骤**：编辑自己评论内容；删除自己无回复的评论；删除含回复的评论。
- **预期**：编辑后 `updated_at` 更新、内容更新；无回复评论硬删；含回复评论软删显示 `[评论已删除]` 占位，回复树保留。

### TC-COMMENT-005 Editor+ 删除任意评论（P1）
- **目标**：Editor/Admin/Owner 可删除他人评论。
- **前置**：以 Editor 访问含他人评论的记录。
- **步骤**：删除他人评论。
- **预期**：成功删除（软删）；Viewer/Commenter 尝试删除他人评论返回 403。

### TC-COMMENT-006 @提及解析与通知（P0，冒烟）
- **目标**：评论 @成员触发被提及者站内信 + 邮件。
- **前置**：评论者与被提及者均为可访问该记录成员。
- **步骤**：评论中 `@显示名` 提及成员并提交。
- **预期**：`comment_mentions` 写入；被提及者收 @提及通知（站内信角标 + 邮件）；正文 @名称高亮；自提及不产生通知。

### TC-COMMENT-007 回复通知（P1）
- **目标**：回复他人评论通知父评论作者。
- **步骤**：回复 A 的评论（回复人 ≠ A）。
- **预期**：A 收到回复通知；回复自己的评论不产生通知。

### TC-COMMENT-008 记录评论通知（关注者）（P1）
- **目标**：新增顶层评论通知记录关注者。
- **前置**：用户 B 关注该记录；用户 A 评论（A ≠ B）。
- **步骤**：A 发表顶层评论。
- **预期**：B 收到记录评论通知；A 关注自己记录不产生通知；非顶层（回复）不触发该通知。

### TC-COMMENT-009 权限边界（P0，冒烟）
- **目标**：角色边界严格。
- **步骤**：Viewer 尝试评论（应无入口/接口 403）；表分享 viewer 角色尝试评论（403）；表分享 commenter 角色评论（成功）；Editor 删他人评论（成功）。
- **预期**：各角色严格按 6.1 / 6.2 矩阵。

### TC-COMMENT-010 @提及范围（P2）
- **目标**：@提及仅限可访问该记录成员。
- **步骤**：评论中 @一个无该记录访问权限的用户。
- **预期**：该用户不进入 `comment_mentions`、不收通知；前端 autocomplete 不展示无权限用户。

### TC-COMMENT-011 边界与约束（P1）
- **目标**：空内容/超长/XSS 转义/级联删除。
- **步骤**：
  1. 提交空或全部空白内容。
  2. 提交超 2000 字符内容。
  3. 评论中含 `<script>` 等片段。
  4. 删除记录后查评论。
- **预期**：① 400 拦截；② 400 拦截；③ 正文转义渲染为文本，不执行；④ 评论随记录级联清除。

### TC-COMMENT-012 通知偏好（P2）
- **目标**：三项通知偏好可关闭对应通知。
- **步骤**：关闭 `notify_on_mention` 后被 @；关闭 `notify_on_reply` 后被回复；关闭 `notify_on_record_comment` 后记录被评论。
- **预期**：对应类型通知不发送；其余类型不受影响。

---

## 12. 验收标准

1. 评论列表、发表、回复、编辑、删除（含软删占位）端到端可用。
2. 三类通知（@提及 / 回复 / 记录评论）正确触发、去重、站内信 + 邮件触达。
3. 权限矩阵（6.1）与表分享受限访问（6.2）严格生效。
4. @提及仅匹配可访问成员，正文高亮且防 XSS。
5. 记录删除级联清理评论与关注者，无孤儿数据。
6. 文档回归：原 TC-COL-002 翻转为"已实现"验证，协作/对标文档的不实 ✅ 标注后续统一修正。

---

## 13. 未来扩展（非本次范围）

- 富文本 / 表情回应（reaction）、评论表情计数。
- 评论编辑历史与"已编辑"标记。
- @提及群组 / 部门（需先补齐群组字段能力）。
- 评论邮件聚合摘要（按日/周汇总未读评论）。
- 评论搜索与按成员筛选。
- 移动端响应式适配细化（当前仅前端响应式）。

---

> 文档结束。本设计规格基于 `smart-table-spec` 现有 `RecordComment` 模型、`NotificationService`、`PermissionService`、`TableShareService` 与 `records` 蓝图路由模式整理，旨在最小化新增代码、最大化复用现有能力。

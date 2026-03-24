# 多维表格功能实现计划

## 任务概述

在 Home.vue 页面实现以下功能：
1. SubTask 2.1.3: 实现多维表格重命名功能
2. SubTask 2.1.4: 实现多维表格删除功能
3. SubTask 2.1.5: 实现多维表格收藏功能
4. SubTask 2.1.6: 实现多维表格搜索功能
5. SubTask 2.2.6: 实现数据表拖拽排序（已在 Base.vue 实现）

## 实现步骤

### 步骤1: 检查并更新 baseService

**文件**: `src/db/services/baseService.ts`

需要确认以下方法是否存在：
- `updateBase(id, data)` - 更新 Base（重命名）
- `deleteBase(id)` - 删除 Base
- `toggleStarBase(id)` - 切换收藏状态

### 步骤2: 更新 baseStore

**文件**: `src/stores/baseStore.ts`

添加以下方法：
- `updateBase(id, data)` - 更新 Base
- `deleteBase(id)` - 删除 Base
- `toggleStarBase(id)` - 切换收藏状态
- `searchBases(keyword)` - 搜索 Base

### 步骤3: 更新 Home.vue

**文件**: `src/views/Home.vue`

添加以下功能：

#### 3.1 搜索功能
- 添加搜索输入框
- 实现实时搜索过滤
- 显示搜索结果数量

#### 3.2 重命名功能
- 添加重命名对话框
- 右键菜单或卡片上的编辑按钮
- 调用 store 方法更新名称

#### 3.3 删除功能
- 添加删除确认对话框
- 右键菜单或卡片上的删除按钮
- 调用 store 方法删除 Base

#### 3.4 收藏功能

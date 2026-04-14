# 多维表格复制功能规范

## Why
用户需要能够快速复制现有的多维表格，以便基于已有表格结构创建新的工作空间，提高工作效率。复制功能应完整保留表格的数据结构和配置，同时排除敏感信息如分享设置和权限。

## What Changes
- **ADDED**: 首页多维表格列表添加"复制"按钮
- **ADDED**: 后端 API 支持完整复制多维表格
- **ADDED**: 复制进度显示和状态反馈
- **ADDED**: 复制错误处理和重试机制

## Impact
- 受影响文件：
  - 前端：首页组件、Base API 服务、路由配置
  - 后端：Base Service、Table Service、View Service、Dashboard Service
- 用户体验：首页每个表格卡片增加复制入口

## ADDED Requirements

### Requirement: 首页复制按钮
The system SHALL provide a copy button for each base in the home page list.

#### Scenario: 显示复制按钮
- **GIVEN** 用户在首页查看多维表格列表
- **WHEN** 列表加载完成
- **THEN** 每个表格项显示"复制"按钮
- **AND** 按钮样式与现有界面风格保持一致

#### Scenario: 点击复制按钮
- **GIVEN** 用户点击某个表格的复制按钮
- **WHEN** 复制操作开始
- **THEN** 显示加载状态提示
- **AND** 按钮变为禁用状态防止重复点击

### Requirement: 后端复制 API
The system SHALL provide a backend API to create a complete copy of a base.

#### Scenario: 复制成功
- **GIVEN** 用户请求复制表格
- **WHEN** 后端接收复制请求
- **THEN** 创建新的 base，名称为"原名称+副本"
- **AND** 复制所有数据表结构及记录
- **AND** 复制所有字段配置
- **AND** 复制所有视图配置
- **AND** 复制所有仪表盘配置
- **AND** 排除分享设置
- **AND** 排除访问权限
- **AND** 排除评论和历史记录
- **AND** 返回新 base 的 ID

#### Scenario: 处理同名冲突
- **GIVEN** 用户复制表格时存在同名副本
- **WHEN** 后端检测到命名冲突
- **THEN** 自动添加序号后缀，如"表格名称 副本(2)"

### Requirement: 复制进度反馈
The system SHALL display copy progress and completion status.

#### Scenario: 显示进度
- **GIVEN** 复制操作进行中
- **WHEN** 复制大型表格需要较长时间
- **THEN** 显示进度指示器（如：复制中 50%）
- **AND** 显示当前复制的阶段（如：复制数据表、复制视图等）

#### Scenario: 复制完成
- **GIVEN** 复制操作完成
- **WHEN** 新 base 创建成功
- **THEN** 显示成功提示
- **AND** 自动刷新首页列表
- **AND** 可选：自动跳转到新 base

#### Scenario: 复制失败
- **GIVEN** 复制操作失败
- **WHEN** 发生错误（如网络错误、权限不足）
- **THEN** 显示错误提示信息
- **AND** 提供重试按钮
- **AND** 记录错误日志

### Requirement: 性能和稳定性
The system SHALL ensure copy operation performance and stability.

#### Scenario: 大型表格复制
- **GIVEN** 复制的表格包含大量数据
- **WHEN** 数据量超过阈值
- **THEN** 使用异步处理
- **AND** 显示后台处理状态
- **AND** 完成后通知用户

#### Scenario: 并发复制
- **GIVEN** 多个用户同时复制表格
- **WHEN** 并发请求到达
- **THEN** 系统稳定处理
- **AND** 不互相干扰

## MODIFIED Requirements
无

## REMOVED Requirements
无

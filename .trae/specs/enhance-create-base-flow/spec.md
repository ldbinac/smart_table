# 首页新建多维表选择功能 - 产品需求文档

## Overview
- **Summary**: 在首页的新建功能区域添加一个选择界面，允许用户在创建新多维表时选择创建空白表格或从模板库中选择模板。
- **Purpose**: 优化用户创建流程，提供更直观的选择体验，让用户能够快速选择创建方式。
- **Target Users**: SmartTable的所有用户。

## Goals
- 在首页新建按钮点击后显示选择界面
- 提供两种创建选项：空白多维表和从模板创建
- 保持与现有设计风格一致
- 确保选择流程简洁流畅

## Non-Goals (Out of Scope)
- 修改模板库本身的展示逻辑
- 修改空白表格的创建流程
- 添加新的模板分类方式

## Background & Context
当前首页点击"新建"按钮后直接弹出创建对话框。用户希望在选择界面中明确区分创建空白表格和从模板创建两种方式，提供更清晰的视觉引导。

## Functional Requirements
- **FR-1**: 点击首页"新建"按钮后显示选择界面（对话框或下拉菜单）
- **FR-2**: 选择界面提供两个选项：创建空白多维表、从模板创建
- **FR-3**: 选择"创建空白多维表"后弹出原有的创建对话框
- **FR-4**: 选择"从模板创建"后跳转到模板页面
- **FR-5**: 选择界面需要有清晰的视觉区分和引导

## Non-Functional Requirements
- **NFR-1**: 选择界面响应速度 < 200ms
- **NFR-2**: 界面设计符合现有系统风格
- **NFR-3**: 移动端适配良好

## Constraints
- **Technical**: Vue 3 + TypeScript + Element Plus
- **Business**: 复用现有的创建对话框和模板页面
- **Dependencies**: 依赖已实现的模板功能

## Assumptions
- 用户已熟悉模板功能
- 模板页面已实现并可正常访问

## Acceptance Criteria

### AC-1: 新建选择界面显示
- **Given**: 用户在首页
- **When**: 点击"新建"按钮
- **Then**: 显示选择界面，包含两个选项：创建空白多维表、从模板创建
- **Verification**: `human-judgment`
- **Notes**: 界面需要有清晰的视觉区分

### AC-2: 创建空白多维表
- **Given**: 用户看到选择界面
- **When**: 选择"创建空白多维表"
- **Then**: 弹出原有的创建对话框
- **Verification**: `human-judgment`
- **Notes**: 复用现有的创建对话框逻辑

### AC-3: 从模板创建
- **Given**: 用户看到选择界面
- **When**: 选择"从模板创建"
- **Then**: 跳转到模板页面
- **Verification**: `human-judgment`
- **Notes**: 导航到模板视图

### AC-4: 视觉设计一致性
- **Given**: 用户查看选择界面
- **When**: 比较与现有系统风格
- **Then**: 风格一致，视觉引导清晰
- **Verification**: `human-judgment`
- **Notes**: 使用Element Plus组件，保持配色一致

## ADDED Requirements

### Requirement: 新建选择界面
The system SHALL provide a selection interface when user clicks the "新建" button on the home page.

#### Scenario: Display selection interface
- **WHEN** user clicks the "新建" button on the home page
- **THEN** the system displays a selection interface with two options:
  - Option 1: "创建空白多维表" - with description and icon
  - Option 2: "从模板创建" - with description and icon

#### Scenario: Create blank base
- **GIVEN** the selection interface is displayed
- **WHEN** user selects "创建空白多维表"
- **THEN** the existing create dialog opens

#### Scenario: Create from template
- **GIVEN** the selection interface is displayed
- **WHEN** user selects "从模板创建"
- **THEN** the system navigates to the templates view

## MODIFIED Requirements
None

## REMOVED Requirements
None

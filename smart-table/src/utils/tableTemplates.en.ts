/**
 * 英文版多维表模板集合（en-US）
 *
 * 与 tableTemplates.ts 中的中文模板（zhTableTemplates）结构、字段 id 完全一致，
 * 仅对 name / description / 选项名 / 文本类记录值做英文翻译。
 * 采用「两套完整模板」方案而非逐字段 i18n 配置，便于后续维护：
 * 新增/修改模板时，直接在中文模板调整后同步翻译到本文件即可。
 *
 * 加载逻辑见 tableTemplates.ts 的 getTableTemplates(lang)。
 */
import type { CellValue } from "../types";
import type { TableTemplate, TemplateRecord } from "./tableTemplates";

const generateId = () => Math.random().toString(36).substr(2, 9);

const selectOptions = (names: string[]): { id: string; name: string; color: string }[] => {
  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];
  return names.map((name, i) => ({
    id: generateId(),
    name,
    color: colors[i % colors.length],
  }));
};

// ==================== 1. Project Management ====================
const projectManagementTemplate: TableTemplate = {
  id: 'project-management',
  name: 'Project Management',
  description: 'Manage project planning, task tracking and team collaboration',
  icon: '📊',
  color: '#3B82F6',
  category: 'Project Management',
  tables: [
    {
      id: 'projects',
      name: 'Projects',
      description: 'Project basic information management',
      order: 0,
      fields: [
        { id: 'proj-name', name: 'Project Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'proj-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['Planning', 'In Progress', 'Completed', 'On Hold', 'Cancelled']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'proj-start', name: 'Start Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'proj-end', name: 'End Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'proj-owner', name: 'Owner', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'proj-priority', name: 'Priority', type: 'single_select', options: { choices: selectOptions(['High', 'Medium', 'Low']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'proj-progress', name: 'Progress', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'proj-budget', name: 'Budget', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'proj-docs', name: 'Documents', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'proj-desc', name: 'Description', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'proj-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'proj-view-1', name: 'Project List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'proj-view-2', name: 'Gantt', type: 'gantt', config: { startDateFieldId: 'proj-start', endDateFieldId: 'proj-end', progressFieldId: 'proj-progress' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'proj-view-3', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'proj-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'proj-rec-1', values: { 'proj-name': 'Smart Table Development', 'proj-status': 'In Progress', 'proj-start': Date.now() - 7 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 30 * 24 * 60 * 60 * 1000, 'proj-progress': 35, 'proj-priority': 'High', 'proj-budget': 500000 } },
        { id: 'proj-rec-2', values: { 'proj-name': 'Website Revamp', 'proj-status': 'Planning', 'proj-start': Date.now(), 'proj-end': Date.now() + 60 * 24 * 60 * 60 * 1000, 'proj-progress': 0, 'proj-priority': 'Medium', 'proj-budget': 80000 } },
        { id: 'proj-rec-3', values: { 'proj-name': 'Mobile Adaptation', 'proj-status': 'In Progress', 'proj-start': Date.now() - 14 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 14 * 24 * 60 * 60 * 1000, 'proj-progress': 60, 'proj-priority': 'High', 'proj-budget': 120000 } },
        { id: 'proj-rec-4', values: { 'proj-name': 'Data Migration', 'proj-status': 'Completed', 'proj-start': Date.now() - 45 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() - 5 * 24 * 60 * 60 * 1000, 'proj-progress': 100, 'proj-priority': 'High', 'proj-budget': 30000 } },
        { id: 'proj-rec-5', values: { 'proj-name': 'User Feedback Optimization', 'proj-status': 'On Hold', 'proj-start': Date.now() - 30 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 90 * 24 * 60 * 60 * 1000, 'proj-progress': 25, 'proj-priority': 'Low', 'proj-budget': 50000 } },
        { id: 'proj-rec-6', values: { 'proj-name': 'API Development', 'proj-status': 'In Progress', 'proj-start': Date.now() - 3 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 21 * 24 * 60 * 60 * 1000, 'proj-progress': 15, 'proj-priority': 'Medium', 'proj-budget': 100000 } }
      ]
    },
    {
      id: 'tasks',
      name: 'Tasks',
      description: 'Project task tracking',
      order: 1,
      fields: [
        { id: 'task-name', name: 'Task Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'task-project', name: 'Project', type: 'link', options: { linkedTableId: 'projects', relationshipType: 'many_to_one' }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'task-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['To Do', 'In Progress', 'Completed', 'Blocked']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'task-assignee', name: 'Assignee', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'task-due', name: 'Due Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'task-priority', name: 'Priority', type: 'single_select', options: { choices: selectOptions(['Urgent', 'High', 'Medium', 'Low']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'task-attachments', name: 'Attachments', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'task-hours', name: 'Estimated Hours', type: 'number', options: { precision: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'task-completed', name: 'Completed', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'task-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'task-view-1', name: 'Task List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'task-view-2', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'task-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'task-view-3', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'task-due' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'task-rec-1', values: { 'task-name': 'Complete data model design', 'task-status': 'Completed', 'task-due': Date.now() - 5 * 24 * 60 * 60 * 1000, 'task-priority': 'High', 'task-hours': 8, 'task-completed': true } },
        { id: 'task-rec-2', values: { 'task-name': 'Develop table view component', 'task-status': 'In Progress', 'task-due': Date.now() + 3 * 24 * 60 * 60 * 1000, 'task-priority': 'Urgent', 'task-hours': 16, 'task-completed': false } },
        { id: 'task-rec-3', values: { 'task-name': 'Write user documentation', 'task-status': 'To Do', 'task-due': Date.now() + 10 * 24 * 60 * 60 * 1000, 'task-priority': 'Medium', 'task-hours': 6, 'task-completed': false } },
        { id: 'task-rec-4', values: { 'task-name': 'Write unit tests', 'task-status': 'In Progress', 'task-due': Date.now() + 5 * 24 * 60 * 60 * 1000, 'task-priority': 'High', 'task-hours': 12, 'task-completed': false } },
        { id: 'task-rec-5', values: { 'task-name': 'Code review', 'task-status': 'To Do', 'task-due': Date.now() + 7 * 24 * 60 * 60 * 1000, 'task-priority': 'Medium', 'task-hours': 4, 'task-completed': false } },
        { id: 'task-rec-6', values: { 'task-name': 'Deploy to production', 'task-status': 'Blocked', 'task-due': Date.now() + 14 * 24 * 60 * 60 * 1000, 'task-priority': 'Urgent', 'task-hours': 2, 'task-completed': false } }
      ]
    }
  ]
};

// ==================== 2. Task Tracking ====================
const taskTrackingTemplate: TableTemplate = {
  id: 'task-tracking',
  name: 'Task Tracking',
  description: 'Simple and efficient task management',
  icon: '✅',
  color: '#10B981',
  category: 'Task Management',
  tables: [
    {
      id: 'tasks',
      name: 'Tasks',
      order: 0,
      fields: [
        { id: 'tt-title', name: 'Task Title', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'tt-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['To Do', 'In Progress', 'Completed', 'Cancelled']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'tt-priority', name: 'Priority', type: 'single_select', options: { choices: selectOptions(['Urgent', 'High', 'Medium', 'Low']) }, isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'tt-due', name: 'Due Date', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'tt-assignee', name: 'Assignee', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'tt-tags', name: 'Tags', type: 'multi_select', options: { choices: selectOptions(['Work', 'Personal', 'Study', 'Life']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'tt-importance', name: 'Importance', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'tt-attachments', name: 'Attachments', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'tt-notes', name: 'Notes', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'tt-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'tt-view-2', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'tt-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'tt-view-3', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'tt-due' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'tt-rec-1', values: { 'tt-title': 'Complete weekly report', 'tt-status': 'In Progress', 'tt-priority': 'High', 'tt-due': Date.now() + 1 * 24 * 60 * 60 * 1000, 'tt-tags': ['Work'], 'tt-importance': 4 } },
        { id: 'tt-rec-2', values: { 'tt-title': 'Read technical articles', 'tt-status': 'To Do', 'tt-priority': 'Medium', 'tt-tags': ['Study'], 'tt-importance': 3 } },
        { id: 'tt-rec-3', values: { 'tt-title': 'Workout', 'tt-status': 'Completed', 'tt-priority': 'Low', 'tt-tags': ['Life'], 'tt-importance': 2 } },
        { id: 'tt-rec-4', values: { 'tt-title': 'Buy daily supplies', 'tt-status': 'To Do', 'tt-priority': 'Medium', 'tt-due': Date.now() + 2 * 24 * 60 * 60 * 1000, 'tt-tags': ['Life'], 'tt-importance': 2 } },
        { id: 'tt-rec-5', values: { 'tt-title': 'Prepare meeting materials', 'tt-status': 'In Progress', 'tt-priority': 'Urgent', 'tt-due': Date.now() + 12 * 60 * 60 * 1000, 'tt-tags': ['Work'], 'tt-importance': 5 } },
        { id: 'tt-rec-6', values: { 'tt-title': 'Learn new framework', 'tt-status': 'Cancelled', 'tt-priority': 'Low', 'tt-tags': ['Study'], 'tt-importance': 1 } }
      ]
    }
  ]
};

// ==================== 3. Customer Management ====================
const customerManagementTemplate: TableTemplate = {
  id: 'customer-management',
  name: 'Customer Management',
  description: 'Customer info, sales leads and follow-up tracking',
  icon: '👥',
  color: '#8B5CF6',
  category: 'Customer Relations',
  tables: [
    {
      id: 'customers',
      name: 'Customers',
      order: 0,
      fields: [
        { id: 'cust-name', name: 'Customer Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cust-contact', name: 'Contact', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cust-phone', name: 'Phone', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cust-email', name: 'Email', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'cust-website', name: 'Website', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cust-stage', name: 'Stage', type: 'single_select', options: { choices: selectOptions(['Lead', 'Prospect', 'Following Up', 'Won', 'Lost']) }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cust-source', name: 'Source', type: 'single_select', options: { choices: selectOptions(['Online Ads', 'Referral', 'Exhibition', 'Telemarketing', 'Organic Search']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cust-value', name: 'Estimated Value', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'cust-rating', name: 'Customer Rating', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'cust-docs', name: 'Customer Files', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'cust-address', name: 'Address', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'cust-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'cust-view-2', name: 'Group by Stage', type: 'kanban', config: { groupFieldId: 'cust-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'cust-view-3', name: 'Customer Gallery', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'cust-rec-1', values: { 'cust-name': 'Tech Company A', 'cust-contact': 'Mr. Zhang', 'cust-phone': '13800138001', 'cust-email': 'ldengbin@126.com', 'cust-website': 'https://github.com/ldbinac/smart_table', 'cust-stage': 'Following Up', 'cust-source': 'Online Ads', 'cust-value': 50000, 'cust-rating': 4 } },
        { id: 'cust-rec-2', values: { 'cust-name': 'Trading Company B', 'cust-contact': 'Mr. Li', 'cust-phone': '13900139002', 'cust-email': 'binac@live.cn', 'cust-stage': 'Won', 'cust-source': 'Referral', 'cust-value': 120000, 'cust-rating': 5 } },
        { id: 'cust-rec-3', values: { 'cust-name': 'Consulting Firm C', 'cust-contact': 'Mr. Wang', 'cust-phone': '13700137003', 'cust-stage': 'Prospect', 'cust-source': 'Exhibition', 'cust-value': 80000, 'cust-rating': 3 } },
        { id: 'cust-rec-4', values: { 'cust-name': 'Manufacturer D', 'cust-contact': 'Mr. Zhao', 'cust-phone': '13600136004', 'cust-email': 'ldengbin@126.com', 'cust-website': 'https://gitee.com/binac/smart_table', 'cust-stage': 'Lead', 'cust-source': 'Organic Search', 'cust-value': 200000, 'cust-rating': 4 } },
        { id: 'cust-rec-5', values: { 'cust-name': 'Retail Chain E', 'cust-contact': 'Mr. Chen', 'cust-phone': '13500135005', 'cust-stage': 'Lost', 'cust-source': 'Telemarketing', 'cust-value': 30000, 'cust-rating': 2 } },
        { id: 'cust-rec-6', values: { 'cust-name': 'Finance Company F', 'cust-contact': 'Mr. Liu', 'cust-phone': '13300133006', 'cust-email': 'binac@live.cn', 'cust-website': 'https://www.zhihu.com/people/lu-dong-bin-19', 'cust-stage': 'Won', 'cust-source': 'Referral', 'cust-value': 500000, 'cust-rating': 5 } }
      ]
    }
  ]
};

// ==================== 4. Product Requirements ====================
const productRequirementsTemplate: TableTemplate = {
  id: 'product-requirements',
  name: 'Product Requirements',
  description: 'Product requirement management, feature planning and prioritization',
  icon: '💡',
  color: '#F59E0B',
  category: 'Product Management',
  tables: [
    {
      id: 'requirements',
      name: 'Requirements',
      order: 0,
      fields: [
        { id: 'pr-id', name: 'Requirement ID', type: 'auto_number', options: { prefix: 'PR-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'pr-title', name: 'Requirement Title', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'pr-type', name: 'Type', type: 'single_select', options: { choices: selectOptions(['New Feature', 'Enhancement', 'Bug Fix', 'Tech Debt']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'pr-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['To Review', 'Planning', 'In Development', 'Testing', 'Released', 'Rejected']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'pr-priority', name: 'Priority', type: 'single_select', options: { choices: selectOptions(['P0-Urgent', 'P1-High', 'P2-Medium', 'P3-Low']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'pr-effort', name: 'Effort', type: 'number', options: { suffix: 'person-days' }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'pr-start', name: 'Planned Start', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'pr-end', name: 'Planned End', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'pr-progress', name: 'Progress', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'pr-reviewer', name: 'Reviewer', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'pr-needs-review', name: 'Needs Review', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'pr-docs', name: 'Requirement Docs', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'pr-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'pr-description', name: 'Description', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 13 }
      ],
      views: [
        { id: 'pr-view-2', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'pr-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'pr-view-3', name: 'Gantt', type: 'gantt', config: { startDateFieldId: 'pr-start', endDateFieldId: 'pr-end', progressFieldId: 'pr-progress' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'pr-rec-1', values: { 'pr-title': 'User login feature', 'pr-type': 'New Feature', 'pr-status': 'Released', 'pr-priority': 'P0-Urgent', 'pr-effort': 5, 'pr-progress': 100, 'pr-needs-review': false } },
        { id: 'pr-rec-2', values: { 'pr-title': 'Optimize loading speed', 'pr-type': 'Enhancement', 'pr-status': 'In Development', 'pr-priority': 'P1-High', 'pr-effort': 3, 'pr-progress': 60, 'pr-needs-review': true } },
        { id: 'pr-rec-3', values: { 'pr-title': 'Add export feature', 'pr-type': 'New Feature', 'pr-status': 'Planning', 'pr-priority': 'P2-Medium', 'pr-effort': 2, 'pr-progress': 0, 'pr-needs-review': true } },
        { id: 'pr-rec-4', values: { 'pr-title': 'Fix memory leak', 'pr-type': 'Bug Fix', 'pr-status': 'Testing', 'pr-priority': 'P0-Urgent', 'pr-effort': 1, 'pr-progress': 90, 'pr-needs-review': false } },
        { id: 'pr-rec-5', values: { 'pr-title': 'Upgrade dependencies', 'pr-type': 'Tech Debt', 'pr-status': 'To Review', 'pr-priority': 'P3-Low', 'pr-effort': 1, 'pr-progress': 0, 'pr-needs-review': false } },
        { id: 'pr-rec-6', values: { 'pr-title': 'Dark mode support', 'pr-type': 'New Feature', 'pr-status': 'Planning', 'pr-priority': 'P1-High', 'pr-effort': 8, 'pr-progress': 0, 'pr-needs-review': true } }
      ]
    }
  ]
};

// ==================== 5. Content Calendar ====================
const contentCalendarTemplate: TableTemplate = {
  id: 'content-calendar',
  name: 'Content Calendar',
  description: 'Content planning, publishing schedule and progress tracking',
  icon: '📅',
  color: '#EC4899',
  category: 'Content Operations',
  tables: [
    {
      id: 'contents',
      name: 'Content',
      order: 0,
      fields: [
        { id: 'cc-title', name: 'Content Title', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cc-type', name: 'Content Type', type: 'single_select', options: { choices: selectOptions(['Blog', 'Video', 'Social Media', 'Email', 'Podcast']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cc-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['Idea', 'Draft', 'In Review', 'Scheduled', 'Published']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cc-publish-date', name: 'Publish Date', type: 'date', options: { includeTime: true }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'cc-platform', name: 'Platform', type: 'multi_select', options: { choices: selectOptions(['WeChat Official Account', 'Weibo', 'Zhihu', 'Bilibili', 'Xiaohongshu', 'Douyin']) }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cc-author', name: 'Author', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cc-tags', name: 'Tags', type: 'multi_select', options: { choices: selectOptions(['Tech', 'Product', 'Operations', 'Case Study', 'Tutorial']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cc-is-original', name: 'Original', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'cc-url', name: 'Content URL', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'cc-cover', name: 'Cover Image', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'cc-views', name: 'Views', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'cc-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'cc-view-2', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'cc-publish-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'cc-view-3', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'cc-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'cc-view-4', name: 'Gallery', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'cc-rec-1', values: { 'cc-title': 'Product Update Announcement - March', 'cc-type': 'Blog', 'cc-status': 'Scheduled', 'cc-publish-date': Date.now() + 3 * 24 * 60 * 60 * 1000, 'cc-platform': ['WeChat Official Account', 'Zhihu'], 'cc-tags': ['Product'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-2', values: { 'cc-title': 'New Feature Tutorial', 'cc-type': 'Video', 'cc-status': 'In Review', 'cc-publish-date': Date.now() + 7 * 24 * 60 * 60 * 1000, 'cc-platform': ['Bilibili', 'Douyin'], 'cc-tags': ['Tutorial'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-3', values: { 'cc-title': 'Industry Trend Analysis', 'cc-type': 'Blog', 'cc-status': 'Draft', 'cc-publish-date': Date.now() + 14 * 24 * 60 * 60 * 1000, 'cc-platform': ['Zhihu'], 'cc-tags': ['Tech'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-4', values: { 'cc-title': 'User Case Study', 'cc-type': 'Social Media', 'cc-status': 'Published', 'cc-publish-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'cc-platform': ['Weibo', 'Xiaohongshu'], 'cc-tags': ['Case Study'], 'cc-is-original': true, 'cc-views': 3500 } },
        { id: 'cc-rec-5', values: { 'cc-title': 'Operations Data Analysis', 'cc-type': 'Email', 'cc-status': 'Idea', 'cc-publish-date': Date.now() + 21 * 24 * 60 * 60 * 1000, 'cc-platform': ['Email'], 'cc-tags': ['Operations'], 'cc-is-original': false, 'cc-views': 0 } },
        { id: 'cc-rec-6', values: { 'cc-title': 'Tech Architecture Deep Dive', 'cc-type': 'Podcast', 'cc-status': 'Draft', 'cc-publish-date': Date.now() + 10 * 24 * 60 * 60 * 1000, 'cc-platform': ['Douyin'], 'cc-tags': ['Tech', 'Tutorial'], 'cc-is-original': true, 'cc-views': 0 } }
      ]
    }
  ]
};

// ==================== 6. Inventory Management ====================
const inventoryManagementTemplate: TableTemplate = {
  id: 'inventory-management',
  name: 'Inventory Management',
  description: 'Product inventory, stock in/out records and low-stock alerts',
  icon: '📦',
  color: '#06B6D4',
  category: 'Inventory Management',
  tables: [
    {
      id: 'products',
      name: 'Products',
      order: 0,
      fields: [
        { id: 'inv-name', name: 'Product Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'inv-sku', name: 'SKU', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'inv-category', name: 'Category', type: 'single_select', options: { choices: selectOptions(['Electronics', 'Clothing', 'Food', 'Home', 'Office Supplies']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'inv-stock', name: 'Current Stock', type: 'number', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'inv-min-stock', name: 'Min Stock', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'inv-price', name: 'Unit Price', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'inv-alert', name: 'Enable Alert', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'inv-images', name: 'Product Images', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'inv-location', name: 'Location', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'inv-supplier', name: 'Supplier', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'inv-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'inv-view-2', name: 'Group by Category', type: 'kanban', config: { groupFieldId: 'inv-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'inv-view-3', name: 'Product Gallery', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'inv-rec-1', values: { 'inv-name': 'Wireless Mouse', 'inv-sku': 'MOUSE-001', 'inv-category': 'Electronics', 'inv-stock': 150, 'inv-min-stock': 20, 'inv-price': 99, 'inv-alert': true, 'inv-location': 'Rack A-3', 'inv-supplier': 'Tech Company A' } },
        { id: 'inv-rec-2', values: { 'inv-name': 'Notebook', 'inv-sku': 'NOTE-001', 'inv-category': 'Office Supplies', 'inv-stock': 25, 'inv-min-stock': 50, 'inv-price': 15, 'inv-alert': true, 'inv-location': 'Rack B-1', 'inv-supplier': 'Stationery Co. B' } },
        { id: 'inv-rec-3', values: { 'inv-name': 'Mechanical Keyboard', 'inv-sku': 'KEYB-001', 'inv-category': 'Electronics', 'inv-stock': 80, 'inv-min-stock': 15, 'inv-price': 399, 'inv-alert': true, 'inv-location': 'Rack A-2', 'inv-supplier': 'Tech Company A' } },
        { id: 'inv-rec-4', values: { 'inv-name': 'Desk', 'inv-sku': 'DESK-001', 'inv-category': 'Home', 'inv-stock': 10, 'inv-min-stock': 5, 'inv-price': 899, 'inv-alert': false, 'inv-location': 'Zone C', 'inv-supplier': 'Furniture Co. C' } },
        { id: 'inv-rec-5', values: { 'inv-name': 'Coffee', 'inv-sku': 'COFF-001', 'inv-category': 'Food', 'inv-stock': 200, 'inv-min-stock': 30, 'inv-price': 35, 'inv-alert': true, 'inv-location': 'Pantry', 'inv-supplier': 'Food Supplier D' } },
        { id: 'inv-rec-6', values: { 'inv-name': 'T-Shirt', 'inv-sku': 'TSHI-001', 'inv-category': 'Clothing', 'inv-stock': 0, 'inv-min-stock': 10, 'inv-price': 129, 'inv-alert': true, 'inv-location': 'Rack D', 'inv-supplier': 'Apparel Factory E' } }
      ]
    }
  ]
};

// ==================== 7. Attendance Record ====================
const attendanceRecordTemplate: TableTemplate = {
  id: 'attendance-record',
  name: 'Attendance Record',
  description: 'Employee attendance, leave and overtime tracking',
  icon: '⏰',
  color: '#84CC16',
  category: 'HR Management',
  tables: [
    {
      id: 'attendance',
      name: 'Attendance',
      order: 0,
      fields: [
        { id: 'att-date', name: 'Date', type: 'date', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'att-employee', name: 'Employee', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'att-type', name: 'Type', type: 'single_select', options: { choices: selectOptions(['Normal', 'Late', 'Early Leave', 'Leave', 'Overtime', 'Absent']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'att-check-in', name: 'Check-in Time', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'att-check-out', name: 'Check-out Time', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'att-hours', name: 'Work Hours', type: 'number', options: { precision: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'att-is-repair', name: 'Corrected', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'att-proof', name: 'Proof Document', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'att-remark', name: 'Remark', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'att-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'att-view-2', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'att-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'att-view-3', name: 'Group by Type', type: 'kanban', config: { groupFieldId: 'att-type' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'att-rec-1', values: { 'att-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'att-type': 'Normal', 'att-hours': 8, 'att-is-repair': false } },
        { id: 'att-rec-2', values: { 'att-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'att-type': 'Late', 'att-hours': 7.5, 'att-remark': 'Traffic jam', 'att-is-repair': false } },
        { id: 'att-rec-3', values: { 'att-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'att-type': 'Leave', 'att-hours': 0, 'att-remark': 'Sick leave', 'att-is-repair': false } },
        { id: 'att-rec-4', values: { 'att-date': Date.now() - 4 * 24 * 60 * 60 * 1000, 'att-type': 'Overtime', 'att-hours': 11, 'att-remark': 'Project launch', 'att-is-repair': false } },
        { id: 'att-rec-5', values: { 'att-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'att-type': 'Normal', 'att-hours': 8, 'att-is-repair': true, 'att-remark': 'Forgot to clock in, corrected' } },
        { id: 'att-rec-6', values: { 'att-date': Date.now() - 6 * 24 * 60 * 60 * 1000, 'att-type': 'Early Leave', 'att-hours': 6, 'att-remark': 'Family matter', 'att-is-repair': false } }
      ]
    }
  ]
};

// ==================== 8. Budget Management ====================
const budgetManagementTemplate: TableTemplate = {
  id: 'budget-management',
  name: 'Budget Management',
  description: 'Income/expense records, budget planning and financial analysis',
  icon: '💰',
  color: '#EF4444',
  category: 'Finance Management',
  tables: [
    {
      id: 'transactions',
      name: 'Transactions',
      order: 0,
      fields: [
        { id: 'bud-date', name: 'Date', type: 'date', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'bud-type', name: 'Type', type: 'single_select', options: { choices: selectOptions(['Income', 'Expense']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'bud-category', name: 'Category', type: 'single_select', options: { choices: selectOptions(['Salary', 'Dining', 'Transport', 'Shopping', 'Entertainment', 'Medical', 'Education', 'Investment', 'Other']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'bud-amount', name: 'Amount', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'bud-description', name: 'Description', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'bud-payment', name: 'Payment Method', type: 'single_select', options: { choices: selectOptions(['Cash', 'WeChat', 'Alipay', 'Bank Card', 'Credit Card']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'bud-is-reimbursed', name: 'Reimbursed', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'bud-invoice', name: 'Invoice', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'bud-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 8 }
      ],
      views: [
        { id: 'bud-view-2', name: 'Group by Type', type: 'kanban', config: { groupFieldId: 'bud-type' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'bud-view-3', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'bud-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'bud-rec-1', values: { 'bud-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'bud-type': 'Income', 'bud-category': 'Salary', 'bud-amount': 15000, 'bud-payment': 'Bank Card', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-2', values: { 'bud-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'bud-type': 'Expense', 'bud-category': 'Dining', 'bud-amount': 85, 'bud-description': 'Lunch', 'bud-payment': 'WeChat', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-3', values: { 'bud-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'bud-type': 'Expense', 'bud-category': 'Transport', 'bud-amount': 30, 'bud-payment': 'Alipay', 'bud-is-reimbursed': true } },
        { id: 'bud-rec-4', values: { 'bud-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bud-type': 'Expense', 'bud-category': 'Shopping', 'bud-amount': 299, 'bud-description': 'Office supplies', 'bud-payment': 'Credit Card', 'bud-is-reimbursed': true } },
        { id: 'bud-rec-5', values: { 'bud-date': Date.now() - 7 * 24 * 60 * 60 * 1000, 'bud-type': 'Expense', 'bud-category': 'Entertainment', 'bud-amount': 120, 'bud-description': 'Movie tickets', 'bud-payment': 'WeChat', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-6', values: { 'bud-date': Date.now() - 10 * 24 * 60 * 60 * 1000, 'bud-type': 'Income', 'bud-category': 'Investment', 'bud-amount': 500, 'bud-description': 'Investment income', 'bud-payment': 'Bank Card', 'bud-is-reimbursed': false } }
      ]
    }
  ]
};

// ==================== 9. Survey & Feedback ====================
const surveyFeedbackTemplate: TableTemplate = {
  id: 'survey-feedback',
  name: 'Survey & Feedback',
  description: 'User surveys, feedback collection and satisfaction analysis',
  icon: '📝',
  color: '#6366F1',
  category: 'User Research',
  tables: [
    {
      id: 'responses',
      name: 'Feedback',
      order: 0,
      fields: [
        { id: 'sur-id', name: 'Feedback ID', type: 'auto_number', options: { prefix: 'FB-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'sur-submit-time', name: 'Submit Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 1 },
        { id: 'sur-satisfaction', name: 'Satisfaction', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'sur-category', name: 'Feedback Type', type: 'single_select', options: { choices: selectOptions(['Feature Suggestion', 'Bug Report', 'Usage Issue', 'Other']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'sur-content', name: 'Feedback Content', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'sur-contact', name: 'Contact', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'sur-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['Pending', 'Processing', 'Resolved', 'Closed']) }, isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'sur-need-follow', name: 'Need Follow-up', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'sur-screenshot', name: 'Screenshot', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'sur-assignee', name: 'Assignee', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'sur-view-2', name: 'Kanban', type: 'kanban', config: { groupFieldId: 'sur-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'sur-view-3', name: 'Collection Form', type: 'form', config: { title: 'User Feedback Collection', description: 'Please share your valuable feedback', submitButtonText: 'Submit Feedback', successMessage: 'Thank you for your feedback!' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'sur-view-4', name: 'Gallery', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'sur-rec-1', values: { 'sur-satisfaction': 4, 'sur-category': 'Feature Suggestion', 'sur-content': 'Hope to add export feature', 'sur-status': 'Processing', 'sur-need-follow': false, 'sur-contact': 'binac@live.cn' } },
        { id: 'sur-rec-2', values: { 'sur-satisfaction': 5, 'sur-category': 'Other', 'sur-content': 'The product is very useful!', 'sur-status': 'Closed', 'sur-need-follow': false } },
        { id: 'sur-rec-3', values: { 'sur-satisfaction': 2, 'sur-category': 'Bug Report', 'sur-content': 'Occasionally errors when saving', 'sur-status': 'Pending', 'sur-need-follow': true, 'sur-contact': '13800138001' } },
        { id: 'sur-rec-4', values: { 'sur-satisfaction': 3, 'sur-category': 'Usage Issue', 'sur-content': "Don't know how to create a view", 'sur-status': 'Resolved', 'sur-need-follow': false, 'sur-contact': 'ldengbin@126.cn' } },
        { id: 'sur-rec-5', values: { 'sur-satisfaction': 5, 'sur-category': 'Feature Suggestion', 'sur-content': 'Suggest adding dark mode', 'sur-status': 'Processing', 'sur-need-follow': false } },
        { id: 'sur-rec-6', values: { 'sur-satisfaction': 1, 'sur-category': 'Bug Report', 'sur-content': 'Blank page after login', 'sur-status': 'Processing', 'sur-need-follow': true, 'sur-contact': '13900139002' } }
      ]
    }
  ]
};

// ==================== 10. Contact List ====================
const contactListTemplate: TableTemplate = {
  id: 'contact-list',
  name: 'Contact List',
  description: 'Contact info management with groups and tags',
  icon: '📇',
  color: '#14B8A6',
  category: 'Personal Management',
  tables: [
    {
      id: 'contacts',
      name: 'Contacts',
      order: 0,
      fields: [
        { id: 'con-name', name: 'Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'con-phone', name: 'Phone', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'con-email', name: 'Email', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'con-company', name: 'Company', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'con-position', name: 'Title', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'con-group', name: 'Group', type: 'single_select', options: { choices: selectOptions(['Family', 'Friend', 'Colleague', 'Customer', 'Other']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'con-address', name: 'Address', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'con-birthday', name: 'Birthday', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'con-avatar', name: 'Avatar', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'con-favorite', name: 'Favorite', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'con-notes', name: 'Notes', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'con-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'con-view-2', name: 'Group by Group', type: 'kanban', config: { groupFieldId: 'con-group' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'con-view-3', name: 'Avatar Gallery', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'con-view-4', name: 'Birthday Calendar', type: 'calendar', config: { dateFieldId: 'con-birthday' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'con-rec-1', values: { 'con-name': 'Zhang San', 'con-phone': '13800138001', 'con-email': 'ldengbin@126.com', 'con-company': 'Tech Company', 'con-position': 'Product Manager', 'con-group': 'Colleague', 'con-favorite': true } },
        { id: 'con-rec-2', values: { 'con-name': 'Li Si', 'con-phone': '13900139002', 'con-group': 'Friend', 'con-birthday': Date.now() - 30 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': false } },
        { id: 'con-rec-3', values: { 'con-name': 'Wang Wu', 'con-phone': '13700137003', 'con-email': 'binac@live.cn', 'con-company': 'Trading Company', 'con-position': 'Sales Director', 'con-group': 'Customer', 'con-favorite': true } },
        { id: 'con-rec-4', values: { 'con-name': 'Zhao Liu', 'con-phone': '13600136004', 'con-group': 'Family', 'con-birthday': Date.now() - 25 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': true } },
        { id: 'con-rec-5', values: { 'con-name': 'Qian Qi', 'con-phone': '13500135005', 'con-email': 'ldengbin@126.cn', 'con-company': 'Consulting Firm', 'con-position': 'Consultant', 'con-group': 'Other', 'con-favorite': false } },
        { id: 'con-rec-6', values: { 'con-name': 'Sun Ba', 'con-phone': '13300133006', 'con-company': 'Financial Institution', 'con-position': 'Analyst', 'con-group': 'Colleague', 'con-favorite': false } }
      ]
    }
  ]
};

// ==================== 11. Meeting Management ====================
const meetingManagementTemplate: TableTemplate = {
  id: 'meeting-management',
  name: 'Meeting Management',
  description: 'Meeting notes, attendees and minutes management',
  icon: '🎯',
  color: '#7C3AED',
  category: 'Team Collaboration',
  tables: [
    {
      id: 'meetings',
      name: 'Meetings',
      order: 0,
      fields: [
        { id: 'meet-title', name: 'Meeting Topic', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'meet-type', name: 'Meeting Type', type: 'single_select', options: { choices: selectOptions(['Regular', 'Project', 'Review', 'Training', 'Other']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'meet-date', name: 'Meeting Time', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'meet-duration', name: 'Duration (min)', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'meet-location', name: 'Location', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'meet-host', name: 'Host', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'meet-attendees', name: 'Attendees', type: 'member', options: { multiple: true }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'meet-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['Scheduled', 'In Progress', 'Ended', 'Cancelled']) }, isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'meet-agenda', name: 'Agenda', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'meet-minutes', name: 'Minutes', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'meet-attachments', name: 'Materials', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'meet-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'meet-view-1', name: 'Meeting List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'meet-view-2', name: 'Calendar', type: 'calendar', config: { dateFieldId: 'meet-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'meet-view-3', name: 'Group by Status', type: 'kanban', config: { groupFieldId: 'meet-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'meet-rec-1', values: { 'meet-title': 'Weekly Standup', 'meet-type': 'Regular', 'meet-date': Date.now() + 1 * 24 * 60 * 60 * 1000, 'meet-duration': 60, 'meet-location': 'Room A', 'meet-status': 'Scheduled', 'meet-agenda': '1.Last week summary\n2.This week plan\n3.Issue discussion' } },
        { id: 'meet-rec-2', values: { 'meet-title': 'Product Review', 'meet-type': 'Review', 'meet-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'meet-duration': 90, 'meet-location': 'Online', 'meet-status': 'Ended', 'meet-minutes': 'Approved, development starts next week' } },
        { id: 'meet-rec-3', values: { 'meet-title': 'Tech Sharing', 'meet-type': 'Training', 'meet-date': Date.now() + 3 * 24 * 60 * 60 * 1000, 'meet-duration': 120, 'meet-location': 'Training Room', 'meet-status': 'Scheduled', 'meet-agenda': 'Vue3 new features sharing' } },
        { id: 'meet-rec-4', values: { 'meet-title': 'Project Kickoff', 'meet-type': 'Project', 'meet-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'meet-duration': 60, 'meet-location': 'Room B', 'meet-status': 'Ended', 'meet-minutes': 'Defined milestones and division' } },
        { id: 'meet-rec-5', values: { 'meet-title': 'Requirement Discussion', 'meet-type': 'Project', 'meet-date': Date.now(), 'meet-duration': 45, 'meet-location': 'Online', 'meet-status': 'In Progress' } },
        { id: 'meet-rec-6', values: { 'meet-title': 'Team Dinner', 'meet-type': 'Other', 'meet-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'meet-status': 'Cancelled', 'meet-duration': 180 } }
      ]
    }
  ]
};

// ==================== 12. Learning Plan ====================
const learningPlanTemplate: TableTemplate = {
  id: 'learning-plan',
  name: 'Learning Plan',
  description: 'Course learning, progress tracking and knowledge management',
  icon: '📚',
  color: '#059669',
  category: 'Personal Management',
  tables: [
    {
      id: 'courses',
      name: 'Courses',
      order: 0,
      fields: [
        { id: 'learn-title', name: 'Course Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'learn-category', name: 'Category', type: 'single_select', options: { choices: selectOptions(['Programming', 'Product Design', 'Data Analysis', 'Language Learning', 'Career Skills', 'Other']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'learn-platform', name: 'Platform', type: 'single_select', options: { choices: selectOptions(['Coursera', 'Udemy', 'Bilibili', 'MOOC', 'GeekTime', 'Self-study']) }, isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'learn-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['Not Started', 'In Progress', 'Completed', 'Paused']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'learn-progress', name: 'Progress', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'learn-start', name: 'Start Date', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'learn-end', name: 'Target Completion', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'learn-hours', name: 'Hours Studied', type: 'number', options: { suffix: 'hours' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'learn-rating', name: 'Course Rating', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'learn-url', name: 'Course URL', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'learn-notes', name: 'Notes', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'learn-resources', name: 'Resources', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'learn-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 }
      ],
      views: [
        { id: 'learn-view-1', name: 'Course List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'learn-view-2', name: 'Learning Kanban', type: 'kanban', config: { groupFieldId: 'learn-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'learn-view-3', name: 'By Category', type: 'kanban', config: { groupFieldId: 'learn-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'learn-rec-1', values: { 'learn-title': 'Vue3 from Beginner to Master', 'learn-category': 'Programming', 'learn-platform': 'Bilibili', 'learn-status': 'In Progress', 'learn-progress': 65, 'learn-start': Date.now() - 14 * 24 * 60 * 60 * 1000, 'learn-hours': 20, 'learn-rating': 5 } },
        { id: 'learn-rec-2', values: { 'learn-title': 'Python Data Analysis', 'learn-category': 'Data Analysis', 'learn-platform': 'Coursera', 'learn-status': 'Completed', 'learn-progress': 100, 'learn-hours': 40, 'learn-rating': 4 } },
        { id: 'learn-rec-3', values: { 'learn-title': 'English Speaking Improvement', 'learn-category': 'Language Learning', 'learn-platform': 'Self-study', 'learn-status': 'In Progress', 'learn-progress': 30, 'learn-hours': 15, 'learn-rating': 3 } },
        { id: 'learn-rec-4', values: { 'learn-title': 'Product Manager Practical', 'learn-category': 'Product Design', 'learn-platform': 'GeekTime', 'learn-status': 'Not Started', 'learn-progress': 0, 'learn-rating': 0 } },
        { id: 'learn-rec-5', values: { 'learn-title': 'TypeScript Advanced', 'learn-category': 'Programming', 'learn-platform': 'MOOC', 'learn-status': 'Paused', 'learn-progress': 45, 'learn-hours': 12, 'learn-rating': 4 } },
        { id: 'learn-rec-6', values: { 'learn-title': 'Workplace Communication', 'learn-category': 'Career Skills', 'learn-platform': 'Udemy', 'learn-status': 'In Progress', 'learn-progress': 80, 'learn-hours': 8, 'learn-rating': 4 } }
      ]
    }
  ]
};

// ==================== 13. Recruitment ====================
const recruitmentTemplate: TableTemplate = {
  id: 'recruitment',
  name: 'Recruitment',
  description: 'Job posting, candidate management and interview tracking',
  icon: '👔',
  color: '#DC2626',
  category: 'HR Management',
  tables: [
    {
      id: 'candidates',
      name: 'Candidates',
      order: 0,
      fields: [
        { id: 'rec-name', name: 'Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'rec-position', name: 'Position', type: 'single_select', options: { choices: selectOptions(['Frontend Dev', 'Backend Dev', 'Product Manager', 'UI Designer', 'QA Engineer', 'Operations Specialist']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'rec-stage', name: 'Interview Stage', type: 'single_select', options: { choices: selectOptions(['Resume Screening', 'First Interview', 'Second Interview', 'Final Interview', 'Hired', 'Rejected']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'rec-phone', name: 'Phone', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'rec-email', name: 'Email', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'rec-source', name: 'Source', type: 'single_select', options: { choices: selectOptions(['Zhaopin', '51job', 'BOSS', 'Headhunter', 'Referral', 'Website']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'rec-experience', name: 'Experience', type: 'number', options: { suffix: 'years' }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'rec-expected-salary', name: 'Expected Salary', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'rec-interview-date', name: 'Interview Time', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'rec-interviewer', name: 'Interviewer', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'rec-rating', name: 'Overall Rating', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'rec-resume', name: 'Resume', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'rec-feedback', name: 'Interview Feedback', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'rec-created', name: 'Applied Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 13 }
      ],
      views: [
        { id: 'rec-view-1', name: 'Candidate List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'rec-view-2', name: 'Interview Kanban', type: 'kanban', config: { groupFieldId: 'rec-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'rec-view-3', name: 'Interview Calendar', type: 'calendar', config: { dateFieldId: 'rec-interview-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'rec-rec-1', values: { 'rec-name': 'Zhang Xiaoming', 'rec-position': 'Frontend Dev', 'rec-stage': 'Second Interview', 'rec-phone': '13800138001', 'rec-email': 'ldengbin@126.cn', 'rec-source': 'BOSS', 'rec-experience': 3, 'rec-expected-salary': 18000, 'rec-rating': 4 } },
        { id: 'rec-rec-2', values: { 'rec-name': 'Li Xiaohong', 'rec-position': 'Product Manager', 'rec-stage': 'Hired', 'rec-phone': '13900139002', 'rec-source': 'Referral', 'rec-experience': 5, 'rec-expected-salary': 25000, 'rec-rating': 5 } },
        { id: 'rec-rec-3', values: { 'rec-name': 'Wang Xiaohua', 'rec-position': 'UI Designer', 'rec-stage': 'First Interview', 'rec-phone': '13700137003', 'rec-source': '51job', 'rec-experience': 2, 'rec-expected-salary': 12000, 'rec-rating': 3 } },
        { id: 'rec-rec-4', values: { 'rec-name': 'Zhao Xiaolong', 'rec-position': 'Backend Dev', 'rec-stage': 'Rejected', 'rec-phone': '13600136004', 'rec-source': 'Zhaopin', 'rec-experience': 1, 'rec-rating': 2, 'rec-feedback': 'Insufficient technical skill' } },
        { id: 'rec-rec-5', values: { 'rec-name': 'Qian Xiaofang', 'rec-position': 'QA Engineer', 'rec-stage': 'Final Interview', 'rec-phone': '13500135005', 'rec-source': 'Headhunter', 'rec-experience': 4, 'rec-expected-salary': 15000, 'rec-rating': 4 } },
        { id: 'rec-rec-6', values: { 'rec-name': 'Sun Xiaoqiang', 'rec-position': 'Operations Specialist', 'rec-stage': 'Resume Screening', 'rec-phone': '13300133006', 'rec-source': 'Website', 'rec-experience': 2, 'rec-expected-salary': 10000 } }
      ]
    }
  ]
};

// ==================== 14. Asset Management ====================
const assetManagementTemplate: TableTemplate = {
  id: 'asset-management',
  name: 'Asset Management',
  description: 'Fixed assets, equipment lending and inventory management',
  icon: '🖥️',
  color: '#0891B2',
  category: 'Administration',
  tables: [
    {
      id: 'assets',
      name: 'Assets',
      order: 0,
      fields: [
        { id: 'asset-code', name: 'Asset Code', type: 'auto_number', options: { prefix: 'AS-', startNumber: 10001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'asset-name', name: 'Asset Name', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'asset-category', name: 'Category', type: 'single_select', options: { choices: selectOptions(['Computer', 'Office Furniture', 'Electronics', 'Vehicle', 'Other']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'asset-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['In Use', 'Idle', 'Under Repair', 'Scrapped', 'Lost']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'asset-user', name: 'User', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'asset-department', name: 'Department', type: 'single_select', options: { choices: selectOptions(['R&D', 'Product', 'Operations', 'Marketing', 'HR', 'Finance']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'asset-purchase-date', name: 'Purchase Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'asset-price', name: 'Purchase Price', type: 'number', options: { format: 'currency', currencySymbol: '$' }, isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'asset-location', name: 'Location', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'asset-warranty', name: 'Warranty Until', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'asset-image', name: 'Asset Photo', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'asset-remark', name: 'Remark', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'asset-created', name: 'Stock-in Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 }
      ],
      views: [
        { id: 'asset-view-1', name: 'Asset List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'asset-view-2', name: 'Group by Status', type: 'kanban', config: { groupFieldId: 'asset-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'asset-view-3', name: 'Group by Category', type: 'kanban', config: { groupFieldId: 'asset-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'asset-rec-1', values: { 'asset-name': 'MacBook Pro 14"', 'asset-category': 'Computer', 'asset-status': 'In Use', 'asset-department': 'R&D', 'asset-purchase-date': Date.now() - 180 * 24 * 60 * 60 * 1000, 'asset-price': 14999, 'asset-location': 'Desk A01', 'asset-warranty': Date.now() + 545 * 24 * 60 * 60 * 1000 } },
        { id: 'asset-rec-2', values: { 'asset-name': 'Ergonomic Chair', 'asset-category': 'Office Furniture', 'asset-status': 'In Use', 'asset-department': 'Product', 'asset-purchase-date': Date.now() - 365 * 24 * 60 * 60 * 1000, 'asset-price': 1999, 'asset-location': 'Desk B02' } },
        { id: 'asset-rec-3', values: { 'asset-name': 'Projector', 'asset-category': 'Electronics', 'asset-status': 'Idle', 'asset-purchase-date': Date.now() - 500 * 24 * 60 * 60 * 1000, 'asset-price': 5999, 'asset-location': 'Room A' } },
        { id: 'asset-rec-4', values: { 'asset-name': 'iPhone 15 Pro', 'asset-category': 'Electronics', 'asset-status': 'Under Repair', 'asset-department': 'Operations', 'asset-purchase-date': Date.now() - 90 * 24 * 60 * 60 * 1000, 'asset-price': 8999, 'asset-remark': 'Screen damaged, under repair' } },
        { id: 'asset-rec-5', values: { 'asset-name': 'Desktop PC', 'asset-category': 'Computer', 'asset-status': 'Scrapped', 'asset-department': 'Marketing', 'asset-purchase-date': Date.now() - 1000 * 24 * 60 * 60 * 1000, 'asset-price': 4500, 'asset-remark': 'Used 5 years, low performance' } },
        { id: 'asset-rec-6', values: { 'asset-name': 'Company Car-粤A12345', 'asset-category': 'Vehicle', 'asset-status': 'In Use', 'asset-department': 'HR', 'asset-purchase-date': Date.now() - 300 * 24 * 60 * 60 * 1000, 'asset-price': 180000 } }
      ]
    }
  ]
};

// ==================== 15. Bug Tracking ====================
const bugTrackingTemplate: TableTemplate = {
  id: 'bug-tracking',
  name: 'Bug Tracking',
  description: 'Defect records, priority management and fix progress tracking',
  icon: '🐛',
  color: '#BE185D',
  category: 'R&D Management',
  tables: [
    {
      id: 'bugs',
      name: 'Defects',
      order: 0,
      fields: [
        { id: 'bug-id', name: 'Bug ID', type: 'auto_number', options: { prefix: 'BUG-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'bug-title', name: 'Bug Title', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'bug-severity', name: 'Severity', type: 'single_select', options: { choices: selectOptions(['Critical', 'Serious', 'Major', 'Minor', 'Suggestion']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'bug-priority', name: 'Priority', type: 'single_select', options: { choices: selectOptions(['P0-Urgent', 'P1-High', 'P2-Medium', 'P3-Low']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'bug-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['New', 'Confirming', 'In Progress', 'Pending Verification', 'Closed', 'Reopened']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'bug-module', name: 'Module', type: 'single_select', options: { choices: selectOptions(['User Module', 'Order Module', 'Payment Module', 'Data Statistics', 'System Settings', 'Other']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'bug-reporter', name: 'Reporter', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'bug-assignee', name: 'Assignee', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'bug-found-date', name: 'Found Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 8 },
        { id: 'bug-fix-date', name: 'Fixed Date', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'bug-environment', name: 'Environment', type: 'single_select', options: { choices: selectOptions(['Production', 'Test', 'Development']) }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'bug-description', name: 'Description', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: true, isVisible: true, order: 11 },
        { id: 'bug-steps', name: 'Steps to Reproduce', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'bug-screenshot', name: 'Screenshot', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 13 },
        { id: 'bug-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 14 }
      ],
      views: [
        { id: 'bug-view-1', name: 'Bug List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'bug-view-2', name: 'Status Kanban', type: 'kanban', config: { groupFieldId: 'bug-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'bug-view-3', name: 'By Severity', type: 'kanban', config: { groupFieldId: 'bug-severity' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'bug-rec-1', values: { 'bug-title': 'Login page fails to load', 'bug-severity': 'Critical', 'bug-priority': 'P0-Urgent', 'bug-status': 'In Progress', 'bug-module': 'User Module', 'bug-found-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': 'Production', 'bug-description': 'Users report blank login page, unable to log in' } },
        { id: 'bug-rec-2', values: { 'bug-title': 'Order list pagination broken', 'bug-severity': 'Serious', 'bug-priority': 'P1-High', 'bug-status': 'Pending Verification', 'bug-module': 'Order Module', 'bug-found-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'bug-fix-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': 'Test' } },
        { id: 'bug-rec-3', values: { 'bug-title': 'Order status not updated after payment', 'bug-severity': 'Serious', 'bug-priority': 'P0-Urgent', 'bug-status': 'New', 'bug-module': 'Payment Module', 'bug-found-date': Date.now(), 'bug-environment': 'Production' } },
        { id: 'bug-rec-4', values: { 'bug-title': 'Data chart display abnormal', 'bug-severity': 'Major', 'bug-priority': 'P2-Medium', 'bug-status': 'Closed', 'bug-module': 'Data Statistics', 'bug-found-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'bug-fix-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'bug-environment': 'Test' } },
        { id: 'bug-rec-5', values: { 'bug-title': 'Settings save button unresponsive', 'bug-severity': 'Major', 'bug-priority': 'P2-Medium', 'bug-status': 'Confirming', 'bug-module': 'System Settings', 'bug-found-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': 'Test' } },
        { id: 'bug-rec-6', values: { 'bug-title': 'Suggest batch export feature', 'bug-severity': 'Suggestion', 'bug-priority': 'P3-Low', 'bug-status': 'New', 'bug-module': 'Other', 'bug-found-date': Date.now() - 7 * 24 * 60 * 60 * 1000, 'bug-environment': 'Production' } }
      ]
    }
  ]
};

// ==================== 16. OKR ====================
const okrTemplate: TableTemplate = {
  id: 'okr-management',
  name: 'OKR',
  description: 'Objectives and Key Results management, progress tracking and alignment',
  icon: '🎯',
  color: '#9333EA',
  category: 'Goal Management',
  tables: [
    {
      id: 'objectives',
      name: 'Objectives',
      order: 0,
      fields: [
        { id: 'okr-title', name: 'Objective Name', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'okr-period', name: 'Period', type: 'single_select', options: { choices: selectOptions(['2024 Q1', '2024 Q2', '2024 Q3', '2024 Q4', '2024 Annual']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'okr-owner', name: 'Owner', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'okr-level', name: 'Level', type: 'single_select', options: { choices: selectOptions(['Company', 'Department', 'Individual']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'okr-progress', name: 'Progress', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'okr-status', name: 'Status', type: 'single_select', options: { choices: selectOptions(['On Track', 'At Risk', 'Delayed', 'Completed']) }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'okr-start', name: 'Start Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'okr-end', name: 'End Date', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'okr-score', name: 'Final Score', type: 'number', options: { precision: 1, min: 0, max: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'okr-description', name: 'Description', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'okr-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'okr-view-1', name: 'Objective List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'okr-view-2', name: 'By Period', type: 'kanban', config: { groupFieldId: 'okr-period' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'okr-view-3', name: 'By Level', type: 'kanban', config: { groupFieldId: 'okr-level' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'okr-rec-1', values: { 'okr-title': 'Improve product UX', 'okr-period': '2024 Q1', 'okr-level': 'Company', 'okr-progress': 75, 'okr-status': 'On Track', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000, 'okr-description': 'Improve user satisfaction by optimizing core features and UI design' } },
        { id: 'okr-rec-2', values: { 'okr-title': 'Complete new feature dev', 'okr-period': '2024 Q1', 'okr-level': 'Department', 'okr-progress': 60, 'okr-status': 'At Risk', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-3', values: { 'okr-title': 'Learn new tech stack', 'okr-period': '2024 Q1', 'okr-level': 'Individual', 'okr-progress': 80, 'okr-status': 'On Track', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-4', values: { 'okr-title': 'Improve team collaboration', 'okr-period': '2024 Q1', 'okr-level': 'Department', 'okr-progress': 45, 'okr-status': 'Delayed', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-5', values: { 'okr-title': 'User growth goal', 'okr-period': '2024 Q2', 'okr-level': 'Company', 'okr-progress': 0, 'okr-status': 'On Track', 'okr-start': Date.now() + 30 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 120 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-6', values: { 'okr-title': 'Tech debt cleanup', 'okr-period': '2024 Q1', 'okr-level': 'Department', 'okr-progress': 100, 'okr-status': 'Completed', 'okr-start': Date.now() - 90 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() - 30 * 24 * 60 * 60 * 1000, 'okr-score': 0.85 } }
      ]
    },
    {
      id: 'key-results',
      name: 'Key Results',
      order: 1,
      fields: [
        { id: 'kr-title', name: 'Key Result', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'kr-objective', name: 'Objective', type: 'link', options: { linkedTableId: 'objectives', relationshipType: 'many_to_one' }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'kr-metric', name: 'Metric', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'kr-target', name: 'Target Value', type: 'number', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'kr-current', name: 'Current Value', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'kr-progress', name: 'Progress', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'kr-owner', name: 'Owner', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'kr-weight', name: 'Weight', type: 'number', options: { suffix: '%', min: 0, max: 100 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'kr-score', name: 'Score', type: 'number', options: { precision: 2, min: 0, max: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'kr-created', name: 'Created Time', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'kr-view-1', name: 'Key Result List', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 }
      ],
      records: [
        { id: 'kr-rec-1', values: { 'kr-title': 'Improve user satisfaction to 4.5', 'kr-metric': 'User satisfaction score', 'kr-target': 4.5, 'kr-current': 4.2, 'kr-progress': 80, 'kr-weight': 30 } },
        { id: 'kr-rec-2', values: { 'kr-title': 'Increase core feature usage by 20%', 'kr-metric': 'Feature usage rate', 'kr-target': 120, 'kr-current': 105, 'kr-progress': 75, 'kr-weight': 40 } },
        { id: 'kr-rec-3', values: { 'kr-title': 'Reduce user churn to 5%', 'kr-metric': 'Monthly churn rate', 'kr-target': 5, 'kr-current': 7, 'kr-progress': 60, 'kr-weight': 30 } }
      ]
    }
  ]
};

// ==================== 17. Full Field Type Test (hidden) ====================
const generateTestRecords = (): TemplateRecord[] => {
  const records: TemplateRecord[] = [];
  const singleSelectOptions = ['Type A', 'Type B', 'Type C', 'Type D', 'Type E'];
  const multiSelectOptions = ['Tag 1', 'Tag 2', 'Tag 3', 'Tag 4', 'Tag 5', 'Tag 6'];

  const pickOne = <T>(arr: T[], i: number): T => arr[i % arr.length];
  const pickSome = <T>(arr: T[], i: number): T[] => {
    const count = i % 4;
    return arr.slice(0, count);
  };

  for (let i = 0; i < 100; i++) {
    const batch = Math.floor(i / 100);
    const idx = i % 100;
    const values: Record<string, CellValue> = {};

    if (batch === 0) {
      values['test-text'] = `Test Record #${i + 1}`;
    } else if (batch === 1 && idx % 7 === 0) {
      values['test-text'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-text'] = 'A'.repeat(500);
    } else if (batch === 3 && idx % 5 === 0) {
      values['test-text'] = '<script>alert("xss")</script>' + (i + 1);
    } else if (batch === 4 && idx % 8 === 0) {
      values['test-text'] = '  ';
    } else {
      values['test-text'] = `Test Record #${i + 1}`;
    }

    if (batch === 0) {
      values['test-longtext'] = `This is the multi-line text content of record #${i + 1}.\nSecond line with line break.\nThird line ends.`;
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-longtext'] = null;
    } else if (batch === 2 && idx % 11 === 0) {
      values['test-longtext'] = 'Long text '.repeat(200).trim();
    } else if (batch === 3 && idx % 7 === 0) {
      values['test-longtext'] = 'Special chars: \n\t\r\0\\\'"`汉字日本語한국어🚀🎉';
    } else if (batch === 4 && idx % 9 === 0) {
      values['test-longtext'] = '\n\n\n\n';
    } else {
      values['test-longtext'] = `Description of record ${i + 1}.`;
    }

    if (batch === 0) {
      values['test-richtext'] = `<p><b>Record ${i + 1}</b>: This is rich text content.</p>`;
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-richtext'] = null;
    } else if (batch === 2 && idx % 8 === 0) {
      values['test-richtext'] = '<div style="font-size:999px">Huge font</div>';
    } else if (batch === 3 && idx % 4 === 0) {
      values['test-richtext'] = '<ul><li>Item 1</li><li>Item 2</li></ul><script>evil()</script>';
    } else if (batch === 4 && idx % 7 === 0) {
      values['test-richtext'] = '<p>🔬🧪🧫🧬🔭📡💻</p>';
    } else {
      values['test-richtext'] = `<p>Normal rich text paragraph #${i + 1}</p>`;
    }

    if (batch === 0) {
      values['test-number'] = i + 1;
    } else if (batch === 1 && idx % 8 === 0) {
      values['test-number'] = null;
    } else if (batch === 2 && idx % 5 === 0) {
      values['test-number'] = 999999999;
    } else if (batch === 2 && idx % 5 === 1) {
      values['test-number'] = -999999999;
    } else if (batch === 2 && idx % 5 === 2) {
      values['test-number'] = 0;
    } else if (batch === 3 && idx % 7 === 0) {
      values['test-number'] = 3.14159265358979;
    } else if (batch === 4 && idx % 6 === 0) {
      values['test-number'] = 1e-10;
    } else {
      values['test-number'] = (i + 1) * 10;
    }

    if (batch === 0) {
      values['test-percent'] = (i % 101);
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-percent'] = null;
    } else if (batch === 2 && idx % 10 === 0) {
      values['test-percent'] = 0;
    } else if (batch === 2 && idx % 10 === 1) {
      values['test-percent'] = 100;
    } else if (batch === 2 && idx % 10 === 2) {
      values['test-percent'] = 200;
    } else if (batch === 3 && idx % 8 === 0) {
      values['test-percent'] = 33.33;
    } else {
      values['test-percent'] = (i * 7) % 101;
    }

    if (batch === 0) {
      values['test-rating'] = (i % 5) + 1;
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-rating'] = null;
    } else if (batch === 2 && idx % 12 === 0) {
      values['test-rating'] = 0;
    } else if (batch === 3 && idx % 10 === 0) {
      values['test-rating'] = 5;
    } else {
      values['test-rating'] = (i * 3) % 5 + 1;
    }

    if (batch === 0) {
      values['test-duration'] = 30 + (i % 10) * 15;
    } else if (batch === 1 && idx % 7 === 0) {
      values['test-duration'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-duration'] = 1440;
    } else if (batch === 2 && idx % 9 === 1) {
      values['test-duration'] = 1;
    } else if (batch === 3 && idx % 6 === 0) {
      values['test-duration'] = 10080;
    } else {
      values['test-duration'] = 60 + (i % 8) * 30;
    }

    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;
    if (batch === 0) {
      values['test-date'] = now + (i - 250) * dayMs;
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-date'] = null;
    } else if (batch === 2 && idx % 7 === 0) {
      values['test-date'] = new Date(2024, 1, 29).getTime();
    } else if (batch === 2 && idx % 7 === 1) {
      values['test-date'] = new Date(1, 0, 1).getTime();
    } else if (batch === 3 && idx % 9 === 0) {
      values['test-date'] = now + 3650 * dayMs;
    } else if (batch === 4 && idx % 6 === 0) {
      values['test-date'] = new Date(2025, 0, 31).getTime();
    } else {
      values['test-date'] = now + (i - 250) * dayMs;
    }

    if (batch === 0) {
      values['test-datetime'] = now + i * 3600000;
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-datetime'] = null;
    } else if (batch === 2 && idx % 8 === 0) {
      values['test-datetime'] = new Date(1970, 0, 1).getTime();
    } else if (batch === 3 && idx % 7 === 0) {
      values['test-datetime'] = new Date(2099, 11, 31, 23, 59, 59).getTime();
    } else if (batch === 4 && idx % 9 === 0) {
      values['test-datetime'] = now + 500 * dayMs;
    } else {
      values['test-datetime'] = now + i * 7200000;
    }

    if (batch === 0) {
      values['test-singleselect'] = pickOne(singleSelectOptions, i);
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-singleselect'] = null;
    } else if (batch === 2 && idx % 13 === 0) {
      values['test-singleselect'] = 'Unknown Option';
    } else {
      values['test-singleselect'] = pickOne(singleSelectOptions, i + 3);
    }

    if (batch === 0) {
      const selected = pickSome(multiSelectOptions, i);
      values['test-multiselect'] = selected.length > 0 ? selected : null;
    } else if (batch === 1 && idx % 3 === 0) {
      values['test-multiselect'] = null;
    } else if (batch === 2 && idx % 11 === 0) {
      values['test-multiselect'] = [...multiSelectOptions];
    } else if (batch === 3 && idx % 6 === 0) {
      values['test-multiselect'] = ['Unknown Tag'];
    } else {
      const selected = pickSome(multiSelectOptions, i + 2);
      values['test-multiselect'] = selected.length > 0 ? selected : null;
    }

    if (batch === 0) {
      values['test-checkbox'] = i % 2 === 0;
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-checkbox'] = null;
    } else if (batch === 2 && idx % 7 === 0) {
      values['test-checkbox'] = true;
    } else {
      values['test-checkbox'] = i % 3 === 0;
    }

    const phones = ['13800138001', '010-88886666', '15912345678', '021-12345678', '400-800-8888'];
    if (batch === 0) {
      values['test-phone'] = pickOne(phones, i);
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-phone'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-phone'] = '000-0000-0000';
    } else if (batch === 3 && idx % 5 === 0) {
      values['test-phone'] = 'invalid-phone';
    } else if (batch === 4 && idx % 4 === 0) {
      values['test-phone'] = '12345';
    } else {
      values['test-phone'] = pickOne(phones, i + 2);
    }

    const emails = ['ldengbin@126.com', 'binac@live.cn'];
    if (batch === 0) {
      values['test-email'] = pickOne(emails, i);
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-email'] = null;
    } else if (batch === 2 && idx % 10 === 0) {
      values['test-email'] = 'ldengbin@126.com';
    } else if (batch === 3 && idx % 5 === 0) {
      values['test-email'] = 'binac@live.cn';
    } else if (batch === 4 && idx % 3 === 0) {
      values['test-email'] = 'not-an-email';
    } else {
      values['test-email'] = pickOne(emails, i + 3);
    }

    const urlList = ['https://github.com/ldbinac/smart_table', 'https://gitee.com/binac/smart_table', 'https://www.zhihu.com/people/lu-dong-bin-19', 'https://blog.csdn.net/q283595518', 'https://juejin.cn/user/2330620381633991', 'https://mp.weixin.qq.com/s/KtvkNesxYRWPHwMqw7BW3w'];
    if (batch === 0) {
      values['test-url'] = pickOne(urlList, i);
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-url'] = null;
    } else if (batch === 2 && idx % 11 === 0) {
      values['test-url'] = 'https://github.com/ldbinac/smart_table';
    } else if (batch === 3 && idx % 7 === 0) {
      values['test-url'] = 'https://gitee.com/binac/smart_table';
    } else if (batch === 4 && idx % 4 === 0) {
      values['test-url'] = 'https://mp.weixin.qq.com/s/KtvkNesxYRWPHwMqw7BW3w';
    } else {
      values['test-url'] = pickOne(urlList, i + 1);
    }

    if (batch === 0) {
      values['test-member'] = 'user_' + ((i % 5) + 1);
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-member'] = null;
    } else {
      values['test-member'] = 'user_' + ((i % 3) + 1);
    }

    if (batch === 0) {
      values['test-collaborator'] = [`user_${(i % 3) + 1}`, `user_${(i % 3) + 2}`];
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-collaborator'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-collaborator'] = [`user_1`, `user_2`, `user_3`, `user_4`, `user_5`];
    } else {
      values['test-collaborator'] = [`user_${(i % 2) + 1}`];
    }

    const attachments = ['report.pdf', 'image.jpg', 'data.xlsx', 'presentation.pptx', 'readme.md'];
    if (batch === 0) {
      values['test-attachment'] = pickOne(attachments, i);
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-attachment'] = null;
    } else if (batch === 2 && idx % 10 === 0) {
      values['test-attachment'] = 'filename_with_very_long_name_that_exceeds_typical_limits_abcdefghijklmnopqrstuvwxyz_1234567890_final_version_v2_final.docx';
    } else if (batch === 3 && idx % 6 === 0) {
      values['test-attachment'] = '中文文件名_测试_文档.pdf';
    } else {
      values['test-attachment'] = pickOne(attachments, i + 2);
    }

    records.push({
      id: `test-rec-${i}`,
      values,
    });
  }

  return records;
};

const fullFieldTypeTestTemplate: TableTemplate = {
  id: 'full-field-type-test',
  name: 'Full Field Type Test',
  description: 'Covers all creatable field types (22), with 100 boundary-value test records, for validating field parsing accuracy and data handling correctness',
  icon: '🧪',
  color: '#6366F1',
  category: 'Field Type Test',
  hidden: true,
  tables: [
    {
      id: 'test-table',
      name: 'Field Type Validation',
      description: 'Comprehensive validation table covering all user-creatable field types, each record covering different data shapes per field',
      order: 0,
      fields: [
        { id: 'test-id', name: 'Record No.', type: 'auto_number', options: { prefix: 'T-', startNumber: 1 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'test-text', name: 'Single Line Text', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 1 },
        { id: 'test-longtext', name: 'Multi Line Text', type: 'long_text', isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'test-richtext', name: 'Rich Text', type: 'rich_text', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'test-number', name: 'Number', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'test-percent', name: 'Percent', type: 'percent', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'test-rating', name: 'Rating', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'test-duration', name: 'Duration', type: 'duration', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'test-date', name: 'Date', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'test-datetime', name: 'Date Time', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'test-singleselect', name: 'Single Select', type: 'single_select', options: { choices: selectOptions(['Type A', 'Type B', 'Type C', 'Type D', 'Type E']) }, isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'test-multiselect', name: 'Multi Select', type: 'multi_select', options: { choices: selectOptions(['Tag 1', 'Tag 2', 'Tag 3', 'Tag 4', 'Tag 5', 'Tag 6']) }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'test-checkbox', name: 'Checkbox', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 13 },
        { id: 'test-phone', name: 'Phone', type: 'phone', isPrimary: false, isRequired: false, isVisible: true, order: 14 },
        { id: 'test-email', name: 'Email', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 15 },
        { id: 'test-url', name: 'URL', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 16 },
        { id: 'test-member', name: 'Member', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 18 },
        { id: 'test-collaborator', name: 'Collaborator', type: 'collaborator', options: { multiple: true }, isPrimary: false, isRequired: false, isVisible: true, order: 19 },
        { id: 'test-attachment', name: 'Attachment', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 20 },
      ],
      views: [
        {
          id: 'test-view-3', name: 'Group by Type', type: 'kanban',
          config: { groupFieldId: 'test-singleselect' },
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 2,
        },
        {
          id: 'test-view-4', name: 'Calendar', type: 'calendar',
          config: { dateFieldId: 'test-date' },
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 3,
        },
        {
          id: 'test-view-5', name: 'Gallery', type: 'gallery',
          config: {},
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 4,
        },
      ],
      records: generateTestRecords(),
    }
  ]
};

export const enTableTemplates: TableTemplate[] = [
  projectManagementTemplate,
  taskTrackingTemplate,
  customerManagementTemplate,
  productRequirementsTemplate,
  contentCalendarTemplate,
  inventoryManagementTemplate,
  attendanceRecordTemplate,
  budgetManagementTemplate,
  surveyFeedbackTemplate,
  contactListTemplate,
  meetingManagementTemplate,
  learningPlanTemplate,
  recruitmentTemplate,
  assetManagementTemplate,
  bugTrackingTemplate,
  okrTemplate,
  fullFieldTypeTestTemplate,
];

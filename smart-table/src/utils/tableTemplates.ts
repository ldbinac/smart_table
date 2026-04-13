import type { FieldTypeValue, CellValue, ViewTypeValue, ViewConfig, FieldOptions } from '../types';

export interface TemplateField {
  id: string;
  name: string;
  type: FieldTypeValue;
  options?: FieldOptions;
  isPrimary: boolean;
  isRequired: boolean;
  isVisible: boolean;
  defaultValue?: CellValue;
  description?: string;
  order: number;
}

export interface TemplateView {
  id: string;
  name: string;
  type: ViewTypeValue;
  config: ViewConfig;
  filters: unknown[];
  sorts: unknown[];
  groupBys: string[];
  hiddenFields: string[];
  frozenFields: string[];
  rowHeight: 'short' | 'medium' | 'tall';
  isDefault: boolean;
  order: number;
  description?: string;
  fieldWidths?: Record<string, number>;
}

export interface TemplateRecord {
  id: string;
  values: Record<string, CellValue>;
}

export interface TemplateTable {
  id: string;
  name: string;
  description?: string;
  fields: TemplateField[];
  views: TemplateView[];
  records: TemplateRecord[];
  order: number;
  sampleData?: Record<string, unknown>[];
}

export interface TableTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  category: string;
  tables: TemplateTable[];
}

const generateId = () => Math.random().toString(36).substr(2, 9);

const selectOptions = (names: string[]): { id: string; name: string; color: string }[] => {
  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];
  return names.map((name, i) => ({
    id: generateId(),
    name,
    color: colors[i % colors.length]
  }));
};

// ==================== 1. 项目管理模板 ====================
const projectManagementTemplate: TableTemplate = {
  id: 'project-management',
  name: '项目管理',
  description: '管理项目计划、任务跟踪和团队协作',
  icon: '📊',
  color: '#3B82F6',
  category: '项目管理',
  tables: [
    {
      id: 'projects',
      name: '项目',
      description: '项目基本信息管理',
      order: 0,
      fields: [
        { id: 'proj-name', name: '项目名称', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'proj-status', name: '状态', type: 'single_select', options: { options: selectOptions(['规划中', '进行中', '已完成', '已暂停', '已取消']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'proj-start', name: '开始日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'proj-end', name: '结束日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'proj-owner', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'proj-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'proj-progress', name: '进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'proj-budget', name: '预算', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'proj-docs', name: '项目文档', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'proj-desc', name: '描述', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'proj-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'proj-view-1', name: '项目列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'proj-view-2', name: '甘特图', type: 'gantt', config: { startDateFieldId: 'proj-start', endDateFieldId: 'proj-end', progressFieldId: 'proj-progress' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'proj-view-3', name: '看板视图', type: 'kanban', config: { groupFieldId: 'proj-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'proj-rec-1', values: { 'proj-name': 'Smart Table 开发', 'proj-status': '进行中', 'proj-start': Date.now() - 7 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 30 * 24 * 60 * 60 * 1000, 'proj-progress': 35, 'proj-priority': '高', 'proj-budget': 500000 } },
        { id: 'proj-rec-2', values: { 'proj-name': '官网改版', 'proj-status': '规划中', 'proj-start': Date.now(), 'proj-end': Date.now() + 60 * 24 * 60 * 60 * 1000, 'proj-progress': 0, 'proj-priority': '中', 'proj-budget': 80000 } },
        { id: 'proj-rec-3', values: { 'proj-name': '移动端适配', 'proj-status': '进行中', 'proj-start': Date.now() - 14 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 14 * 24 * 60 * 60 * 1000, 'proj-progress': 60, 'proj-priority': '高', 'proj-budget': 120000 } },
        { id: 'proj-rec-4', values: { 'proj-name': '数据迁移', 'proj-status': '已完成', 'proj-start': Date.now() - 45 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() - 5 * 24 * 60 * 60 * 1000, 'proj-progress': 100, 'proj-priority': '高', 'proj-budget': 30000 } },
        { id: 'proj-rec-5', values: { 'proj-name': '用户反馈优化', 'proj-status': '已暂停', 'proj-start': Date.now() - 30 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 90 * 24 * 60 * 60 * 1000, 'proj-progress': 25, 'proj-priority': '低', 'proj-budget': 50000 } },
        { id: 'proj-rec-6', values: { 'proj-name': 'API 接口开发', 'proj-status': '进行中', 'proj-start': Date.now() - 3 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 21 * 24 * 60 * 60 * 1000, 'proj-progress': 15, 'proj-priority': '中', 'proj-budget': 100000 } }
      ]
    },
    {
      id: 'tasks',
      name: '任务',
      description: '项目任务跟踪',
      order: 1,
      fields: [
        { id: 'task-name', name: '任务名称', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'task-project', name: '所属项目', type: 'link', options: { linkedTableId: 'projects', relationshipType: 'many_to_one' }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'task-status', name: '状态', type: 'single_select', options: { options: selectOptions(['待办', '进行中', '已完成', '已阻塞']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'task-assignee', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'task-due', name: '截止日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'task-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['紧急', '高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'task-attachments', name: '附件', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'task-hours', name: '预计工时', type: 'number', options: { precision: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'task-completed', name: '已完成', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'task-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'task-view-1', name: '任务列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'task-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'task-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'task-view-3', name: '日历视图', type: 'calendar', config: { dateFieldId: 'task-due' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'task-rec-1', values: { 'task-name': '完成数据模型设计', 'task-status': '已完成', 'task-due': Date.now() - 5 * 24 * 60 * 60 * 1000, 'task-priority': '高', 'task-hours': 8, 'task-completed': true } },
        { id: 'task-rec-2', values: { 'task-name': '开发表格视图组件', 'task-status': '进行中', 'task-due': Date.now() + 3 * 24 * 60 * 60 * 1000, 'task-priority': '紧急', 'task-hours': 16, 'task-completed': false } },
        { id: 'task-rec-3', values: { 'task-name': '编写用户文档', 'task-status': '待办', 'task-due': Date.now() + 10 * 24 * 60 * 60 * 1000, 'task-priority': '中', 'task-hours': 6, 'task-completed': false } },
        { id: 'task-rec-4', values: { 'task-name': '单元测试编写', 'task-status': '进行中', 'task-due': Date.now() + 5 * 24 * 60 * 60 * 1000, 'task-priority': '高', 'task-hours': 12, 'task-completed': false } },
        { id: 'task-rec-5', values: { 'task-name': '代码审查', 'task-status': '待办', 'task-due': Date.now() + 7 * 24 * 60 * 60 * 1000, 'task-priority': '中', 'task-hours': 4, 'task-completed': false } },
        { id: 'task-rec-6', values: { 'task-name': '部署到生产环境', 'task-status': '已阻塞', 'task-due': Date.now() + 14 * 24 * 60 * 60 * 1000, 'task-priority': '紧急', 'task-hours': 2, 'task-completed': false } }
      ]
    }
  ]
};

// ==================== 2. 任务跟踪模板 ====================
const taskTrackingTemplate: TableTemplate = {
  id: 'task-tracking',
  name: '任务跟踪',
  description: '简单高效的任务管理',
  icon: '✅',
  color: '#10B981',
  category: '任务管理',
  tables: [
    {
      id: 'tasks',
      name: '任务',
      order: 0,
      fields: [
        { id: 'tt-title', name: '任务标题', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'tt-status', name: '状态', type: 'single_select', options: { options: selectOptions(['待办', '进行中', '已完成', '已取消']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'tt-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['紧急', '高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'tt-due', name: '截止日期', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'tt-assignee', name: '负责人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'tt-tags', name: '标签', type: 'multi_select', options: { options: selectOptions(['工作', '个人', '学习', '生活']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'tt-importance', name: '重要程度', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'tt-attachments', name: '附件', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'tt-notes', name: '备注', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'tt-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'tt-view-2', name: '看板', type: 'kanban', config: { groupFieldId: 'tt-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'tt-view-3', name: '日历', type: 'calendar', config: { dateFieldId: 'tt-due' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'tt-rec-1', values: { 'tt-title': '完成周报', 'tt-status': '进行中', 'tt-priority': '高', 'tt-due': Date.now() + 1 * 24 * 60 * 60 * 1000, 'tt-tags': ['工作'], 'tt-importance': 4 } },
        { id: 'tt-rec-2', values: { 'tt-title': '阅读技术文章', 'tt-status': '待办', 'tt-priority': '中', 'tt-tags': ['学习'], 'tt-importance': 3 } },
        { id: 'tt-rec-3', values: { 'tt-title': '健身锻炼', 'tt-status': '已完成', 'tt-priority': '低', 'tt-tags': ['生活'], 'tt-importance': 2 } },
        { id: 'tt-rec-4', values: { 'tt-title': '购买生活用品', 'tt-status': '待办', 'tt-priority': '中', 'tt-due': Date.now() + 2 * 24 * 60 * 60 * 1000, 'tt-tags': ['生活'], 'tt-importance': 2 } },
        { id: 'tt-rec-5', values: { 'tt-title': '准备会议材料', 'tt-status': '进行中', 'tt-priority': '紧急', 'tt-due': Date.now() + 12 * 60 * 60 * 1000, 'tt-tags': ['工作'], 'tt-importance': 5 } },
        { id: 'tt-rec-6', values: { 'tt-title': '学习新框架', 'tt-status': '已取消', 'tt-priority': '低', 'tt-tags': ['学习'], 'tt-importance': 1 } }
      ]
    }
  ]
};

// ==================== 3. 客户管理模板 ====================
const customerManagementTemplate: TableTemplate = {
  id: 'customer-management',
  name: '客户管理',
  description: '客户信息、销售线索和跟进记录管理',
  icon: '👥',
  color: '#8B5CF6',
  category: '客户关系',
  tables: [
    {
      id: 'customers',
      name: '客户',
      order: 0,
      fields: [
        { id: 'cust-name', name: '客户名称', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cust-contact', name: '联系人', type: 'text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cust-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cust-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'cust-website', name: '官网', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cust-stage', name: '阶段', type: 'single_select', options: { options: selectOptions(['潜在客户', '意向客户', '跟进中', '成交客户', '流失客户']) }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cust-source', name: '来源', type: 'single_select', options: { options: selectOptions(['线上广告', '朋友推荐', '展会', '电话营销', '自然搜索']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cust-value', name: '预估价值', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'cust-rating', name: '客户评级', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'cust-docs', name: '客户资料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'cust-address', name: '地址', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'cust-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'cust-view-2', name: '按阶段分组', type: 'kanban', config: { groupFieldId: 'cust-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'cust-view-3', name: '客户画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'cust-rec-1', values: { 'cust-name': '科技公司A', 'cust-contact': '张经理', 'cust-phone': '13800138001', 'cust-email': 'zhang@example.com', 'cust-website': 'https://company-a.com', 'cust-stage': '跟进中', 'cust-source': '线上广告', 'cust-value': 50000, 'cust-rating': 4 } },
        { id: 'cust-rec-2', values: { 'cust-name': '贸易公司B', 'cust-contact': '李总', 'cust-phone': '13900139002', 'cust-email': 'li@example.com', 'cust-stage': '成交客户', 'cust-source': '朋友推荐', 'cust-value': 120000, 'cust-rating': 5 } },
        { id: 'cust-rec-3', values: { 'cust-name': '咨询机构C', 'cust-contact': '王总监', 'cust-phone': '13700137003', 'cust-stage': '意向客户', 'cust-source': '展会', 'cust-value': 80000, 'cust-rating': 3 } },
        { id: 'cust-rec-4', values: { 'cust-name': '制造企业D', 'cust-contact': '赵经理', 'cust-phone': '13600136004', 'cust-email': 'zhao@example.com', 'cust-website': 'https://factory-d.com', 'cust-stage': '潜在客户', 'cust-source': '自然搜索', 'cust-value': 200000, 'cust-rating': 4 } },
        { id: 'cust-rec-5', values: { 'cust-name': '零售连锁E', 'cust-contact': '陈店长', 'cust-phone': '13500135005', 'cust-stage': '流失客户', 'cust-source': '电话营销', 'cust-value': 30000, 'cust-rating': 2 } },
        { id: 'cust-rec-6', values: { 'cust-name': '金融公司F', 'cust-contact': '刘总监', 'cust-phone': '13300133006', 'cust-email': 'liu@example.com', 'cust-website': 'https://finance-f.com', 'cust-stage': '成交客户', 'cust-source': '朋友推荐', 'cust-value': 500000, 'cust-rating': 5 } }
      ]
    }
  ]
};

// ==================== 4. 产品需求模板 ====================
const productRequirementsTemplate: TableTemplate = {
  id: 'product-requirements',
  name: '产品需求',
  description: '产品需求管理、功能规划和优先级排序',
  icon: '💡',
  color: '#F59E0B',
  category: '产品管理',
  tables: [
    {
      id: 'requirements',
      name: '需求',
      order: 0,
      fields: [
        { id: 'pr-id', name: '需求编号', type: 'auto_number', options: { prefix: 'PR-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'pr-title', name: '需求标题', type: 'text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'pr-type', name: '类型', type: 'single_select', options: { options: selectOptions(['新功能', '优化', 'Bug修复', '技术债务']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'pr-status', name: '状态', type: 'single_select', options: { options: selectOptions(['待评估', '规划中', '开发中', '测试中', '已上线', '已拒绝']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'pr-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['P0-紧急', 'P1-高', 'P2-中', 'P3-低']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'pr-effort', name: '工作量', type: 'number', options: { suffix: '人天' }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'pr-start', name: '计划开始', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'pr-end', name: '计划结束', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'pr-progress', name: '进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'pr-reviewer', name: '评审人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'pr-needs-review', name: '需要评审', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'pr-docs', name: '需求文档', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'pr-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'pr-description', name: '详细描述', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 13 }
      ],
      views: [
        { id: 'pr-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'pr-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'pr-view-3', name: '甘特图', type: 'gantt', config: { startDateFieldId: 'pr-start', endDateFieldId: 'pr-end', progressFieldId: 'pr-progress' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'pr-rec-1', values: { 'pr-title': '用户登录功能', 'pr-type': '新功能', 'pr-status': '已上线', 'pr-priority': 'P0-紧急', 'pr-effort': 5, 'pr-progress': 100, 'pr-needs-review': false } },
        { id: 'pr-rec-2', values: { 'pr-title': '优化加载速度', 'pr-type': '优化', 'pr-status': '开发中', 'pr-priority': 'P1-高', 'pr-effort': 3, 'pr-progress': 60, 'pr-needs-review': true } },
        { id: 'pr-rec-3', values: { 'pr-title': '添加导出功能', 'pr-type': '新功能', 'pr-status': '规划中', 'pr-priority': 'P2-中', 'pr-effort': 2, 'pr-progress': 0, 'pr-needs-review': true } },
        { id: 'pr-rec-4', values: { 'pr-title': '修复内存泄漏', 'pr-type': 'Bug修复', 'pr-status': '测试中', 'pr-priority': 'P0-紧急', 'pr-effort': 1, 'pr-progress': 90, 'pr-needs-review': false } },
        { id: 'pr-rec-5', values: { 'pr-title': '升级依赖库', 'pr-type': '技术债务', 'pr-status': '待评估', 'pr-priority': 'P3-低', 'pr-effort': 1, 'pr-progress': 0, 'pr-needs-review': false } },
        { id: 'pr-rec-6', values: { 'pr-title': '暗黑模式支持', 'pr-type': '新功能', 'pr-status': '规划中', 'pr-priority': 'P1-高', 'pr-effort': 8, 'pr-progress': 0, 'pr-needs-review': true } }
      ]
    }
  ]
};

// ==================== 5. 内容日历模板 ====================
const contentCalendarTemplate: TableTemplate = {
  id: 'content-calendar',
  name: '内容日历',
  description: '内容创作计划、发布安排和进度跟踪',
  icon: '📅',
  color: '#EC4899',
  category: '内容运营',
  tables: [
    {
      id: 'contents',
      name: '内容',
      order: 0,
      fields: [
        { id: 'cc-title', name: '内容标题', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cc-type', name: '内容类型', type: 'single_select', options: { options: selectOptions(['博客', '视频', '社交媒体', '邮件', '播客']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cc-status', name: '状态', type: 'single_select', options: { options: selectOptions(['想法', '草稿', '审核中', '已排期', '已发布']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cc-publish-date', name: '发布日期', type: 'date', options: { includeTime: true }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'cc-platform', name: '发布平台', type: 'multi_select', options: { options: selectOptions(['微信公众号', '微博', '知乎', 'B站', '小红书', '抖音']) }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cc-author', name: '作者', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cc-tags', name: '标签', type: 'multi_select', options: { options: selectOptions(['技术', '产品', '运营', '案例', '教程']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cc-is-original', name: '原创内容', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'cc-url', name: '内容链接', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'cc-cover', name: '封面图', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'cc-views', name: '阅读量', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'cc-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'cc-view-2', name: '日历视图', type: 'calendar', config: { dateFieldId: 'cc-publish-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'cc-view-3', name: '看板视图', type: 'kanban', config: { groupFieldId: 'cc-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'cc-view-4', name: '内容画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'cc-rec-1', values: { 'cc-title': '产品更新公告 - 3月版', 'cc-type': '博客', 'cc-status': '已排期', 'cc-publish-date': Date.now() + 3 * 24 * 60 * 60 * 1000, 'cc-platform': ['微信公众号', '知乎'], 'cc-tags': ['产品'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-2', values: { 'cc-title': '新功能使用教程', 'cc-type': '视频', 'cc-status': '审核中', 'cc-publish-date': Date.now() + 7 * 24 * 60 * 60 * 1000, 'cc-platform': ['B站', '抖音'], 'cc-tags': ['教程'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-3', values: { 'cc-title': '行业趋势分析', 'cc-type': '博客', 'cc-status': '草稿', 'cc-publish-date': Date.now() + 14 * 24 * 60 * 60 * 1000, 'cc-platform': ['知乎'], 'cc-tags': ['技术'], 'cc-is-original': true, 'cc-views': 0 } },
        { id: 'cc-rec-4', values: { 'cc-title': '用户案例分享', 'cc-type': '社交媒体', 'cc-status': '已发布', 'cc-publish-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'cc-platform': ['微博', '小红书'], 'cc-tags': ['案例'], 'cc-is-original': true, 'cc-views': 3500 } },
        { id: 'cc-rec-5', values: { 'cc-title': '运营数据分析', 'cc-type': '邮件', 'cc-status': '想法', 'cc-publish-date': Date.now() + 21 * 24 * 60 * 60 * 1000, 'cc-platform': ['邮件'], 'cc-tags': ['运营'], 'cc-is-original': false, 'cc-views': 0 } },
        { id: 'cc-rec-6', values: { 'cc-title': '技术架构解析', 'cc-type': '播客', 'cc-status': '草稿', 'cc-publish-date': Date.now() + 10 * 24 * 60 * 60 * 1000, 'cc-platform': ['抖音'], 'cc-tags': ['技术', '教程'], 'cc-is-original': true, 'cc-views': 0 } }
      ]
    }
  ]
};

// ==================== 6. 库存管理模板 ====================
const inventoryManagementTemplate: TableTemplate = {
  id: 'inventory-management',
  name: '库存管理',
  description: '商品库存、出入库记录和库存预警',
  icon: '📦',
  color: '#06B6D4',
  category: '库存管理',
  tables: [
    {
      id: 'products',
      name: '商品',
      order: 0,
      fields: [
        { id: 'inv-name', name: '商品名称', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'inv-sku', name: 'SKU', type: 'text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'inv-category', name: '分类', type: 'single_select', options: { options: selectOptions(['电子产品', '服装', '食品', '家居', '办公用品']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'inv-stock', name: '当前库存', type: 'number', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'inv-min-stock', name: '最低库存', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'inv-price', name: '单价', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'inv-alert', name: '启用预警', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'inv-images', name: '商品图片', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'inv-location', name: '存放位置', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'inv-supplier', name: '供应商', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'inv-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'inv-view-2', name: '按分类查看', type: 'kanban', config: { groupFieldId: 'inv-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'inv-view-3', name: '商品画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'inv-rec-1', values: { 'inv-name': '无线鼠标', 'inv-sku': 'MOUSE-001', 'inv-category': '电子产品', 'inv-stock': 150, 'inv-min-stock': 20, 'inv-price': 99, 'inv-alert': true, 'inv-location': 'A架-3层', 'inv-supplier': '科技公司A' } },
        { id: 'inv-rec-2', values: { 'inv-name': '笔记本', 'inv-sku': 'NOTE-001', 'inv-category': '办公用品', 'inv-stock': 25, 'inv-min-stock': 50, 'inv-price': 15, 'inv-alert': true, 'inv-location': 'B架-1层', 'inv-supplier': '文具厂B' } },
        { id: 'inv-rec-3', values: { 'inv-name': '机械键盘', 'inv-sku': 'KEYB-001', 'inv-category': '电子产品', 'inv-stock': 80, 'inv-min-stock': 15, 'inv-price': 399, 'inv-alert': true, 'inv-location': 'A架-2层', 'inv-supplier': '科技公司A' } },
        { id: 'inv-rec-4', values: { 'inv-name': '办公桌', 'inv-sku': 'DESK-001', 'inv-category': '家居', 'inv-stock': 10, 'inv-min-stock': 5, 'inv-price': 899, 'inv-alert': false, 'inv-location': 'C区', 'inv-supplier': '家具厂C' } },
        { id: 'inv-rec-5', values: { 'inv-name': '咖啡', 'inv-sku': 'COFF-001', 'inv-category': '食品', 'inv-stock': 200, 'inv-min-stock': 30, 'inv-price': 35, 'inv-alert': true, 'inv-location': '茶水间', 'inv-supplier': '食品商D' } },
        { id: 'inv-rec-6', values: { 'inv-name': 'T恤', 'inv-sku': 'TSHI-001', 'inv-category': '服装', 'inv-stock': 0, 'inv-min-stock': 10, 'inv-price': 129, 'inv-alert': true, 'inv-location': 'D架', 'inv-supplier': '服装厂E' } }
      ]
    }
  ]
};

// ==================== 7. 考勤记录模板 ====================
const attendanceRecordTemplate: TableTemplate = {
  id: 'attendance-record',
  name: '考勤记录',
  description: '员工考勤、请假和加班记录管理',
  icon: '⏰',
  color: '#84CC16',
  category: '人事管理',
  tables: [
    {
      id: 'attendance',
      name: '考勤',
      order: 0,
      fields: [
        { id: 'att-date', name: '日期', type: 'date', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'att-employee', name: '员工', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'att-type', name: '类型', type: 'single_select', options: { options: selectOptions(['正常', '迟到', '早退', '请假', '加班', '旷工']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'att-check-in', name: '签到时间', type: 'date', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'att-check-out', name: '签退时间', type: 'date', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'att-hours', name: '工作时长', type: 'number', options: { precision: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'att-is-repair', name: '补卡', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'att-proof', name: '证明材料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'att-remark', name: '备注', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'att-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'att-view-2', name: '日历视图', type: 'calendar', config: { dateFieldId: 'att-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'att-view-3', name: '按类型分组', type: 'kanban', config: { groupFieldId: 'att-type' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'att-rec-1', values: { 'att-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'att-type': '正常', 'att-hours': 8, 'att-is-repair': false } },
        { id: 'att-rec-2', values: { 'att-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'att-type': '迟到', 'att-hours': 7.5, 'att-remark': '交通拥堵', 'att-is-repair': false } },
        { id: 'att-rec-3', values: { 'att-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'att-type': '请假', 'att-hours': 0, 'att-remark': '病假', 'att-is-repair': false } },
        { id: 'att-rec-4', values: { 'att-date': Date.now() - 4 * 24 * 60 * 60 * 1000, 'att-type': '加班', 'att-hours': 11, 'att-remark': '项目上线', 'att-is-repair': false } },
        { id: 'att-rec-5', values: { 'att-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'att-type': '正常', 'att-hours': 8, 'att-is-repair': true, 'att-remark': '忘打卡，已补卡' } },
        { id: 'att-rec-6', values: { 'att-date': Date.now() - 6 * 24 * 60 * 60 * 1000, 'att-type': '早退', 'att-hours': 6, 'att-remark': '家中有事', 'att-is-repair': false } }
      ]
    }
  ]
};

// ==================== 8. 预算管理模板 ====================
const budgetManagementTemplate: TableTemplate = {
  id: 'budget-management',
  name: '预算管理',
  description: '收入支出记录、预算规划和财务分析',
  icon: '💰',
  color: '#EF4444',
  category: '财务管理',
  tables: [
    {
      id: 'transactions',
      name: '收支记录',
      order: 0,
      fields: [
        { id: 'bud-date', name: '日期', type: 'date', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'bud-type', name: '类型', type: 'single_select', options: { options: selectOptions(['收入', '支出']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'bud-category', name: '分类', type: 'single_select', options: { options: selectOptions(['工资', '餐饮', '交通', '购物', '娱乐', '医疗', '教育', '投资', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'bud-amount', name: '金额', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'bud-description', name: '说明', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'bud-payment', name: '支付方式', type: 'single_select', options: { options: selectOptions(['现金', '微信', '支付宝', '银行卡', '信用卡']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'bud-is-reimbursed', name: '已报销', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'bud-invoice', name: '发票凭证', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'bud-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 8 }
      ],
      views: [
        { id: 'bud-view-2', name: '按类型分组', type: 'kanban', config: { groupFieldId: 'bud-type' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'bud-view-3', name: '日历视图', type: 'calendar', config: { dateFieldId: 'bud-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'bud-rec-1', values: { 'bud-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'bud-type': '收入', 'bud-category': '工资', 'bud-amount': 15000, 'bud-payment': '银行卡', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-2', values: { 'bud-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '餐饮', 'bud-amount': 85, 'bud-description': '午餐', 'bud-payment': '微信', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-3', values: { 'bud-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '交通', 'bud-amount': 30, 'bud-payment': '支付宝', 'bud-is-reimbursed': true } },
        { id: 'bud-rec-4', values: { 'bud-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '购物', 'bud-amount': 299, 'bud-description': '办公用品', 'bud-payment': '信用卡', 'bud-is-reimbursed': true } },
        { id: 'bud-rec-5', values: { 'bud-date': Date.now() - 7 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '娱乐', 'bud-amount': 120, 'bud-description': '电影票', 'bud-payment': '微信', 'bud-is-reimbursed': false } },
        { id: 'bud-rec-6', values: { 'bud-date': Date.now() - 10 * 24 * 60 * 60 * 1000, 'bud-type': '收入', 'bud-category': '投资', 'bud-amount': 500, 'bud-description': '理财收益', 'bud-payment': '银行卡', 'bud-is-reimbursed': false } }
      ]
    }
  ]
};

// ==================== 9. 调查反馈模板 ====================
const surveyFeedbackTemplate: TableTemplate = {
  id: 'survey-feedback',
  name: '调查反馈',
  description: '用户调查、反馈收集和满意度分析',
  icon: '📝',
  color: '#6366F1',
  category: '用户研究',
  tables: [
    {
      id: 'responses',
      name: '反馈记录',
      order: 0,
      fields: [
        { id: 'sur-id', name: '反馈编号', type: 'auto_number', options: { prefix: 'FB-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'sur-submit-time', name: '提交时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 1 },
        { id: 'sur-satisfaction', name: '满意度', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'sur-category', name: '反馈类型', type: 'single_select', options: { options: selectOptions(['功能建议', 'Bug报告', '使用问题', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'sur-content', name: '反馈内容', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'sur-contact', name: '联系方式', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'sur-status', name: '处理状态', type: 'single_select', options: { options: selectOptions(['待处理', '处理中', '已解决', '已关闭']) }, isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'sur-need-follow', name: '需要回访', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'sur-screenshot', name: '截图', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'sur-assignee', name: '处理人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'sur-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'sur-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'sur-view-3', name: '收集表单', type: 'form', config: { title: '用户反馈收集', description: '请填写您的宝贵意见', submitButtonText: '提交反馈', successMessage: '感谢您的反馈！' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'sur-view-4', name: '反馈画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'sur-rec-1', values: { 'sur-satisfaction': 4, 'sur-category': '功能建议', 'sur-content': '希望能添加导出功能', 'sur-status': '处理中', 'sur-need-follow': false, 'sur-contact': 'user1@example.com' } },
        { id: 'sur-rec-2', values: { 'sur-satisfaction': 5, 'sur-category': '其他', 'sur-content': '产品很好用！', 'sur-status': '已关闭', 'sur-need-follow': false } },
        { id: 'sur-rec-3', values: { 'sur-satisfaction': 2, 'sur-category': 'Bug报告', 'sur-content': '保存时偶尔会报错', 'sur-status': '待处理', 'sur-need-follow': true, 'sur-contact': '13800138001' } },
        { id: 'sur-rec-4', values: { 'sur-satisfaction': 3, 'sur-category': '使用问题', 'sur-content': '不知道如何创建视图', 'sur-status': '已解决', 'sur-need-follow': false, 'sur-contact': 'user2@example.com' } },
        { id: 'sur-rec-5', values: { 'sur-satisfaction': 5, 'sur-category': '功能建议', 'sur-content': '建议增加暗黑模式', 'sur-status': '处理中', 'sur-need-follow': false } },
        { id: 'sur-rec-6', values: { 'sur-satisfaction': 1, 'sur-category': 'Bug报告', 'sur-content': '登录后页面空白', 'sur-status': '处理中', 'sur-need-follow': true, 'sur-contact': '13900139002' } }
      ]
    }
  ]
};

// ==================== 10. 通讯录模板 ====================
const contactListTemplate: TableTemplate = {
  id: 'contact-list',
  name: '通讯录',
  description: '联系人信息管理，支持分组和标签',
  icon: '📇',
  color: '#14B8A6',
  category: '个人管理',
  tables: [
    {
      id: 'contacts',
      name: '联系人',
      order: 0,
      fields: [
        { id: 'con-name', name: '姓名', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'con-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'con-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'con-company', name: '公司', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'con-position', name: '职位', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'con-group', name: '分组', type: 'single_select', options: { options: selectOptions(['家人', '朋友', '同事', '客户', '其他']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'con-address', name: '地址', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'con-birthday', name: '生日', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'con-avatar', name: '头像', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'con-favorite', name: '收藏', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'con-notes', name: '备注', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'con-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'con-view-2', name: '按分组', type: 'kanban', config: { groupFieldId: 'con-group' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'con-view-3', name: '头像画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'con-view-4', name: '生日日历', type: 'calendar', config: { dateFieldId: 'con-birthday' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'con-rec-1', values: { 'con-name': '张三', 'con-phone': '13800138001', 'con-email': 'zhangsan@example.com', 'con-company': '科技公司', 'con-position': '产品经理', 'con-group': '同事', 'con-favorite': true } },
        { id: 'con-rec-2', values: { 'con-name': '李四', 'con-phone': '13900139002', 'con-group': '朋友', 'con-birthday': Date.now() - 30 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': false } },
        { id: 'con-rec-3', values: { 'con-name': '王五', 'con-phone': '13700137003', 'con-email': 'wangwu@example.com', 'con-company': '贸易公司', 'con-position': '销售总监', 'con-group': '客户', 'con-favorite': true } },
        { id: 'con-rec-4', values: { 'con-name': '赵六', 'con-phone': '13600136004', 'con-group': '家人', 'con-birthday': Date.now() - 25 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': true } },
        { id: 'con-rec-5', values: { 'con-name': '钱七', 'con-phone': '13500135005', 'con-email': 'qianqi@example.com', 'con-company': '咨询公司', 'con-position': '顾问', 'con-group': '其他', 'con-favorite': false } },
        { id: 'con-rec-6', values: { 'con-name': '孙八', 'con-phone': '13300133006', 'con-company': '金融机构', 'con-position': '分析师', 'con-group': '同事', 'con-favorite': false } }
      ]
    }
  ]
};

export const tableTemplates: TableTemplate[] = [
  projectManagementTemplate,
  taskTrackingTemplate,
  customerManagementTemplate,
  productRequirementsTemplate,
  contentCalendarTemplate,
  inventoryManagementTemplate,
  attendanceRecordTemplate,
  budgetManagementTemplate,
  surveyFeedbackTemplate,
  contactListTemplate
];

// 类型已在文件顶部导出，无需重复导出

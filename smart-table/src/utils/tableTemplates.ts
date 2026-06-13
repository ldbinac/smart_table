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
        { id: 'proj-name', name: '项目名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'proj-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['规划中', '进行中', '已完成', '已暂停', '已取消']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'proj-start', name: '开始日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'proj-end', name: '结束日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'proj-owner', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'proj-priority', name: '优先级', type: 'single_select', options: { choices: selectOptions(['高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'proj-progress', name: '进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'proj-budget', name: '预算', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'proj-docs', name: '项目文档', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'proj-desc', name: '描述', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
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
        { id: 'task-name', name: '任务名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'task-project', name: '所属项目', type: 'link', options: { linkedTableId: 'projects', relationshipType: 'many_to_one' }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'task-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['待办', '进行中', '已完成', '已阻塞']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'task-assignee', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'task-due', name: '截止日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'task-priority', name: '优先级', type: 'single_select', options: { choices: selectOptions(['紧急', '高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
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
        { id: 'tt-title', name: '任务标题', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'tt-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['待办', '进行中', '已完成', '已取消']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'tt-priority', name: '优先级', type: 'single_select', options: { choices: selectOptions(['紧急', '高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'tt-due', name: '截止日期', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'tt-assignee', name: '负责人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'tt-tags', name: '标签', type: 'multi_select', options: { choices: selectOptions(['工作', '个人', '学习', '生活']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'tt-importance', name: '重要程度', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'tt-attachments', name: '附件', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'tt-notes', name: '备注', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
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
        { id: 'cust-name', name: '客户名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cust-contact', name: '联系人', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cust-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cust-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'cust-website', name: '官网', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cust-stage', name: '阶段', type: 'single_select', options: { choices: selectOptions(['潜在客户', '意向客户', '跟进中', '成交客户', '流失客户']) }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cust-source', name: '来源', type: 'single_select', options: { choices: selectOptions(['线上广告', '朋友推荐', '展会', '电话营销', '自然搜索']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cust-value', name: '预估价值', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'cust-rating', name: '客户评级', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'cust-docs', name: '客户资料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'cust-address', name: '地址', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'cust-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'cust-view-2', name: '按阶段分组', type: 'kanban', config: { groupFieldId: 'cust-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'cust-view-3', name: '客户画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'cust-rec-1', values: { 'cust-name': '科技公司A', 'cust-contact': '张经理', 'cust-phone': '13800138001', 'cust-email': 'ldengbin@126.com', 'cust-website': 'https://github.com/ldbinac/smart_table', 'cust-stage': '跟进中', 'cust-source': '线上广告', 'cust-value': 50000, 'cust-rating': 4 } },
        { id: 'cust-rec-2', values: { 'cust-name': '贸易公司B', 'cust-contact': '李总', 'cust-phone': '13900139002', 'cust-email': 'binac@live.cn', 'cust-stage': '成交客户', 'cust-source': '朋友推荐', 'cust-value': 120000, 'cust-rating': 5 } },
        { id: 'cust-rec-3', values: { 'cust-name': '咨询机构C', 'cust-contact': '王总监', 'cust-phone': '13700137003', 'cust-stage': '意向客户', 'cust-source': '展会', 'cust-value': 80000, 'cust-rating': 3 } },
        { id: 'cust-rec-4', values: { 'cust-name': '制造企业D', 'cust-contact': '赵经理', 'cust-phone': '13600136004', 'cust-email': 'ldengbin@126.com', 'cust-website': 'https://gitee.com/binac/smart_table', 'cust-stage': '潜在客户', 'cust-source': '自然搜索', 'cust-value': 200000, 'cust-rating': 4 } },
        { id: 'cust-rec-5', values: { 'cust-name': '零售连锁E', 'cust-contact': '陈店长', 'cust-phone': '13500135005', 'cust-stage': '流失客户', 'cust-source': '电话营销', 'cust-value': 30000, 'cust-rating': 2 } },
        { id: 'cust-rec-6', values: { 'cust-name': '金融公司F', 'cust-contact': '刘总监', 'cust-phone': '13300133006', 'cust-email': 'binac@live.cn', 'cust-website': 'https://www.zhihu.com/people/lu-dong-bin-19', 'cust-stage': '成交客户', 'cust-source': '朋友推荐', 'cust-value': 500000, 'cust-rating': 5 } }
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
        { id: 'pr-title', name: '需求标题', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'pr-type', name: '类型', type: 'single_select', options: { choices: selectOptions(['新功能', '优化', 'Bug修复', '技术债务']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'pr-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['待评估', '规划中', '开发中', '测试中', '已上线', '已拒绝']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'pr-priority', name: '优先级', type: 'single_select', options: { choices: selectOptions(['P0-紧急', 'P1-高', 'P2-中', 'P3-低']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'pr-effort', name: '工作量', type: 'number', options: { suffix: '人天' }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'pr-start', name: '计划开始', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'pr-end', name: '计划结束', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'pr-progress', name: '进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'pr-reviewer', name: '评审人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'pr-needs-review', name: '需要评审', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'pr-docs', name: '需求文档', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'pr-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'pr-description', name: '详细描述', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 13 }
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
        { id: 'cc-title', name: '内容标题', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'cc-type', name: '内容类型', type: 'single_select', options: { choices: selectOptions(['博客', '视频', '社交媒体', '邮件', '播客']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'cc-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['想法', '草稿', '审核中', '已排期', '已发布']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'cc-publish-date', name: '发布日期', type: 'date', options: { includeTime: true }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'cc-platform', name: '发布平台', type: 'multi_select', options: { choices: selectOptions(['微信公众号', '微博', '知乎', 'B站', '小红书', '抖音']) }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'cc-author', name: '作者', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'cc-tags', name: '标签', type: 'multi_select', options: { choices: selectOptions(['技术', '产品', '运营', '案例', '教程']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
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
        { id: 'inv-name', name: '商品名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'inv-sku', name: 'SKU', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'inv-category', name: '分类', type: 'single_select', options: { choices: selectOptions(['电子产品', '服装', '食品', '家居', '办公用品']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'inv-stock', name: '当前库存', type: 'number', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'inv-min-stock', name: '最低库存', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'inv-price', name: '单价', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'inv-alert', name: '启用预警', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'inv-images', name: '商品图片', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'inv-location', name: '存放位置', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'inv-supplier', name: '供应商', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
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
        { id: 'att-type', name: '类型', type: 'single_select', options: { choices: selectOptions(['正常', '迟到', '早退', '请假', '加班', '旷工']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'att-check-in', name: '签到时间', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'att-check-out', name: '签退时间', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'att-hours', name: '工作时长', type: 'number', options: { precision: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'att-is-repair', name: '补卡', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'att-proof', name: '证明材料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'att-remark', name: '备注', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
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
        { id: 'bud-type', name: '类型', type: 'single_select', options: { choices: selectOptions(['收入', '支出']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'bud-category', name: '分类', type: 'single_select', options: { choices: selectOptions(['工资', '餐饮', '交通', '购物', '娱乐', '医疗', '教育', '投资', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'bud-amount', name: '金额', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'bud-description', name: '说明', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'bud-payment', name: '支付方式', type: 'single_select', options: { choices: selectOptions(['现金', '微信', '支付宝', '银行卡', '信用卡']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
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
        { id: 'sur-category', name: '反馈类型', type: 'single_select', options: { choices: selectOptions(['功能建议', 'Bug报告', '使用问题', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'sur-content', name: '反馈内容', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'sur-contact', name: '联系方式', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'sur-status', name: '处理状态', type: 'single_select', options: { choices: selectOptions(['待处理', '处理中', '已解决', '已关闭']) }, isPrimary: false, isRequired: true, isVisible: true, order: 6 },
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
        { id: 'sur-rec-1', values: { 'sur-satisfaction': 4, 'sur-category': '功能建议', 'sur-content': '希望能添加导出功能', 'sur-status': '处理中', 'sur-need-follow': false, 'sur-contact': 'binac@live.cn' } },
        { id: 'sur-rec-2', values: { 'sur-satisfaction': 5, 'sur-category': '其他', 'sur-content': '产品很好用！', 'sur-status': '已关闭', 'sur-need-follow': false } },
        { id: 'sur-rec-3', values: { 'sur-satisfaction': 2, 'sur-category': 'Bug报告', 'sur-content': '保存时偶尔会报错', 'sur-status': '待处理', 'sur-need-follow': true, 'sur-contact': '13800138001' } },
        { id: 'sur-rec-4', values: { 'sur-satisfaction': 3, 'sur-category': '使用问题', 'sur-content': '不知道如何创建视图', 'sur-status': '已解决', 'sur-need-follow': false, 'sur-contact': 'ldengbin@126.cn' } },
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
        { id: 'con-name', name: '姓名', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'con-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'con-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'con-company', name: '公司', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'con-position', name: '职位', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'con-group', name: '分组', type: 'single_select', options: { choices: selectOptions(['家人', '朋友', '同事', '客户', '其他']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'con-address', name: '地址', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'con-birthday', name: '生日', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'con-avatar', name: '头像', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'con-favorite', name: '收藏', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'con-notes', name: '备注', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'con-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'con-view-2', name: '按分组', type: 'kanban', config: { groupFieldId: 'con-group' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'con-view-3', name: '头像画廊', type: 'gallery', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'con-view-4', name: '生日日历', type: 'calendar', config: { dateFieldId: 'con-birthday' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'con-rec-1', values: { 'con-name': '张三', 'con-phone': '13800138001', 'con-email': 'ldengbin@126.com', 'con-company': '科技公司', 'con-position': '产品经理', 'con-group': '同事', 'con-favorite': true } },
        { id: 'con-rec-2', values: { 'con-name': '李四', 'con-phone': '13900139002', 'con-group': '朋友', 'con-birthday': Date.now() - 30 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': false } },
        { id: 'con-rec-3', values: { 'con-name': '王五', 'con-phone': '13700137003', 'con-email': 'binac@live.cn', 'con-company': '贸易公司', 'con-position': '销售总监', 'con-group': '客户', 'con-favorite': true } },
        { id: 'con-rec-4', values: { 'con-name': '赵六', 'con-phone': '13600136004', 'con-group': '家人', 'con-birthday': Date.now() - 25 * 365 * 24 * 60 * 60 * 1000, 'con-favorite': true } },
        { id: 'con-rec-5', values: { 'con-name': '钱七', 'con-phone': '13500135005', 'con-email': 'ldengbin@126.cn', 'con-company': '咨询公司', 'con-position': '顾问', 'con-group': '其他', 'con-favorite': false } },
        { id: 'con-rec-6', values: { 'con-name': '孙八', 'con-phone': '13300133006', 'con-company': '金融机构', 'con-position': '分析师', 'con-group': '同事', 'con-favorite': false } }
      ]
    }
  ]
};

// ==================== 11. 会议管理模板 ====================
const meetingManagementTemplate: TableTemplate = {
  id: 'meeting-management',
  name: '会议管理',
  description: '会议记录、参会人员和会议纪要管理',
  icon: '🎯',
  color: '#7C3AED',
  category: '团队协作',
  tables: [
    {
      id: 'meetings',
      name: '会议',
      order: 0,
      fields: [
        { id: 'meet-title', name: '会议主题', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'meet-type', name: '会议类型', type: 'single_select', options: { choices: selectOptions(['例会', '项目会议', '评审会议', '培训', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'meet-date', name: '会议时间', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'meet-duration', name: '时长(分钟)', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'meet-location', name: '会议地点', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'meet-host', name: '主持人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'meet-attendees', name: '参会人员', type: 'member', options: { multiple: true }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'meet-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['待召开', '进行中', '已结束', '已取消']) }, isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'meet-agenda', name: '会议议程', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'meet-minutes', name: '会议纪要', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'meet-attachments', name: '会议材料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'meet-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 11 }
      ],
      views: [
        { id: 'meet-view-1', name: '会议列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'meet-view-2', name: '日历视图', type: 'calendar', config: { dateFieldId: 'meet-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'meet-view-3', name: '按状态分组', type: 'kanban', config: { groupFieldId: 'meet-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'meet-rec-1', values: { 'meet-title': '周例会', 'meet-type': '例会', 'meet-date': Date.now() + 1 * 24 * 60 * 60 * 1000, 'meet-duration': 60, 'meet-location': '会议室A', 'meet-status': '待召开', 'meet-agenda': '1.上周工作总结\n2.本周工作计划\n3.问题讨论' } },
        { id: 'meet-rec-2', values: { 'meet-title': '产品评审会', 'meet-type': '评审会议', 'meet-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'meet-duration': 90, 'meet-location': '线上会议', 'meet-status': '已结束', 'meet-minutes': '评审通过，下周开始开发' } },
        { id: 'meet-rec-3', values: { 'meet-title': '技术分享会', 'meet-type': '培训', 'meet-date': Date.now() + 3 * 24 * 60 * 60 * 1000, 'meet-duration': 120, 'meet-location': '培训室', 'meet-status': '待召开', 'meet-agenda': 'Vue3新特性分享' } },
        { id: 'meet-rec-4', values: { 'meet-title': '项目启动会', 'meet-type': '项目会议', 'meet-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'meet-duration': 60, 'meet-location': '会议室B', 'meet-status': '已结束', 'meet-minutes': '确定项目里程碑和分工' } },
        { id: 'meet-rec-5', values: { 'meet-title': '需求讨论', 'meet-type': '项目会议', 'meet-date': Date.now(), 'meet-duration': 45, 'meet-location': '线上会议', 'meet-status': '进行中' } },
        { id: 'meet-rec-6', values: { 'meet-title': '部门聚餐', 'meet-type': '其他', 'meet-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'meet-status': '已取消', 'meet-duration': 180 } }
      ]
    }
  ]
};

// ==================== 12. 学习计划模板 ====================
const learningPlanTemplate: TableTemplate = {
  id: 'learning-plan',
  name: '学习计划',
  description: '课程学习、进度跟踪和知识管理',
  icon: '📚',
  color: '#059669',
  category: '个人管理',
  tables: [
    {
      id: 'courses',
      name: '课程',
      order: 0,
      fields: [
        { id: 'learn-title', name: '课程名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'learn-category', name: '分类', type: 'single_select', options: { choices: selectOptions(['编程开发', '产品设计', '数据分析', '语言学习', '职业技能', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'learn-platform', name: '学习平台', type: 'single_select', options: { choices: selectOptions(['Coursera', 'Udemy', 'B站', '慕课网', '极客时间', '自学']) }, isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'learn-status', name: '学习状态', type: 'single_select', options: { choices: selectOptions(['未开始', '学习中', '已完成', '已暂停']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'learn-progress', name: '学习进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'learn-start', name: '开始日期', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'learn-end', name: '目标完成', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'learn-hours', name: '已学时长', type: 'number', options: { suffix: '小时' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'learn-rating', name: '课程评分', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'learn-url', name: '课程链接', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'learn-notes', name: '学习笔记', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'learn-resources', name: '学习资料', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'learn-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 }
      ],
      views: [
        { id: 'learn-view-1', name: '课程列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'learn-view-2', name: '学习看板', type: 'kanban', config: { groupFieldId: 'learn-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'learn-view-3', name: '按分类', type: 'kanban', config: { groupFieldId: 'learn-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'learn-rec-1', values: { 'learn-title': 'Vue3从入门到精通', 'learn-category': '编程开发', 'learn-platform': 'B站', 'learn-status': '学习中', 'learn-progress': 65, 'learn-start': Date.now() - 14 * 24 * 60 * 60 * 1000, 'learn-hours': 20, 'learn-rating': 5 } },
        { id: 'learn-rec-2', values: { 'learn-title': 'Python数据分析', 'learn-category': '数据分析', 'learn-platform': 'Coursera', 'learn-status': '已完成', 'learn-progress': 100, 'learn-hours': 40, 'learn-rating': 4 } },
        { id: 'learn-rec-3', values: { 'learn-title': '英语口语提升', 'learn-category': '语言学习', 'learn-platform': '自学', 'learn-status': '学习中', 'learn-progress': 30, 'learn-hours': 15, 'learn-rating': 3 } },
        { id: 'learn-rec-4', values: { 'learn-title': '产品经理实战课', 'learn-category': '产品设计', 'learn-platform': '极客时间', 'learn-status': '未开始', 'learn-progress': 0, 'learn-rating': 0 } },
        { id: 'learn-rec-5', values: { 'learn-title': 'TypeScript高级教程', 'learn-category': '编程开发', 'learn-platform': '慕课网', 'learn-status': '已暂停', 'learn-progress': 45, 'learn-hours': 12, 'learn-rating': 4 } },
        { id: 'learn-rec-6', values: { 'learn-title': '职场沟通技巧', 'learn-category': '职业技能', 'learn-platform': 'Udemy', 'learn-status': '学习中', 'learn-progress': 80, 'learn-hours': 8, 'learn-rating': 4 } }
      ]
    }
  ]
};

// ==================== 13. 招聘管理模板 ====================
const recruitmentTemplate: TableTemplate = {
  id: 'recruitment',
  name: '招聘管理',
  description: '职位发布、候选人管理和面试流程跟踪',
  icon: '👔',
  color: '#DC2626',
  category: '人事管理',
  tables: [
    {
      id: 'candidates',
      name: '候选人',
      order: 0,
      fields: [
        { id: 'rec-name', name: '姓名', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'rec-position', name: '应聘职位', type: 'single_select', options: { choices: selectOptions(['前端开发', '后端开发', '产品经理', 'UI设计师', '测试工程师', '运营专员']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'rec-stage', name: '面试阶段', type: 'single_select', options: { choices: selectOptions(['简历筛选', '初试', '复试', '终试', '已录用', '已淘汰']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'rec-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'rec-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'rec-source', name: '来源', type: 'single_select', options: { choices: selectOptions(['智联招聘', '前程无忧', 'BOSS直聘', '猎头推荐', '内推', '官网投递']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'rec-experience', name: '工作经验', type: 'number', options: { suffix: '年' }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'rec-expected-salary', name: '期望薪资', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'rec-interview-date', name: '面试时间', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'rec-interviewer', name: '面试官', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'rec-rating', name: '综合评分', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'rec-resume', name: '简历', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'rec-feedback', name: '面试反馈', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'rec-created', name: '投递时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 13 }
      ],
      views: [
        { id: 'rec-view-1', name: '候选人列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'rec-view-2', name: '面试看板', type: 'kanban', config: { groupFieldId: 'rec-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'rec-view-3', name: '面试日历', type: 'calendar', config: { dateFieldId: 'rec-interview-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'rec-rec-1', values: { 'rec-name': '张小明', 'rec-position': '前端开发', 'rec-stage': '复试', 'rec-phone': '13800138001', 'rec-email': 'ldengbin@126.cn', 'rec-source': 'BOSS直聘', 'rec-experience': 3, 'rec-expected-salary': 18000, 'rec-rating': 4 } },
        { id: 'rec-rec-2', values: { 'rec-name': '李小红', 'rec-position': '产品经理', 'rec-stage': '已录用', 'rec-phone': '13900139002', 'rec-source': '内推', 'rec-experience': 5, 'rec-expected-salary': 25000, 'rec-rating': 5 } },
        { id: 'rec-rec-3', values: { 'rec-name': '王小华', 'rec-position': 'UI设计师', 'rec-stage': '初试', 'rec-phone': '13700137003', 'rec-source': '前程无忧', 'rec-experience': 2, 'rec-expected-salary': 12000, 'rec-rating': 3 } },
        { id: 'rec-rec-4', values: { 'rec-name': '赵小龙', 'rec-position': '后端开发', 'rec-stage': '已淘汰', 'rec-phone': '13600136004', 'rec-source': '智联招聘', 'rec-experience': 1, 'rec-rating': 2, 'rec-feedback': '技术能力不足' } },
        { id: 'rec-rec-5', values: { 'rec-name': '钱小芳', 'rec-position': '测试工程师', 'rec-stage': '终试', 'rec-phone': '13500135005', 'rec-source': '猎头推荐', 'rec-experience': 4, 'rec-expected-salary': 15000, 'rec-rating': 4 } },
        { id: 'rec-rec-6', values: { 'rec-name': '孙小强', 'rec-position': '运营专员', 'rec-stage': '简历筛选', 'rec-phone': '13300133006', 'rec-source': '官网投递', 'rec-experience': 2, 'rec-expected-salary': 10000 } }
      ]
    }
  ]
};

// ==================== 14. 资产管理模板 ====================
const assetManagementTemplate: TableTemplate = {
  id: 'asset-management',
  name: '资产管理',
  description: '固定资产、设备领用和资产盘点管理',
  icon: '🖥️',
  color: '#0891B2',
  category: '行政管理',
  tables: [
    {
      id: 'assets',
      name: '资产',
      order: 0,
      fields: [
        { id: 'asset-code', name: '资产编号', type: 'auto_number', options: { prefix: 'AS-', startNumber: 10001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'asset-name', name: '资产名称', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'asset-category', name: '资产类别', type: 'single_select', options: { choices: selectOptions(['电脑设备', '办公家具', '电子设备', '交通工具', '其他']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'asset-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['在用', '闲置', '维修中', '已报废', '已丢失']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'asset-user', name: '使用人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'asset-department', name: '所属部门', type: 'single_select', options: { choices: selectOptions(['研发部', '产品部', '运营部', '市场部', '人事部', '财务部']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'asset-purchase-date', name: '购买日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'asset-price', name: '购买价格', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'asset-location', name: '存放位置', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'asset-warranty', name: '保修期至', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'asset-image', name: '资产照片', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'asset-remark', name: '备注', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'asset-created', name: '入库时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 12 }
      ],
      views: [
        { id: 'asset-view-1', name: '资产列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'asset-view-2', name: '按状态分组', type: 'kanban', config: { groupFieldId: 'asset-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'asset-view-3', name: '按类别分组', type: 'kanban', config: { groupFieldId: 'asset-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'asset-rec-1', values: { 'asset-name': 'MacBook Pro 14寸', 'asset-category': '电脑设备', 'asset-status': '在用', 'asset-department': '研发部', 'asset-purchase-date': Date.now() - 180 * 24 * 60 * 60 * 1000, 'asset-price': 14999, 'asset-location': '工位A01', 'asset-warranty': Date.now() + 545 * 24 * 60 * 60 * 1000 } },
        { id: 'asset-rec-2', values: { 'asset-name': '人体工学椅', 'asset-category': '办公家具', 'asset-status': '在用', 'asset-department': '产品部', 'asset-purchase-date': Date.now() - 365 * 24 * 60 * 60 * 1000, 'asset-price': 1999, 'asset-location': '工位B02' } },
        { id: 'asset-rec-3', values: { 'asset-name': '投影仪', 'asset-category': '电子设备', 'asset-status': '闲置', 'asset-purchase-date': Date.now() - 500 * 24 * 60 * 60 * 1000, 'asset-price': 5999, 'asset-location': '会议室A' } },
        { id: 'asset-rec-4', values: { 'asset-name': 'iPhone 15 Pro', 'asset-category': '电子设备', 'asset-status': '维修中', 'asset-department': '运营部', 'asset-purchase-date': Date.now() - 90 * 24 * 60 * 60 * 1000, 'asset-price': 8999, 'asset-remark': '屏幕损坏维修中' } },
        { id: 'asset-rec-5', values: { 'asset-name': '台式电脑', 'asset-category': '电脑设备', 'asset-status': '已报废', 'asset-department': '市场部', 'asset-purchase-date': Date.now() - 1000 * 24 * 60 * 60 * 1000, 'asset-price': 4500, 'asset-remark': '已使用5年，性能不足' } },
        { id: 'asset-rec-6', values: { 'asset-name': '公司车辆-粤A12345', 'asset-category': '交通工具', 'asset-status': '在用', 'asset-department': '人事部', 'asset-purchase-date': Date.now() - 300 * 24 * 60 * 60 * 1000, 'asset-price': 180000 } }
      ]
    }
  ]
};

// ==================== 15. Bug跟踪模板 ====================
const bugTrackingTemplate: TableTemplate = {
  id: 'bug-tracking',
  name: 'Bug跟踪',
  description: '软件缺陷记录、优先级管理和修复进度跟踪',
  icon: '🐛',
  color: '#BE185D',
  category: '研发管理',
  tables: [
    {
      id: 'bugs',
      name: '缺陷',
      order: 0,
      fields: [
        { id: 'bug-id', name: '缺陷编号', type: 'auto_number', options: { prefix: 'BUG-', startNumber: 1001 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'bug-title', name: '缺陷标题', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'bug-severity', name: '严重程度', type: 'single_select', options: { choices: selectOptions(['致命', '严重', '一般', '轻微', '建议']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'bug-priority', name: '优先级', type: 'single_select', options: { choices: selectOptions(['P0-紧急', 'P1-高', 'P2-中', 'P3-低']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'bug-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['新建', '确认中', '处理中', '待验证', '已关闭', '重新打开']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'bug-module', name: '所属模块', type: 'single_select', options: { choices: selectOptions(['用户模块', '订单模块', '支付模块', '数据统计', '系统设置', '其他']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'bug-reporter', name: '报告人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'bug-assignee', name: '处理人', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'bug-found-date', name: '发现日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 8 },
        { id: 'bug-fix-date', name: '修复日期', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'bug-environment', name: '环境', type: 'single_select', options: { choices: selectOptions(['生产环境', '测试环境', '开发环境']) }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'bug-description', name: '缺陷描述', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: true, isVisible: true, order: 11 },
        { id: 'bug-steps', name: '复现步骤', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'bug-screenshot', name: '截图', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 13 },
        { id: 'bug-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 14 }
      ],
      views: [
        { id: 'bug-view-1', name: '缺陷列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'bug-view-2', name: '状态看板', type: 'kanban', config: { groupFieldId: 'bug-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'bug-view-3', name: '按严重程度', type: 'kanban', config: { groupFieldId: 'bug-severity' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'bug-rec-1', values: { 'bug-title': '登录页面无法正常加载', 'bug-severity': '致命', 'bug-priority': 'P0-紧急', 'bug-status': '处理中', 'bug-module': '用户模块', 'bug-found-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': '生产环境', 'bug-description': '用户反馈登录页面白屏，无法进行登录操作' } },
        { id: 'bug-rec-2', values: { 'bug-title': '订单列表分页失效', 'bug-severity': '严重', 'bug-priority': 'P1-高', 'bug-status': '待验证', 'bug-module': '订单模块', 'bug-found-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'bug-fix-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': '测试环境' } },
        { id: 'bug-rec-3', values: { 'bug-title': '支付成功后订单状态未更新', 'bug-severity': '严重', 'bug-priority': 'P0-紧急', 'bug-status': '新建', 'bug-module': '支付模块', 'bug-found-date': Date.now(), 'bug-environment': '生产环境' } },
        { id: 'bug-rec-4', values: { 'bug-title': '数据统计图表显示异常', 'bug-severity': '一般', 'bug-priority': 'P2-中', 'bug-status': '已关闭', 'bug-module': '数据统计', 'bug-found-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'bug-fix-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'bug-environment': '测试环境' } },
        { id: 'bug-rec-5', values: { 'bug-title': '设置页面保存按钮无响应', 'bug-severity': '一般', 'bug-priority': 'P2-中', 'bug-status': '确认中', 'bug-module': '系统设置', 'bug-found-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'bug-environment': '测试环境' } },
        { id: 'bug-rec-6', values: { 'bug-title': '建议增加批量导出功能', 'bug-severity': '建议', 'bug-priority': 'P3-低', 'bug-status': '新建', 'bug-module': '其他', 'bug-found-date': Date.now() - 7 * 24 * 60 * 60 * 1000, 'bug-environment': '生产环境' } }
      ]
    }
  ]
};

// ==================== 记录生成器（用于生成测试记录） ====================
const generateTestRecords = (): TemplateRecord[] => {
  const records: TemplateRecord[] = [];
  const singleSelectOptions = ['类型A', '类型B', '类型C', '类型D', '类型E'];
  const multiSelectOptions = ['标签1', '标签2', '标签3', '标签4', '标签5', '标签6'];

  const pickOne = <T>(arr: T[], i: number): T => arr[i % arr.length];
  const pickSome = <T>(arr: T[], i: number): T[] => {
    const count = i % 4;
    return arr.slice(0, count);
  };

  for (let i = 0; i < 100; i++) {
    const batch = Math.floor(i / 100); // 0=正常 1=空值 2=边界 3=特殊字符 4=格式验证
    const idx = i % 100; // 批次内序号
    const values: Record<string, CellValue> = {};

    // ——— 单行文本 ———
    if (batch === 0) {
      values['test-text'] = `测试记录 #${i + 1}`;
    } else if (batch === 1 && idx % 7 === 0) {
      values['test-text'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-text'] = 'A'.repeat(500);
    } else if (batch === 3 && idx % 5 === 0) {
      values['test-text'] = '<script>alert("xss")</script>' + (i + 1);
    } else if (batch === 4 && idx % 8 === 0) {
      values['test-text'] = '  ';
    } else {
      values['test-text'] = `测试记录 #${i + 1}`;
    }

    // ——— 多行文本 ———
    if (batch === 0) {
      values['test-longtext'] = `这是第 ${i + 1} 条记录的多行文本内容。\n包含换行符的第二行。\n第三行结束。`;
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-longtext'] = null;
    } else if (batch === 2 && idx % 11 === 0) {
      values['test-longtext'] = '长文本 '.repeat(200).trim();
    } else if (batch === 3 && idx % 7 === 0) {
      values['test-longtext'] = '特殊字符: \n\t\r\0\\\'"`汉字日本語한국어🚀🎉';
    } else if (batch === 4 && idx % 9 === 0) {
      values['test-longtext'] = '\n\n\n\n';
    } else {
      values['test-longtext'] = `记录 ${i + 1} 的说明内容。`;
    }

    // ——— 富文本 ———
    if (batch === 0) {
      values['test-richtext'] = `<p><b>记录 ${i + 1}</b>：这是富文本内容。</p>`;
    } else if (batch === 1 && idx % 6 === 0) {
      values['test-richtext'] = null;
    } else if (batch === 2 && idx % 8 === 0) {
      values['test-richtext'] = '<div style="font-size:999px">超大字体</div>';
    } else if (batch === 3 && idx % 4 === 0) {
      values['test-richtext'] = '<ul><li>列表项1</li><li>列表项2</li></ul><script>evil()</script>';
    } else if (batch === 4 && idx % 7 === 0) {
      values['test-richtext'] = '<p>🔬🧪🧫🧬🔭📡💻</p>';
    } else {
      values['test-richtext'] = `<p>普通富文本段落 #${i + 1}</p>`;
    }

    // ——— 数字 ———
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

    // ——— 货币 ———
    // if (batch === 0) {
    //   values['test-currency'] = (i + 1) * 100;
    // } else if (batch === 1 && idx % 5 === 0) {
    //   values['test-currency'] = null;
    // } else if (batch === 2 && idx % 11 === 0) {
    //   values['test-currency'] = 0.01;
    // } else if (batch === 3 && idx % 9 === 0) {
    //   values['test-currency'] = 99999999.99;
    // } else if (batch === 4 && idx % 7 === 0) {
    //   values['test-currency'] = -500;
    // } else {
    //   values['test-currency'] = (i + 1) * 50;
    // }

    // ——— 百分比 ———
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

    // ——— 评分 ———
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

    // ——— 时长 ———
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

    // ——— 日期 ———
    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;
    if (batch === 0) {
      values['test-date'] = now + (i - 250) * dayMs;
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-date'] = null;
    } else if (batch === 2 && idx % 7 === 0) {
      // 闰年 2024-02-29
      values['test-date'] = new Date(2024, 1, 29).getTime();
    } else if (batch === 2 && idx % 7 === 1) {
      // 纪元前近似
      values['test-date'] = new Date(1, 0, 1).getTime();
    } else if (batch === 3 && idx % 9 === 0) {
      // 未来 10 年
      values['test-date'] = now + 3650 * dayMs;
    } else if (batch === 4 && idx % 6 === 0) {
      // 月末日 2025-01-31
      values['test-date'] = new Date(2025, 0, 31).getTime();
    } else {
      values['test-date'] = now + (i - 250) * dayMs;
    }

    // ——— 日期时间 ———
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

    // ——— 单选 ———
    if (batch === 0) {
      values['test-singleselect'] = pickOne(singleSelectOptions, i);
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-singleselect'] = null;
    } else if (batch === 2 && idx % 13 === 0) {
      values['test-singleselect'] = '未知选项';
    } else {
      values['test-singleselect'] = pickOne(singleSelectOptions, i + 3);
    }

    // ——— 多选 ———
    if (batch === 0) {
      const selected = pickSome(multiSelectOptions, i);
      values['test-multiselect'] = selected.length > 0 ? selected : null;
    } else if (batch === 1 && idx % 3 === 0) {
      values['test-multiselect'] = null;
    } else if (batch === 2 && idx % 11 === 0) {
      values['test-multiselect'] = [...multiSelectOptions];
    } else if (batch === 3 && idx % 6 === 0) {
      values['test-multiselect'] = ['未知标签'];
    } else {
      const selected = pickSome(multiSelectOptions, i + 2);
      values['test-multiselect'] = selected.length > 0 ? selected : null;
    }

    // ——— 复选框 ———
    if (batch === 0) {
      values['test-checkbox'] = i % 2 === 0;
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-checkbox'] = null;
    } else if (batch === 2 && idx % 7 === 0) {
      values['test-checkbox'] = true;
    } else {
      values['test-checkbox'] = i % 3 === 0;
    }

    // ——— 电话 ———
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

    // ——— 邮箱 ———
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

    // ——— URL ———
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

    // ——— 进度 ———
    // if (batch === 0) {
    //   values['test-progress'] = i % 101;
    // } else if (batch === 1 && idx % 5 === 0) {
    //   values['test-progress'] = null;
    // } else if (batch === 2 && idx % 8 === 0) {
    //   values['test-progress'] = 0;
    // } else if (batch === 2 && idx % 8 === 1) {
    //   values['test-progress'] = 100;
    // } else if (batch === 3 && idx % 9 === 0) {
    //   values['test-progress'] = 50;
    // } else {
    //   values['test-progress'] = (i * 17) % 101;
    // }

    // ——— 成员 ———
    if (batch === 0) {
      values['test-member'] = 'user_' + ((i % 5) + 1);
    } else if (batch === 1 && idx % 5 === 0) {
      values['test-member'] = null;
    } else {
      values['test-member'] = 'user_' + ((i % 3) + 1);
    }

    // ——— 协作者 ———
    if (batch === 0) {
      values['test-collaborator'] = [`user_${(i % 3) + 1}`, `user_${(i % 3) + 2}`];
    } else if (batch === 1 && idx % 4 === 0) {
      values['test-collaborator'] = null;
    } else if (batch === 2 && idx % 9 === 0) {
      values['test-collaborator'] = [`user_1`, `user_2`, `user_3`, `user_4`, `user_5`];
    } else {
      values['test-collaborator'] = [`user_${(i % 2) + 1}`];
    }

    // ——— 附件 ———
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

    // ——— 条形码 ———
    // const barcodes = ['9781234567897', '6901234567890', 'ABC123DEF456', '1234567890123', 'TEST-CODE-001'];
    // if (batch === 0) {
    //   values['test-barcode'] = pickOne(barcodes, i);
    // } else if (batch === 1 && idx % 6 === 0) {
    //   values['test-barcode'] = null;
    // } else if (batch === 2 && idx % 8 === 0) {
    //   values['test-barcode'] = '0'.repeat(50);
    // } else if (batch === 3 && idx % 5 === 0) {
    //   values['test-barcode'] = '!@#$%^&*()';
    // } else {
    //   values['test-barcode'] = pickOne(barcodes, i + 1);
    // }

    // ——— 按钮 ———
    // if (batch === 0) {
    //   values['test-button'] = `操作_${(i % 4) + 1}`;
    // } else if (batch === 1 && idx % 7 === 0) {
    //   values['test-button'] = null;
    // } else if (batch === 2 && idx % 10 === 0) {
    //   values['test-button'] = '点击执行';
    // } else {
    //   values['test-button'] = `按钮_${(i % 3) + 1}`;
    // }

    records.push({
      id: `test-rec-${i}`,
      values,
    });
  }

  return records;
};

// ==================== 17. 全字段类型测试模板 ====================
const fullFieldTypeTestTemplate: TableTemplate = {
  id: 'full-field-type-test',
  name: '全字段类型测试',
  description: '系统覆盖所有可创建字段类型（22种），含500条边界值测试记录，用于验证字段解析准确性和数据处理正确性',
  icon: '🧪',
  color: '#6366F1',
  category: '全字段测试',
  tables: [
    {
      id: 'test-table',
      name: '字段类型验证表',
      description: '包含所有用户可创建字段类型的综合验证表，每条记录覆盖各字段的不同数据形态',
      order: 0,
      fields: [
        { id: 'test-id', name: '记录编号', type: 'auto_number', options: { prefix: 'T-', startNumber: 1 }, isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'test-text', name: '单行文本', type: 'single_line_text', isPrimary: false, isRequired: false, isVisible: true, order: 1 },
        { id: 'test-longtext', name: '多行文本', type: 'long_text', isPrimary: false, isRequired: false, isVisible: true, order: 2 },
        { id: 'test-richtext', name: '富文本', type: 'rich_text', isPrimary: false, isRequired: false, isVisible: true, order: 3 },
        { id: 'test-number', name: '数字', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
       // { id: 'test-currency', name: '货币', type: 'currency', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'test-percent', name: '百分比', type: 'percent', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'test-rating', name: '评分', type: 'rating', options: { maxRating: 5 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'test-duration', name: '时长', type: 'duration', isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'test-date', name: '日期', type: 'date', isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'test-datetime', name: '日期时间', type: 'date_time', options: { includeTime: true }, isPrimary: false, isRequired: false, isVisible: true, order: 10 },
        { id: 'test-singleselect', name: '单选', type: 'single_select', options: { choices: selectOptions(['类型A', '类型B', '类型C', '类型D', '类型E']) }, isPrimary: false, isRequired: false, isVisible: true, order: 11 },
        { id: 'test-multiselect', name: '多选', type: 'multi_select', options: { choices: selectOptions(['标签1', '标签2', '标签3', '标签4', '标签5', '标签6']) }, isPrimary: false, isRequired: false, isVisible: true, order: 12 },
        { id: 'test-checkbox', name: '复选框', type: 'checkbox', isPrimary: false, isRequired: false, isVisible: true, order: 13 },
        { id: 'test-phone', name: '电话', type: 'phone', isPrimary: false, isRequired: false, isVisible: true, order: 14 },
        { id: 'test-email', name: '邮箱', type: 'email', isPrimary: false, isRequired: false, isVisible: true, order: 15 },
        { id: 'test-url', name: '链接', type: 'url', isPrimary: false, isRequired: false, isVisible: true, order: 16 },
        //{ id: 'test-progress', name: '进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 17 },
        { id: 'test-member', name: '成员', type: 'member', isPrimary: false, isRequired: false, isVisible: true, order: 18 },
        { id: 'test-collaborator', name: '协作者', type: 'collaborator', options: { multiple: true }, isPrimary: false, isRequired: false, isVisible: true, order: 19 },
        { id: 'test-attachment', name: '附件', type: 'attachment', isPrimary: false, isRequired: false, isVisible: true, order: 20 },
        //{ id: 'test-barcode', name: '条形码', type: 'barcode', isPrimary: false, isRequired: false, isVisible: true, order: 21 },
        //{ id: 'test-button', name: '按钮', type: 'button', isPrimary: false, isRequired: false, isVisible: true, order: 22 },
      ],
      views: [
        // {
        //   id: 'test-view-1', name: '完整字段视图', type: 'table',
        //   config: {},
        //   filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
        //   rowHeight: 'medium', isDefault: true, order: 0,
        // },
        // {
        //   id: 'test-view-2', name: '核心字段视图', type: 'table',
        //   config: {},
        //   filters: [], sorts: [], groupBys: [],
        //   hiddenFields: ['test-longtext', 'test-richtext', 'test-percent', 'test-duration', 'test-datetime', 'test-checkbox', 'test-member', 'test-collaborator', 'test-attachment', 'test-barcode', 'test-button'],
        //   frozenFields: ['test-text'],
        //   rowHeight: 'medium', isDefault: false, order: 1,
        // },
        {
          id: 'test-view-3', name: '按类型分组', type: 'kanban',
          config: { groupFieldId: 'test-singleselect' },
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 2,
        },
        {
          id: 'test-view-4', name: '日历视图', type: 'calendar',
          config: { dateFieldId: 'test-date' },
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 3,
        },
        {
          id: 'test-view-5', name: '画廊视图', type: 'gallery',
          config: {},
          filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [],
          rowHeight: 'medium', isDefault: false, order: 4,
        },
      ],
      records: generateTestRecords(),
    }
  ]
};
const okrTemplate: TableTemplate = {
  id: 'okr-management',
  name: 'OKR目标',
  description: '目标和关键结果管理，进度跟踪和对齐',
  icon: '🎯',
  color: '#9333EA',
  category: '目标管理',
  tables: [
    {
      id: 'objectives',
      name: '目标',
      order: 0,
      fields: [
        { id: 'okr-title', name: '目标名称', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'okr-period', name: '周期', type: 'single_select', options: { choices: selectOptions(['2024 Q1', '2024 Q2', '2024 Q3', '2024 Q4', '2024年度']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'okr-owner', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'okr-level', name: '层级', type: 'single_select', options: { choices: selectOptions(['公司级', '部门级', '个人级']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'okr-progress', name: '完成进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'okr-status', name: '状态', type: 'single_select', options: { choices: selectOptions(['正常', '有风险', '已延期', '已完成']) }, isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'okr-start', name: '开始日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'okr-end', name: '结束日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 7 },
        { id: 'okr-score', name: '最终得分', type: 'number', options: { precision: 1, min: 0, max: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'okr-description', name: '目标描述', type: 'single_line_text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 9 },
        { id: 'okr-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 10 }
      ],
      views: [
        { id: 'okr-view-1', name: '目标列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 },
        { id: 'okr-view-2', name: '按周期分组', type: 'kanban', config: { groupFieldId: 'okr-period' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'okr-view-3', name: '按层级分组', type: 'kanban', config: { groupFieldId: 'okr-level' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'okr-rec-1', values: { 'okr-title': '提升产品用户体验', 'okr-period': '2024 Q1', 'okr-level': '公司级', 'okr-progress': 75, 'okr-status': '正常', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000, 'okr-description': '通过优化核心功能和界面设计，提升用户满意度' } },
        { id: 'okr-rec-2', values: { 'okr-title': '完成新功能开发', 'okr-period': '2024 Q1', 'okr-level': '部门级', 'okr-progress': 60, 'okr-status': '有风险', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-3', values: { 'okr-title': '学习新技术栈', 'okr-period': '2024 Q1', 'okr-level': '个人级', 'okr-progress': 80, 'okr-status': '正常', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-4', values: { 'okr-title': '提升团队协作效率', 'okr-period': '2024 Q1', 'okr-level': '部门级', 'okr-progress': 45, 'okr-status': '已延期', 'okr-start': Date.now() - 60 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 30 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-5', values: { 'okr-title': '用户增长目标', 'okr-period': '2024 Q2', 'okr-level': '公司级', 'okr-progress': 0, 'okr-status': '正常', 'okr-start': Date.now() + 30 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() + 120 * 24 * 60 * 60 * 1000 } },
        { id: 'okr-rec-6', values: { 'okr-title': '技术债务清理', 'okr-period': '2024 Q1', 'okr-level': '部门级', 'okr-progress': 100, 'okr-status': '已完成', 'okr-start': Date.now() - 90 * 24 * 60 * 60 * 1000, 'okr-end': Date.now() - 30 * 24 * 60 * 60 * 1000, 'okr-score': 0.85 } }
      ]
    },
    {
      id: 'key-results',
      name: '关键结果',
      order: 1,
      fields: [
        { id: 'kr-title', name: '关键结果', type: 'single_line_text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'kr-objective', name: '所属目标', type: 'link', options: { linkedTableId: 'objectives', relationshipType: 'many_to_one' }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'kr-metric', name: '衡量指标', type: 'single_line_text', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'kr-target', name: '目标值', type: 'number', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'kr-current', name: '当前值', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'kr-progress', name: '完成进度', type: 'progress', options: { showPercent: true }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'kr-owner', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 6 },
        { id: 'kr-weight', name: '权重', type: 'number', options: { suffix: '%', min: 0, max: 100 }, isPrimary: false, isRequired: false, isVisible: true, order: 7 },
        { id: 'kr-score', name: '得分', type: 'number', options: { precision: 2, min: 0, max: 1 }, isPrimary: false, isRequired: false, isVisible: true, order: 8 },
        { id: 'kr-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 9 }
      ],
      views: [
        { id: 'kr-view-1', name: '关键结果列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 0 }
      ],
      records: [
        { id: 'kr-rec-1', values: { 'kr-title': '用户满意度提升至4.5分', 'kr-metric': '用户满意度评分', 'kr-target': 4.5, 'kr-current': 4.2, 'kr-progress': 80, 'kr-weight': 30 } },
        { id: 'kr-rec-2', values: { 'kr-title': '核心功能使用率提升20%', 'kr-metric': '功能使用率', 'kr-target': 120, 'kr-current': 105, 'kr-progress': 75, 'kr-weight': 40 } },
        { id: 'kr-rec-3', values: { 'kr-title': '用户流失率降低至5%', 'kr-metric': '月度流失率', 'kr-target': 5, 'kr-current': 7, 'kr-progress': 60, 'kr-weight': 30 } }
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
  contactListTemplate,
  meetingManagementTemplate,
  learningPlanTemplate,
  recruitmentTemplate,
  assetManagementTemplate,
  bugTrackingTemplate,
  okrTemplate,
  fullFieldTypeTestTemplate
];

// 类型已在文件顶部导出，无需重复导出

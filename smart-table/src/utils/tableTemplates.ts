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
        { id: 'proj-desc', name: '描述', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 7 }
      ],
      views: [
        { id: 'proj-view-1', name: '项目列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'proj-view-2', name: '甘特图', type: 'gantt', config: { startDateFieldId: 'proj-start', endDateFieldId: 'proj-end', progressFieldId: 'proj-progress' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'proj-rec-1', values: { 'proj-name': 'Smart Table 开发', 'proj-status': '进行中', 'proj-start': Date.now() - 7 * 24 * 60 * 60 * 1000, 'proj-end': Date.now() + 30 * 24 * 60 * 60 * 1000, 'proj-progress': 35 } },
        { id: 'proj-rec-2', values: { 'proj-name': '官网改版', 'proj-status': '规划中', 'proj-start': Date.now(), 'proj-end': Date.now() + 60 * 24 * 60 * 60 * 1000, 'proj-progress': 0 } }
      ],
      sampleData: [
        { 
          'proj-name': 'Smart Table 开发', 
          'proj-status': '进行中', 
          'proj-start': new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString('zh-CN'), 
          'proj-end': new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString('zh-CN'), 
          'proj-owner': '张三',
          'proj-priority': '高',
          'proj-progress': '35%',
          'proj-desc': '开发一个智能表格应用'
        },
        { 
          'proj-name': '官网改版', 
          'proj-status': '规划中', 
          'proj-start': new Date(Date.now()).toLocaleDateString('zh-CN'), 
          'proj-end': new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toLocaleDateString('zh-CN'), 
          'proj-owner': '李四',
          'proj-priority': '中',
          'proj-progress': '0%',
          'proj-desc': '重新设计公司官网'
        }
      ]
    },
    {
      id: 'tasks',
      name: '任务',
      description: '项目任务跟踪',
      order: 1,
      fields: [
        { id: 'task-name', name: '任务名称', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'task-status', name: '状态', type: 'single_select', options: { options: selectOptions(['待办', '进行中', '已完成', '已阻塞']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'task-assignee', name: '负责人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'task-due', name: '截止日期', type: 'date', isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'task-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['紧急', '高', '中', '低']) }, isPrimary: false, isRequired: false, isVisible: true, order: 4 }
      ],
      views: [
        { id: 'task-view-1', name: '任务列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'task-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'task-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'task-view-3', name: '日历视图', type: 'calendar', config: { dateFieldId: 'task-due' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'task-rec-1', values: { 'task-name': '完成数据模型设计', 'task-status': '已完成', 'task-due': Date.now() - 5 * 24 * 60 * 60 * 1000, 'task-priority': '高' } },
        { id: 'task-rec-2', values: { 'task-name': '开发表格视图组件', 'task-status': '进行中', 'task-due': Date.now() + 3 * 24 * 60 * 60 * 1000, 'task-priority': '紧急' } },
        { id: 'task-rec-3', values: { 'task-name': '编写用户文档', 'task-status': '待办', 'task-due': Date.now() + 10 * 24 * 60 * 60 * 1000, 'task-priority': '中' } }
      ]
    }
  ]
};

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
        { id: 'tt-notes', name: '备注', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 6 }
      ],
      views: [
        { id: 'tt-view-1', name: '任务列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'tt-view-2', name: '看板', type: 'kanban', config: { groupFieldId: 'tt-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'tt-rec-1', values: { 'tt-title': '完成周报', 'tt-status': '进行中', 'tt-priority': '高', 'tt-due': Date.now() + 1 * 24 * 60 * 60 * 1000, 'tt-tags': ['工作'] } },
        { id: 'tt-rec-2', values: { 'tt-title': '阅读技术文章', 'tt-status': '待办', 'tt-priority': '中', 'tt-tags': ['学习'] } },
        { id: 'tt-rec-3', values: { 'tt-title': '健身锻炼', 'tt-status': '已完成', 'tt-priority': '低', 'tt-tags': ['生活'] } }
      ]
    }
  ]
};

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
        { id: 'cust-stage', name: '阶段', type: 'single_select', options: { options: selectOptions(['潜在客户', '意向客户', '跟进中', '成交客户', '流失客户']) }, isPrimary: false, isRequired: true, isVisible: true, order: 4 },
        { id: 'cust-source', name: '来源', type: 'single_select', options: { options: selectOptions(['线上广告', '朋友推荐', '展会', '电话营销', '自然搜索']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'cust-value', name: '预估价值', type: 'number', options: { format: 'currency', currencySymbol: '¥' }, isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'cust-address', name: '地址', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 7 }
      ],
      views: [
        { id: 'cust-view-1', name: '客户列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'cust-view-2', name: '按阶段分组', type: 'kanban', config: { groupFieldId: 'cust-stage' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'cust-rec-1', values: { 'cust-name': '科技公司A', 'cust-contact': '张经理', 'cust-phone': '13800138001', 'cust-email': 'zhang@example.com', 'cust-stage': '跟进中', 'cust-source': '线上广告', 'cust-value': 50000 } },
        { id: 'cust-rec-2', values: { 'cust-name': '贸易公司B', 'cust-contact': '李总', 'cust-phone': '13900139002', 'cust-stage': '成交客户', 'cust-source': '朋友推荐', 'cust-value': 120000 } }
      ]
    }
  ]
};

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
        { id: 'pr-title', name: '需求标题', type: 'text', isPrimary: true, isRequired: true, isVisible: true, order: 0 },
        { id: 'pr-type', name: '类型', type: 'single_select', options: { options: selectOptions(['新功能', '优化', 'Bug修复', '技术债务']) }, isPrimary: false, isRequired: true, isVisible: true, order: 1 },
        { id: 'pr-status', name: '状态', type: 'single_select', options: { options: selectOptions(['待评估', '规划中', '开发中', '测试中', '已上线', '已拒绝']) }, isPrimary: false, isRequired: true, isVisible: true, order: 2 },
        { id: 'pr-priority', name: '优先级', type: 'single_select', options: { options: selectOptions(['P0-紧急', 'P1-高', 'P2-中', 'P3-低']) }, isPrimary: false, isRequired: true, isVisible: true, order: 3 },
        { id: 'pr-effort', name: '工作量', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 4 },
        { id: 'pr-reporter', name: '提交人', type: 'member', isPrimary: false, isRequired: true, isVisible: true, order: 5 },
        { id: 'pr-created', name: '创建时间', type: 'created_time', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'pr-description', name: '详细描述', type: 'text', options: { isRichText: true }, isPrimary: false, isRequired: false, isVisible: true, order: 7 }
      ],
      views: [
        { id: 'pr-view-1', name: '需求列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'pr-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'pr-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'pr-rec-1', values: { 'pr-title': '用户登录功能', 'pr-type': '新功能', 'pr-status': '已上线', 'pr-priority': 'P0-紧急', 'pr-effort': 5 } },
        { id: 'pr-rec-2', values: { 'pr-title': '优化加载速度', 'pr-type': '优化', 'pr-status': '开发中', 'pr-priority': 'P1-高', 'pr-effort': 3 } },
        { id: 'pr-rec-3', values: { 'pr-title': '添加导出功能', 'pr-type': '新功能', 'pr-status': '规划中', 'pr-priority': 'P2-中', 'pr-effort': 2 } }
      ]
    }
  ]
};

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
        { id: 'cc-tags', name: '标签', type: 'multi_select', options: { options: selectOptions(['技术', '产品', '运营', '案例', '教程']) }, isPrimary: false, isRequired: false, isVisible: true, order: 6 }
      ],
      views: [
        { id: 'cc-view-1', name: '内容列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'cc-view-2', name: '日历视图', type: 'calendar', config: { dateFieldId: 'cc-publish-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 },
        { id: 'cc-view-3', name: '看板视图', type: 'kanban', config: { groupFieldId: 'cc-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 2 }
      ],
      records: [
        { id: 'cc-rec-1', values: { 'cc-title': '产品更新公告 - 3月版', 'cc-type': '博客', 'cc-status': '已排期', 'cc-publish-date': Date.now() + 3 * 24 * 60 * 60 * 1000, 'cc-platform': ['微信公众号', '知乎'], 'cc-tags': ['产品'] } },
        { id: 'cc-rec-2', values: { 'cc-title': '新功能使用教程', 'cc-type': '视频', 'cc-status': '审核中', 'cc-publish-date': Date.now() + 7 * 24 * 60 * 60 * 1000, 'cc-platform': ['B站', '抖音'], 'cc-tags': ['教程'] } }
      ]
    }
  ]
};

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
        { id: 'inv-location', name: '存放位置', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 6 },
        { id: 'inv-supplier', name: '供应商', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 7 }
      ],
      views: [
        { id: 'inv-view-1', name: '商品列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'inv-view-2', name: '按分类查看', type: 'kanban', config: { groupFieldId: 'inv-category' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'inv-rec-1', values: { 'inv-name': '无线鼠标', 'inv-sku': 'MOUSE-001', 'inv-category': '电子产品', 'inv-stock': 150, 'inv-min-stock': 20, 'inv-price': 99, 'inv-location': 'A架-3层', 'inv-supplier': '科技公司A' } },
        { id: 'inv-rec-2', values: { 'inv-name': '笔记本', 'inv-sku': 'NOTE-001', 'inv-category': '办公用品', 'inv-stock': 25, 'inv-min-stock': 50, 'inv-price': 15, 'inv-location': 'B架-1层', 'inv-supplier': '文具厂B' } }
      ]
    }
  ]
};

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
        { id: 'att-hours', name: '工作时长', type: 'number', isPrimary: false, isRequired: false, isVisible: true, order: 5 },
        { id: 'att-remark', name: '备注', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 6 }
      ],
      views: [
        { id: 'att-view-1', name: '考勤记录', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'att-view-2', name: '日历视图', type: 'calendar', config: { dateFieldId: 'att-date' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'att-rec-1', values: { 'att-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'att-type': '正常', 'att-hours': 8 } },
        { id: 'att-rec-2', values: { 'att-date': Date.now() - 1 * 24 * 60 * 60 * 1000, 'att-type': '迟到', 'att-hours': 7.5, 'att-remark': '交通拥堵' } }
      ]
    }
  ]
};

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
        { id: 'bud-payment', name: '支付方式', type: 'single_select', options: { options: selectOptions(['现金', '微信', '支付宝', '银行卡', '信用卡']) }, isPrimary: false, isRequired: false, isVisible: true, order: 5 }
      ],
      views: [
        { id: 'bud-view-1', name: '收支明细', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 }
      ],
      records: [
        { id: 'bud-rec-1', values: { 'bud-date': Date.now() - 5 * 24 * 60 * 60 * 1000, 'bud-type': '收入', 'bud-category': '工资', 'bud-amount': 15000, 'bud-payment': '银行卡' } },
        { id: 'bud-rec-2', values: { 'bud-date': Date.now() - 3 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '餐饮', 'bud-amount': 85, 'bud-description': '午餐', 'bud-payment': '微信' } },
        { id: 'bud-rec-3', values: { 'bud-date': Date.now() - 2 * 24 * 60 * 60 * 1000, 'bud-type': '支出', 'bud-category': '交通', 'bud-amount': 30, 'bud-payment': '支付宝' } }
      ]
    }
  ]
};

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
        { id: 'sur-status', name: '处理状态', type: 'single_select', options: { options: selectOptions(['待处理', '处理中', '已解决', '已关闭']) }, isPrimary: false, isRequired: true, isVisible: true, order: 6 }
      ],
      views: [
        { id: 'sur-view-1', name: '反馈列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'sur-view-2', name: '看板视图', type: 'kanban', config: { groupFieldId: 'sur-status' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'sur-rec-1', values: { 'sur-satisfaction': 4, 'sur-category': '功能建议', 'sur-content': '希望能添加导出功能', 'sur-status': '处理中' } },
        { id: 'sur-rec-2', values: { 'sur-satisfaction': 5, 'sur-category': '其他', 'sur-content': '产品很好用！', 'sur-status': '已关闭' } },
        { id: 'sur-rec-3', values: { 'sur-satisfaction': 2, 'sur-category': 'Bug报告', 'sur-content': '保存时偶尔会报错', 'sur-status': '待处理' } }
      ]
    }
  ]
};

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
        { id: 'con-notes', name: '备注', type: 'text', isPrimary: false, isRequired: false, isVisible: true, order: 8 }
      ],
      views: [
        { id: 'con-view-1', name: '联系人列表', type: 'table', config: {}, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: true, order: 0 },
        { id: 'con-view-2', name: '按分组', type: 'kanban', config: { groupFieldId: 'con-group' }, filters: [], sorts: [], groupBys: [], hiddenFields: [], frozenFields: [], rowHeight: 'medium', isDefault: false, order: 1 }
      ],
      records: [
        { id: 'con-rec-1', values: { 'con-name': '张三', 'con-phone': '13800138001', 'con-email': 'zhangsan@example.com', 'con-company': '科技公司', 'con-position': '产品经理', 'con-group': '同事' } },
        { id: 'con-rec-2', values: { 'con-name': '李四', 'con-phone': '13900139002', 'con-group': '朋友', 'con-birthday': Date.now() - 30 * 365 * 24 * 60 * 60 * 1000 } },
        { id: 'con-rec-3', values: { 'con-name': '王五', 'con-phone': '13700137003', 'con-email': 'wangwu@example.com', 'con-company': '贸易公司', 'con-group': '客户' } }
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

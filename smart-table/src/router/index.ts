import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
} from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("@/views/Home.vue"),
    meta: {
      title: "首页",
    },
  },
  {
    path: "/base/:id",
    name: "Base",
    component: () => import("@/views/Base.vue"),
    meta: {
      title: "多维表格",
    },
  },
  {
    path: "/base/:id/dashboard/:dashboardId",
    name: "Dashboard",
    component: () => import("@/views/Dashboard.vue"),
    meta: {
      title: "仪表盘",
    },
  },
  {
    path: "/share/dashboard/:token",
    name: "DashboardShare",
    component: () => import("@/views/DashboardShare.vue"),
    meta: {
      title: "仪表盘分享",
      public: true, // 标记为公开页面
      layout: "blank", // 使用空白布局
    },
  },
  {
    path: "/form/:id",
    name: "FormShare",
    component: () => import("@/views/FormShare.vue"),
    meta: {
      title: "表单填写",
      public: true, // 标记为公开页面，不需要登录
      layout: "blank", // 使用空白布局，无导航栏和菜单
    },
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("@/views/Settings.vue"),
    meta: {
      title: "设置",
    },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/NotFound.vue"),
    meta: {
      title: "页面未找到",
    },
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string;
  if (title) {
    document.title = `${title} - Smart Table`;
  }
  next();
});

export default router;

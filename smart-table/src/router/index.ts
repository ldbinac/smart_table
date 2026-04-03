import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
} from "vue-router";
import { authGuard, titleGuard } from "./guards";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/auth/Login.vue"),
    meta: {
      title: "登录",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/views/auth/Register.vue"),
    meta: {
      title: "注册",
      public: true,
      layout: "blank",
    },
  },
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
    path: "/base/:id/members",
    name: "BaseMembers",
    component: () => import("@/views/base/MemberManagement.vue"),
    meta: {
      title: "成员管理",
    },
  },
  {
    path: "/share/dashboard/:token",
    name: "DashboardShare",
    component: () => import("@/views/DashboardShare.vue"),
    meta: {
      title: "仪表盘分享",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/form/:id",
    name: "FormShare",
    component: () => import("@/views/FormShare.vue"),
    meta: {
      title: "表单填写",
      public: true,
      layout: "blank",
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

// 使用路由守卫
router.beforeEach(authGuard);
router.beforeEach(titleGuard);

export default router;

import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
} from "vue-router";
import { authGuard, titleGuard, adminGuard } from "./guards";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/auth/Login.vue"),
    meta: {
      title: "route.login",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/views/auth/Register.vue"),
    meta: {
      title: "route.register",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/verify-email",
    name: "VerifyEmail",
    component: () => import("@/views/auth/VerifyEmail.vue"),
    meta: {
      title: "route.verifyEmail",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/forgot-password",
    name: "ForgotPassword",
    component: () => import("@/views/auth/ForgotPassword.vue"),
    meta: {
      title: "route.forgotPassword",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/gitee-callback",
    name: "GiteeCallback",
    component: () => import("@/views/auth/GiteeCallback.vue"),
    meta: {
      title: "route.giteeCallback",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/reset-password",
    name: "ResetPassword",
    component: () => import("@/views/auth/ResetPassword.vue"),
    meta: {
      title: "route.resetPassword",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/",
    name: "Home",
    component: () => import("@/views/Home.vue"),
    meta: {
      title: "route.home",
    },
  },
  {
    path: "/base/:id",
    name: "Base",
    component: () => import("@/views/Base.vue"),
    meta: {
      title: "route.base",
    },
  },
  {
    path: "/base/:id/table/:tableId",
    name: "BaseTable",
    component: () => import("@/views/Base.vue"),
    meta: {
      title: "route.baseTable",
    },
  },
  {
    path: "/base/:id/dashboard/:dashboardId",
    name: "Dashboard",
    component: () => import("@/views/Dashboard.vue"),
    meta: {
      title: "route.dashboard",
    },
  },
  {
    path: "/base/:id/members",
    name: "BaseMembers",
    component: () => import("@/views/base/MemberManagement.vue"),
    meta: {
      title: "route.baseMembers",
    },
  },
  {
    path: "/base/:id/documents/:docId",
    name: "BaseDocument",
    component: () => import("@/views/Base.vue"),
    meta: {
      title: "route.baseDocument",
    },
  },
  {
    path: "/base/:id/workflows",
    name: "BaseWorkflows",
    component: () => import("@/views/base/WorkflowManager.vue"),
    meta: {
      title: "route.baseWorkflows",
      requiresAuth: true,
    },
  },
  {
    path: "/share/dashboard/:token",
    name: "DashboardShare",
    component: () => import("@/views/DashboardShare.vue"),
    meta: {
      title: "route.dashboardShare",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/form/:token",
    name: "FormShare",
    component: () => import("@/views/FormShare.vue"),
    meta: {
      title: "route.formShare",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/share/:token",
    name: "BaseShare",
    component: () => import("@/views/BaseShare.vue"),
    meta: {
      title: "route.baseShare",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/pdf-preview",
    name: "PdfPreview",
    component: () => import("@/views/PdfPreviewPage.vue"),
    meta: {
      title: "route.pdfPreview",
      public: true,
      layout: "blank",
    },
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("@/views/Settings.vue"),
    meta: {
      title: "route.settings",
    },
  },
  {
    path: "/notifications",
    name: "Notifications",
    component: () => import("@/views/Notifications.vue"),
    meta: {
      title: "route.notifications",
      requiresAuth: true,
    },
  },
  {
    path: "/admin/users",
    name: "AdminUsers",
    component: () => import("@/views/admin/UserManagement.vue"),
    meta: {
      title: "route.adminUsers",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/settings",
    name: "AdminSettings",
    component: () => import("@/views/admin/SystemSettings.vue"),
    meta: {
      title: "route.adminSettings",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/logs",
    name: "AdminLogs",
    component: () => import("@/views/admin/OperationLogs.vue"),
    meta: {
      title: "route.adminLogs",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/oauth-apps",
    name: "AdminOAuthApps",
    component: () => import("@/views/admin/OAuthAppManagement.vue"),
    meta: {
      title: "route.adminOAuthApps",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/email/templates",
    name: "EmailTemplates",
    component: () => import("@/views/admin/EmailTemplates.vue"),
    meta: {
      title: "route.emailTemplates",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/email/logs",
    name: "EmailLogs",
    component: () => import("@/views/admin/EmailLogs.vue"),
    meta: {
      title: "route.emailLogs",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/email/stats",
    name: "EmailStats",
    component: () => import("@/views/admin/EmailStats.vue"),
    meta: {
      title: "route.emailStats",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/notifications/logs",
    name: "NotificationLogs",
    component: () => import("@/views/admin/NotificationLogs.vue"),
    meta: {
      title: "route.notificationLogs",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/notifications/stats",
    name: "NotificationStats",
    component: () => import("@/views/admin/NotificationStats.vue"),
    meta: {
      title: "route.notificationStats",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/admin/plugins",
    name: "AdminPlugins",
    component: () => import("@/views/PluginManage.vue"),
    meta: {
      title: "route.adminPlugins",
      requiresAdmin: true,
    },
    beforeEnter: adminGuard,
  },
  {
    path: "/403",
    name: "Forbidden",
    component: () => import("@/views/Forbidden.vue"),
    meta: {
      title: "route.forbidden",
    },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/NotFound.vue"),
    meta: {
      title: "route.notFound",
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
router.beforeEach(async (to, _from, next) => {
  if (to.meta.requiresAdmin) {
    await adminGuard(to, _from, next);
  } else {
    next();
  }
});
router.beforeEach(titleGuard);

export default router;

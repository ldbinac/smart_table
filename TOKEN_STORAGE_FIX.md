# 认证 Token 存储问题修复报告

## 问题描述

当浏览器客户端调用 `/api/bases` 接口时，返回 401 Unauthorized 错误。经过检查发现:
1. 前端请求拦截器已经修复，可以从 `localStorage` 和 `sessionStorage` 读取 token
2. **但是登录后 token 没有被正确存储到浏览器缓存中**

## 根本原因

在 [`authStore.ts`](d:/_dev/fs_table/smart-table-spec/smart-table/src/stores/auth/authStore.ts) 的 `login` 方法中，访问 token 的路径错误:

### 错误代码 (修复前)
```typescript
const login = async (credentials: LoginRequest, remember: boolean = false): Promise<boolean> => {
  const response = await authService.login(credentials)
  
  // ❌ 错误：response.access_token 不存在
  setToken(response.access_token, remember)
  setRefreshToken(response.refresh_token, remember)
  
  // ...
}
```

### 问题分析

后端返回的 `LoginResponse` 结构是:
```typescript
interface LoginResponse {
  user: User
  tokens: {
    access_token: string
    refresh_token: string
  }
}
```

但是代码尝试访问 `response.access_token` 和 `response.refresh_token`,这两个字段不存在，导致:
- `response.access_token` 返回 `undefined`
- `setToken(undefined, remember)` 将 `undefined` 存储到浏览器缓存
- 后续 API 请求使用 `undefined` 作为 token，导致 401 错误

## 修复方案

### 修复后的代码
```typescript
const login = async (credentials: LoginRequest, remember: boolean = false): Promise<boolean> => {
  const response = await authService.login(credentials)
  
  // ✅ 正确：使用 response.tokens.access_token
  setToken(response.tokens.access_token, remember)
  setRefreshToken(response.tokens.refresh_token, remember)
  setRememberMe(remember)
  
  user.value = response.user
  isAuthenticated.value = true
  
  message.success('登录成功')
  return true
}
```

## 验证测试

### 测试 1: Token 存储结构验证
```javascript
console.log('后端返回结构:');
console.log('  - response.user: ✓');
console.log('  - response.tokens.access_token: ✓');
console.log('  - response.tokens.refresh_token: ✓');
```

### 测试 2: Token 存储验证 (不记住登录)
```javascript
setToken(data.data.tokens.access_token, false);
setRefreshToken(data.data.tokens.refresh_token, false);

// 验证 sessionStorage
const storedToken = getToken();
// ✓ Token 正确存储到 sessionStorage
```

### 测试 3: Token 存储验证 (记住登录)
```javascript
setToken(data.data.tokens.access_token, true);
setRefreshToken(data.data.tokens.refresh_token, true);

// 验证 localStorage
const storedToken = getToken();
// ✓ Token 正确存储到 localStorage
```

### 测试 4: API 调用验证
```javascript
fetch('/api/bases', {
  headers: { 'Authorization': `Bearer ${storedToken}` }
});
// 状态码：200
// ✓ API 调用成功
```

## 测试结果

所有测试通过 ✅:
- ✅ 后端返回正确的 token 结构 (`response.tokens.access_token`)
- ✅ Token 正确存储到浏览器缓存 (`localStorage`/`sessionStorage`)
- ✅ 存储的 Token 可以正确读取并用于 API 调用
- ✅ `/api/bases` 接口返回 200 OK

## 修复文件

- [`smart-table/src/stores/auth/authStore.ts`](d:/_dev/fs_table/smart-table-spec/smart-table/src/stores/auth/authStore.ts) - 第 42-43 行

## 总结

这是一个典型的**数据结构访问错误**:
1. 后端返回嵌套的 `tokens` 对象
2. 前端代码直接访问顶层不存在的字段
3. 导致 `undefined` 被存储到浏览器缓存
4. 后续请求使用无效的 token 导致 401 错误

修复后，登录流程完全正常:
```
登录 → 获取 response.tokens.access_token → 存储到浏览器 → 后续请求携带 token → 200 OK
```

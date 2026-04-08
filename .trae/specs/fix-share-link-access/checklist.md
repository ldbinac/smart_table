# Checklist

- [x] 后端 `GET /bases/{base_id}` 接口支持 `share_token` 查询参数
- [x] 后端能够验证 `share_token` 的有效性
- [x] 后端在 `share_token` 有效时自动将用户添加为 Base 成员
- [x] 前端 `baseApiService.getBase` 方法支持 `shareToken` 参数
- [x] 前端 `baseStore.fetchBase` 方法支持 `shareToken` 参数
- [x] 通过分享链接访问时，Base 页面能正常加载，不再返回 403 错误
- [x] 通过分享链接访问的用户被正确添加为 Base 成员

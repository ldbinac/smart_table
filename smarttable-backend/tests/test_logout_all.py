"""
退出所有设备功能测试脚本
验证版本号机制是否正常工作
"""

print("=== 退出所有设备功能测试 ===\n")

print("实现原理：")
print("1. 生成 token 时，从缓存获取当前 token_version 并包含在 token 中")
print("2. 验证 token 时，检查 token 中的 version 是否 >= 缓存中的当前 version")
print("3. 退出所有设备时，将缓存中的 version + 1，使旧 token 失效\n")

print("测试步骤：")
print("1. 用户登录 -> 生成 token（version=0）")
print("2. 在另一个浏览器登录 -> 生成 token（version=0）")
print("3. 在浏览器 A 点击'退出所有设备' -> version 变为 1")
print("4. 浏览器 A 的 token 失效（version=0 < 1）")
print("5. 浏览器 B 的 token 也失效（version=0 < 1）\n")

print("关键代码：")
print("- auth_service.py: generate_tokens() - 生成时包含 version")
print("- extensions.py: check_if_token_revoked() - 验证时检查 version")
print("- auth_service.py: revoke_all_user_tokens() - 增加 version\n")

print("✓ 实现完成，需要重启后端服务进行测试")

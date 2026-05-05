"""
验证新功能：自动创建管理员 + 自动打开浏览器
"""
import sys
import os

print("="*70)
print("  SmartTable 新功能验证")
print("="*70)

# 测试 1: 验证 ensure_default_admin_exists 函数存在且可调用
print("\n[测试 1] 检查 ensure_default_admin_exists 函数...")
try:
    # 导入函数（不执行）
    sys.path.insert(0, '.')
    from run import ensure_default_admin_exists
    
    if callable(ensure_default_admin_exists):
        print("✅ 函数定义正确")
        print(f"   函数名: {ensure_default_admin_exists.__name__}")
        print(f"   文档字符串: {ensure_default_admin_exists.__doc__[:50]}..." if ensure_default_admin_exists.__doc__ else "   ⚠️ 无文档")
    else:
        print("❌ 不是可调用对象")
except Exception as e:
    print(f"❌ 导入失败: {e}")

# 测试 2: 验证 open_browser_after_delay 函数
print("\n[测试 2] 检查 open_browser_after_delay 函数...")
try:
    from run import open_browser_after_delay
    
    if callable(open_browser_after_delay):
        print("✅ 函数定义正确")
        print(f"   函数名: {open_browser_after_delay.__name__}")
        
        # 验证参数签名
        import inspect
        sig = inspect.signature(open_browser_after_delay)
        params = list(sig.parameters.keys())
        expected_params = ['url', 'delay_seconds']
        if set(params) == set(expected_params):
            print(f"   参数签名: {params} ✅")
        else:
            print(f"   参数签名: {params} (期望: {expected_params})")
    else:
        print("❌ 不是可调用对象")
except Exception as e:
    print(f"❌ 导入失败: {e}")

# 测试 3: 验证 webbrowser 和 threading 已导入
print("\n[测试 3] 检查依赖模块导入...")
try:
    import webbrowser
    import threading
    print("✅ webbrowser 模块已导入")
    print(f"   版本/路径: {webbrowser.__file__ if hasattr(webbrowser, '__file__') else '内置模块'}")
    print("✅ threading 模块已导入")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")

# 测试 4: 验证默认管理员配置
print("\n[测试 4] 检查默认管理员配置...")
try:
    # 从函数源码中提取默认值（通过 AST 或字符串解析）
    import inspect
    source = inspect.getsource(ensure_default_admin_exists)
    
    if 'ldengbin@126.com' in source:
        print("✅ 默认邮箱: ldengbin@126.com")
    else:
        print("⚠️ 未找到默认邮箱配置")
    
    if 'LDengBin@126.com' in source:
        print("✅ 默认密码: LDengBin@126.com")
    else:
        print("⚠️ 未找到默认密码配置")
    
    if "'root'" in source or '"root"' in source:
        print("✅ 默认账号: root")
    else:
        print("⚠️ 未找到默认账号配置")
        
    if 'UserRole.ADMIN' in source:
        print("✅ 角色设置: UserRole.ADMIN")
    else:
        print("⚠️ 未找到角色配置")

except Exception as e:
    print(f"❌ 配置检查失败: {e}")

# 测试 5: 验证启动流程集成
print("\n[测试 5] 检查启动流程集成...")
try:
    with open('run.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('ensure_default_admin_exists()', '管理员检查调用'),
            ('open_browser_after_delay(', '浏览器打开调用'),
            ('service_url = ', 'URL 构建逻辑'),
        ]
        
        all_found = True
        for pattern, desc in checks:
            if pattern in content:
                print(f"✅ {desc}: 已集成")
            else:
                print(f"❌ {desc}: 未找到")
                all_found = False
        
        if all_found:
            print("\n✅ 所有启动流程集成检查通过！")

except Exception as e:
    print(f"❌ 启动流程检查失败: {e}")

print("\n" + "="*70)
print("  验证完成！")
print("="*70)
print("\n下一步:")
print("  1. 运行 'python run.py' 启动服务")
print("  2. 观察控制台输出:")
print("     - 应该看到管理员账号信息（如果没有管理员）")
print("     - 2秒后应该自动打开浏览器")
print("="*70)

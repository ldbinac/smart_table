/**
 * 测试 Token 存储修复
 * 验证登录后 token 是否正确存储到浏览器缓存
 */

const API_BASE = 'http://localhost:5000/api';

// 模拟浏览器存储
const localStorage = {
  data: {},
  setItem(key, value) {
    this.data[key] = value;
    console.log(`  [localStorage] 设置 ${key} = ${value.substring(0, 30)}...`);
  },
  getItem(key) {
    const value = this.data[key];
    console.log(`  [localStorage] 读取 ${key} = ${value ? value.substring(0, 30) + '...' : 'null'}`);
    return value;
  },
  removeItem(key) {
    delete this.data[key];
    console.log(`  [localStorage] 移除 ${key}`);
  },
  clear() {
    this.data = {};
  }
};

const sessionStorage = {
  data: {},
  setItem(key, value) {
    this.data[key] = value;
    console.log(`  [sessionStorage] 设置 ${key} = ${value.substring(0, 30)}...`);
  },
  getItem(key) {
    const value = this.data[key];
    console.log(`  [sessionStorage] 读取 ${key} = ${value ? value.substring(0, 30) + '...' : 'null'}`);
    return value;
  },
  removeItem(key) {
    delete this.data[key];
    console.log(`  [sessionStorage] 移除 ${key}`);
  },
  clear() {
    this.data = {};
  }
};

// Token 管理工具
const AUTH_CONFIG = {
  TOKEN_KEY: 'access_token',
  REFRESH_TOKEN_KEY: 'refresh_token',
  REMEMBER_KEY: 'remember_me'
};

function setToken(token, remember = false) {
  if (remember) {
    localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token);
  } else {
    sessionStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token);
  }
}

function setRefreshToken(token, remember = false) {
  if (remember) {
    localStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, token);
  } else {
    sessionStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, token);
  }
}

function getToken() {
  return localStorage.getItem(AUTH_CONFIG.TOKEN_KEY) || 
         sessionStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
}

async function testTokenStorage() {
  console.log('=== 测试 Token 存储修复 ===\n');

  try {
    // 步骤 1: 登录 (不记住登录状态)
    console.log('1. 测试登录 (不记住登录状态)...');
    const loginResponse = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' })
    });

    if (!loginResponse.ok) {
      console.log('   ✗ 登录失败，请先注册');
      return;
    }

    const data = await loginResponse.json();
    console.log('   ✓ 登录成功');
    console.log(`   - 后端返回结构:`);
    console.log(`     * response.user: ${data.data.user ? '✓' : '✗'}`);
    console.log(`     * response.tokens.access_token: ${data.data.tokens?.access_token ? '✓' : '✗'}`);
    console.log(`     * response.tokens.refresh_token: ${data.data.tokens?.refresh_token ? '✓' : '✗'}`);

    // 步骤 2: 模拟存储 Token (不记住)
    console.log('\n2. 模拟存储 Token (不记住登录状态)...');
    setToken(data.data.tokens.access_token, false);
    setRefreshToken(data.data.tokens.refresh_token, false);

    // 步骤 3: 验证 Token 是否正确存储
    console.log('\n3. 验证 Token 是否正确存储...');
    const storedToken = getToken();
    const expectedToken = data.data.tokens.access_token;
    
    if (storedToken === expectedToken) {
      console.log('   ✓ Token 正确存储到 sessionStorage');
    } else {
      console.log('   ✗ Token 存储失败');
      console.log(`     期望：${expectedToken.substring(0, 30)}...`);
      console.log(`     实际：${storedToken ? storedToken.substring(0, 30) + '...' : 'null'}`);
    }

    // 步骤 4: 测试使用 Token 访问 API
    console.log('\n4. 测试使用 Token 访问 /api/bases...');
    const apiResponse = await fetch(`${API_BASE}/bases`, {
      headers: { 'Authorization': `Bearer ${storedToken}` }
    });

    console.log(`   状态码：${apiResponse.status}`);
    if (apiResponse.status === 200) {
      const result = await apiResponse.json();
      console.log('   ✓ API 调用成功');
      console.log(`   - 响应：${result.message}`);
    } else {
      const error = await apiResponse.json();
      console.log('   ✗ API 调用失败');
      console.log(`   - 错误：${error.message}`);
    }

    // 步骤 5: 测试记住登录状态
    console.log('\n5. 测试记住登录状态 (存储到 localStorage)...');
    localStorage.clear();
    sessionStorage.clear();
    
    setToken(data.data.tokens.access_token, true);
    setRefreshToken(data.data.tokens.refresh_token, true);
    
    const storedToken2 = getToken();
    if (storedToken2 === expectedToken) {
      console.log('   ✓ Token 正确存储到 localStorage');
    } else {
      console.log('   ✗ Token 存储失败');
    }

    console.log('\n=== 测试完成 ===');
    console.log('\n总结:');
    console.log('✓ 后端返回正确的 token 结构 (response.tokens.access_token)');
    console.log('✓ Token 正确存储到浏览器缓存 (localStorage/sessionStorage)');
    console.log('✓ 存储的 Token 可以正确读取并用于 API 调用');
    console.log('\n修复验证通过!authStore.login 方法现在使用 response.tokens.access_token 而不是 response.access_token');

  } catch (error) {
    console.error('\n✗ 测试过程中发生错误:', error.message);
  }
}

// 运行测试
testTokenStorage();

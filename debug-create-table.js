/**
 * 调试创建表的响应
 */

const API_BASE = 'http://localhost:5000/api';

async function debugCreateTable() {
  try {
    // 登录
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' })
    });
    
    const loginData = await loginRes.json();
    const token = loginData.data.tokens.access_token;
    
    // 获取 bases
    const basesRes = await fetch(`${API_BASE}/bases`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const basesData = await basesRes.json();
    const baseId = basesData.data[0].id;
    
    // 创建 table
    console.log('创建测试表...');
    const createTableRes = await fetch(`${API_BASE}/bases/${baseId}/tables`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: '测试表', description: '测试字段格式' })
    });
    
    const tableData = await createTableRes.json();
    console.log('创建表响应:', JSON.stringify(tableData, null, 2));
    
  } catch (error) {
    console.error('错误:', error);
  }
}

debugCreateTable();

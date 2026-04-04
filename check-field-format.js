/**
 * 检查后端返回的字段数据格式
 */

const API_BASE = 'http://localhost:5000/api';

async function checkFieldFormat() {
  try {
    // 登录
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' })
    });
    
    if (!loginRes.ok) {
      console.error('登录失败');
      return;
    }
    
    const loginData = await loginRes.json();
    const token = loginData.data.tokens.access_token;
    console.log('✓ 登录成功');
    
    // 获取 bases
    const basesRes = await fetch(`${API_BASE}/bases`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const basesData = await basesRes.json();
    
    if (basesData.data.length === 0) {
      console.error('没有 Bases');
      return;
    }
    
    const baseId = basesData.data[0].id;
    
    // 获取 tables
    const tablesRes = await fetch(`${API_BASE}/bases/${baseId}/tables`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const tablesData = await tablesRes.json();
    
    if (tablesData.data.length === 0) {
      console.error('没有 Tables');
      return;
    }
    
    const tableId = tablesData.data[0].id;
    console.log(`\n使用 Table: ${tableId}`);
    
    // 获取 fields
    const fieldsRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const fieldsData = await fieldsRes.json();
    
    console.log(`\n=== 字段列表 ===`);
    fieldsData.data.forEach(field => {
      console.log(`\n字段：${field.name} (${field.type})`);
      console.log('  ID:', field.id);
      console.log('  options:', JSON.stringify(field.options, null, 2));
      
      // 检查 options 的结构
      if (field.options) {
        console.log('  options 的键:', Object.keys(field.options));
        if (field.options.choices) {
          console.log('  ✓ 包含 choices:', field.options.choices);
        }
        if (field.options.options) {
          console.log('  ✓ 包含 options:', field.options.options);
        }
      }
    });
    
    // 获取 records
    const recordsRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const recordsData = await recordsRes.json();
    
    console.log(`\n=== 记录数据 ===`);
    console.log('记录数量:', recordsData.data.length);
    
    if (recordsData.data.length > 0) {
      const record = recordsData.data[0];
      console.log('\n第一条记录的 values:', JSON.stringify(record.values, null, 2));
    }
    
  } catch (error) {
    console.error('错误:', error);
  }
}

checkFieldFormat();

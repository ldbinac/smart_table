/**
 * 测试字段数据格式
 * 检查后端返回的字段数据中 options 的实际结构
 */

const API_BASE = 'http://localhost:5000/api';

async function testFieldDataFormat() {
  try {
    // 1. 登录获取 token
    console.log('1. 登录...');
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
    console.log('✓ Token:', token.substring(0, 50) + '...');
    
    // 2. 获取 bases 列表
    console.log('\n2. 获取 Bases 列表...');
    const basesRes = await fetch(`${API_BASE}/bases`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const basesData = await basesRes.json();
    console.log('Bases:', basesData.data.length);
    
    if (basesData.data.length === 0) {
      console.error('没有 Bases');
      return;
    }
    
    const baseId = basesData.data[0].id;
    console.log('Base ID:', baseId);
    
    // 3. 获取 tables 列表
    console.log('\n3. 获取 Tables 列表...');
    const tablesRes = await fetch(`${API_BASE}/bases/${baseId}/tables`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const tablesData = await tablesRes.json();
    console.log('Tables:', tablesData.data.length);
    
    if (tablesData.data.length === 0) {
      console.error('没有 Tables');
      return;
    }
    
    const tableId = tablesData.data[0].id;
    console.log('Table ID:', tableId);
    
    // 4. 获取 fields 列表
    console.log('\n4. 获取 Fields 列表...');
    const fieldsRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const fieldsData = await fieldsRes.json();
    console.log('Fields:', fieldsData.data.length);
    
    // 5. 查找单选/多选字段
    console.log('\n5. 查找单选/多选字段...');
    const singleSelectFields = fieldsData.data.filter(f => f.type === 'single_select');
    const multiSelectFields = fieldsData.data.filter(f => f.type === 'multi_select');
    
    console.log('单选字段:', singleSelectFields.length);
    console.log('多选字段:', multiSelectFields.length);
    
    if (singleSelectFields.length > 0) {
      console.log('\n=== 第一个单选字段 ===');
      const field = singleSelectFields[0];
      console.log('字段 ID:', field.id);
      console.log('字段名称:', field.name);
      console.log('字段类型:', field.type);
      console.log('字段 options:', JSON.stringify(field.options, null, 2));
      console.log('options.choices:', field.options?.choices);
      console.log('options.options:', field.options?.options);
    }
    
    if (multiSelectFields.length > 0) {
      console.log('\n=== 第一个多选字段 ===');
      const field = multiSelectFields[0];
      console.log('字段 ID:', field.id);
      console.log('字段名称:', field.name);
      console.log('字段类型:', field.type);
      console.log('字段 options:', JSON.stringify(field.options, null, 2));
    }
    
    // 6. 获取 records 查看实际存储的值
    console.log('\n6. 获取 Records...');
    const recordsRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const recordsData = await recordsRes.json();
    console.log('Records:', recordsData.data.length);
    
    if (recordsData.data.length > 0 && singleSelectFields.length > 0) {
      const fieldId = singleSelectFields[0].id;
      console.log(`\n=== 记录中的单选字段值 (field: ${singleSelectFields[0].name}) ===`);
      recordsData.data.forEach((record, idx) => {
        if (idx < 5) { // 只显示前 5 条
          console.log(`记录${idx + 1}:`, record.values[fieldId]);
        }
      });
    }
    
  } catch (error) {
    console.error('测试失败:', error);
  }
}

// 运行测试
testFieldDataFormat();

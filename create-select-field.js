/**
 * 创建单选字段并测试
 */

const API_BASE = 'http://localhost:5000/api';

async function createAndTest() {
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
    
    // 获取 tables
    const tablesRes = await fetch(`${API_BASE}/bases/${baseId}/tables`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const tablesData = await tablesRes.json();
    const tableId = tablesData.data[0].id;
    
    console.log('创建单选字段...');
    // 创建单选字段
    const createFieldRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: '性别',
        type: 'single_select',
        options: {
          choices: [
            { id: 'male', name: '男', color: '#4ECDC4' },
            { id: 'female', name: '女', color: '#FF6B6B' }
          ]
        }
      })
    });
    
    const fieldData = await createFieldRes.json();
    console.log('\n=== 创建字段响应 ===');
    console.log('Success:', fieldData.success);
    
    if (!fieldData.data) {
      console.error('字段创建失败');
      return;
    }
    
    console.log('\n字段 options:', JSON.stringify(fieldData.data.options, null, 2));
    
    // 立即获取字段列表查看实际存储的格式
    console.log('\n=== 获取字段列表 ===');
    const getFieldsRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const fieldsData = await getFieldsRes.json();
    const singleSelectField = fieldsData.data.find(f => f.type === 'single_select');
    
    console.log('\n从列表获取的字段:');
    console.log('名称:', singleSelectField.name);
    console.log('options:', JSON.stringify(singleSelectField.options, null, 2));
    console.log('options.choices:', singleSelectField.options?.choices);
    console.log('options.options:', singleSelectField.options?.options);
    
    // 创建测试记录
    console.log('\n=== 创建测试记录 ===');
    const fieldId = singleSelectField.id;
    const createRecordRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        values: {
          [fieldId]: 'male' // 使用选项 ID
        }
      })
    });
    const recordData = await createRecordRes.json();
    console.log('创建记录响应:', JSON.stringify(recordData, null, 2));
    
    // 获取记录查看存储的值
    console.log('\n=== 获取记录 ===');
    const getRecordsRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const recordsData = await getRecordsRes.json();
    const record = recordsData.data.find(r => r.values[fieldId]);
    
    console.log('记录 values:', JSON.stringify(record.values, null, 2));
    console.log(`记录中 ${fieldId} 的值:`, record.values[fieldId]);
    
  } catch (error) {
    console.error('错误:', error);
  }
}

createAndTest();

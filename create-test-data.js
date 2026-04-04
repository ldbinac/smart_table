/**
 * 创建测试数据
 */

const API_BASE = 'http://localhost:5000/api';

async function createTestData() {
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
    const tableId = tableData.table.id;
    console.log('✓ Table ID:', tableId);
    
    // 创建单选字段
    console.log('\n创建单选字段...');
    const createFieldRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: '状态',
        type: 'single_select',
        options: {
          choices: [
            { id: 'opt1', name: '待处理', color: '#FF6B6B' },
            { id: 'opt2', name: '进行中', color: '#4ECDC4' },
            { id: 'opt3', name: '已完成', color: '#95E1D3' }
          ]
        }
      })
    });
    const fieldData = await createFieldRes.json();
    console.log('✓ Field ID:', fieldData.field.id);
    console.log('✓ Field options:', JSON.stringify(fieldData.field.options, null, 2));
    
    // 创建记录
    console.log('\n创建测试记录...');
    const fieldId = fieldData.field.id;
    const createRecordRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        values: {
          [fieldId]: 'opt1' // 使用选项 ID
        }
      })
    });
    const recordData = await createRecordRes.json();
    console.log('✓ Record ID:', recordData.record.id);
    console.log('✓ Record values:', JSON.stringify(recordData.record.values, null, 2));
    
    // 获取 fields 验证格式
    console.log('\n验证字段格式...');
    const getFieldsRes = await fetch(`${API_BASE}/tables/${tableId}/fields`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const fieldsData = await getFieldsRes.json();
    const field = fieldsData.data.find(f => f.type === 'single_select');
    console.log('\n=== 后端返回的字段数据 ===');
    console.log('options:', JSON.stringify(field.options, null, 2));
    console.log('options.choices:', field.options?.choices);
    console.log('options.options:', field.options?.options);
    
    // 获取 records 验证值
    console.log('\n验证记录值...');
    const getRecordsRes = await fetch(`${API_BASE}/tables/${tableId}/records`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const recordsData = await getRecordsRes.json();
    const record = recordsData.data[0];
    console.log('Record values[fieldId]:', record.values[fieldId]);
    
  } catch (error) {
    console.error('错误:', error);
  }
}

createTestData();

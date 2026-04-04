import re

# 读取文件
with open('d:/_dev/fs_table/smart-table-spec/smart-table/src/views/Base.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 baseStore.records -> tableStore.records
content = content.replace('baseStore.records', 'tableStore.records')

# 替换 baseStore.fields -> tableStore.fields
content = content.replace('baseStore.fields', 'tableStore.fields')

# 替换 baseStore.currentTable -> tableStore.currentTable
content = content.replace('baseStore.currentTable', 'tableStore.currentTable')

# 替换 baseStore.views -> tableStore.views
content = content.replace('baseStore.views', 'tableStore.views')

# 写回文件
with open('d:/_dev/fs_table/smart-table-spec/smart-table/src/views/Base.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print('替换完成!')

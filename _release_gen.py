import sys, os
sys.path.insert(0, '.')
from build import prepare_release_package, RELEASE_DIR, PLATFORMS

platform = 'windows'
print(f'准备 {PLATFORMS[platform]["display_name"]} 发布包...')
prepare_release_package(platform)

release_dir = RELEASE_DIR / PLATFORMS[platform]['display_name']
print(f'\n✅ 发布包内容:')
for root, dirs, files in os.walk(release_dir):
    level = root.replace(str(release_dir), '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}{os.path.basename(root)}/')
    sub_indent = '  ' * (level + 1)
    for file in files:
        filepath = os.path.join(root, file)
        size = os.path.getsize(filepath) / 1024
        print(f'{sub_indent}{file} ({size:.1f} KB)')

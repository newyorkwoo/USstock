# 測試腳本

import sys
import os

# 添加後端目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 60)
print("美國股市分析系統 - 環境檢測")
print("=" * 60)

# 檢查 Python 版本
print("\n1. Python 環境:")
print(f"   Python 版本: {sys.version}")

# 檢查後端依賴
print("\n2. 後端依賴檢測:")
dependencies = [
    'flask',
    'flask_cors',
    'yfinance',
    'pandas',
    'numpy',
    'scipy'
]

missing = []
for dep in dependencies:
    try:
        __import__(dep)
        print(f"   ✓ {dep}")
    except ImportError:
        print(f"   ✗ {dep} (未安裝)")
        missing.append(dep)

if missing:
    print(f"\n   ⚠️  缺少依賴: {', '.join(missing)}")
    print("   請執行: cd backend && source venv/bin/activate && pip install -r requirements.txt")
else:
    print("\n   ✓ 所有後端依賴已安裝")

# 檢查前端
print("\n3. 前端環境:")
frontend_path = os.path.join(os.path.dirname(__file__), 'frontend', 'node_modules')
if os.path.exists(frontend_path):
    print("   ✓ node_modules 存在")
else:
    print("   ✗ node_modules 不存在")
    print("   請執行: cd frontend && npm install")

# 檢查配置文件
print("\n4. 配置文件檢測:")
config_files = [
    'frontend/package.json',
    'frontend/vite.config.js',
    'frontend/tailwind.config.js',
    'backend/app.py',
    'backend/requirements.txt'
]

for file in config_files:
    full_path = os.path.join(os.path.dirname(__file__), file)
    if os.path.exists(full_path):
        print(f"   ✓ {file}")
    else:
        print(f"   ✗ {file} (缺失)")

print("\n" + "=" * 60)
print("檢測完成！")
print("=" * 60)

# 快速啟動提示
print("\n📝 快速啟動步驟:")
print("\n終端 1 (後端):")
print("   cd /Users/steven/Documents/myproject/USstock")
print("   ./start-backend.sh")
print("\n終端 2 (前端):")
print("   cd /Users/steven/Documents/myproject/USstock")
print("   ./start-frontend.sh")
print("\n瀏覽器:")
print("   http://localhost:3000 (或顯示的端口)")
print("\n" + "=" * 60)

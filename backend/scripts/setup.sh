#!/bin/bash
# Quick setup script for Narrify
# Fixes all import issues and prepares database

set -e  # Exit on error

echo "======================================================================"
echo "🚀 Narrify Quick Setup"
echo "======================================================================"
echo ""

# Change to backend directory
cd "$(dirname "$0")/.."

# 1. Install dependencies
echo "📦 Step 1/5: Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# 2. Migrate database
echo "🗄️  Step 2/5: Migrating database..."
if [ -f "stories.db" ]; then
    python scripts/migrate_database.py --auto
else
    echo "ℹ️  No existing database found (will be created on first run)"
fi
echo ""

# 3. Create .env file
echo "⚙️  Step 3/5: Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  IMPORTANT: Edit .env with your API credentials!"
else
    echo "✅ .env file already exists"
fi
echo ""

# 4. Create necessary directories
echo "📁 Step 4/5: Creating directories..."
mkdir -p logs
mkdir -p config
echo "✅ Directories created"
echo ""

# 5. Test imports
echo "🔍 Step 5/5: Testing imports..."
python -c "
try:
    from app.main import app
    print('✅ All imports working!')
except ImportError as e:
    print(f'❌ Import error: {e}')
    print('💡 Try: pip install -r requirements.txt')
    exit(1)
"
echo ""

echo "======================================================================"
echo "✅ Setup Complete!"
echo "======================================================================"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Edit your .env file with API credentials:"
echo "   nano .env"
echo ""
echo "2. Download YouTube OAuth credentials:"
echo "   • Go to: https://console.cloud.google.com/"
echo "   • Enable YouTube Data API v3"
echo "   • Download OAuth credentials"
echo "   • Save as: config/youtube_credentials.json"
echo ""
echo "3. Start the application:"
echo "   python -m uvicorn app.main:app --reload"
echo ""
echo "4. Test automation (dry run):"
echo "   python scripts/run_automation.py --dry-run"
echo ""
echo "📖 Full documentation: docs/AUTOMATION_GUIDE.md"
echo ""

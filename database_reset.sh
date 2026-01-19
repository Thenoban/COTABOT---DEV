#!/bin/bash

# Cotabot DEV - Database Reset Script
# Usage: sudo bash database_reset.sh

set -e

cd /DATA/AppData/COTABOT/COTABOT\ -\ DEV

echo "=========================================="
echo "Cotabot DEV - Database Reset"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will DELETE the current database!"
echo "This is safe for DEV environment."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled."
    exit 0
fi

echo ""
echo "📦 Step 1: Backing up old database..."
BACKUP_NAME="cotabot_dev.db.old_$(date +%Y%m%d_%H%M%S)"
mv cotabot_dev.db "$BACKUP_NAME"
echo "✅ Old database backed up as: $BACKUP_NAME"
echo ""

echo "🔧 Step 2: Creating fresh database..."
python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/DATA/AppData/COTABOT/COTABOT - DEV')

from database.adapter import DatabaseAdapter

# Create new database
print("Creating tables...")
db = DatabaseAdapter('sqlite:///cotabot_dev.db')

# Initialize database (create all tables)
from database.models import Base
Base.metadata.create_all(db.engine)

print("✅ Database created successfully!")
print("\nTables created:")
for table in Base.metadata.sorted_tables:
    print(f"  - {table.name}")
PYTHON_SCRIPT

echo ""
echo "✅ Step 3: Fresh database created!"
echo ""

echo "🔄 Step 4: Restarting bot container..."
sudo docker compose restart cotabot-dev
echo "✅ Container restarted"
echo ""

echo "=========================================="
echo "✅ Database Reset Complete!"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo "1. Monitor logs: sudo docker logs -f cotabot-dev"
echo "2. No more 'malformed' errors should appear"
echo "3. Database is clean and ready to use"
echo ""
echo "ℹ️  Note: All old data is in: $BACKUP_NAME"
echo ""

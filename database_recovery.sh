#!/bin/bash

# Cotabot Database Recovery Script
# Usage: sudo bash database_recovery.sh

set -e

cd /DATA/AppData/COTABOT/COTABOT\ -\ DEV

echo "=========================================="
echo "Cotabot Database Recovery"
echo "=========================================="
echo ""

# 1. Backup
echo "📦 Step 1: Creating backup..."
BACKUP_NAME="cotabot_dev.db.corrupt_$(date +%Y%m%d_%H%M%S)"
cp cotabot_dev.db "$BACKUP_NAME"
echo "✅ Backup created: $BACKUP_NAME"
echo ""

# 2. Integrity check
echo "🔍 Step 2: Checking integrity..."
sqlite3 cotabot_dev.db "PRAGMA integrity_check;" > integrity_check.log 2>&1 || true
echo "Integrity check result:"
cat integrity_check.log
echo ""

# 3. Recovery
echo "🔧 Step 3: Attempting recovery..."
sqlite3 cotabot_dev.db ".recover" | sqlite3 cotabot_dev_recovered.db 2>&1 || {
    echo "❌ Recovery failed!"
    exit 1
}
echo "✅ Recovery completed"
echo ""

# 4. Verify recovered db
echo "✅ Step 4: Verifying recovered database..."
VERIFY_RESULT=$(sqlite3 cotabot_dev_recovered.db "PRAGMA integrity_check;" 2>&1)
echo "Verification: $VERIFY_RESULT"

if [ "$VERIFY_RESULT" != "ok" ]; then
    echo "⚠️  Warning: Recovered database may still have issues"
fi
echo ""

# 5. Check table counts
echo "📊 Step 5: Checking table counts..."
echo "Events:         $(sqlite3 cotabot_dev_recovered.db 'SELECT COUNT(*) FROM events' 2>/dev/null || echo 'ERROR')"
echo "Players:        $(sqlite3 cotabot_dev_recovered.db 'SELECT COUNT(*) FROM players' 2>/dev/null || echo 'ERROR')"
echo "Voice Sessions: $(sqlite3 cotabot_dev_recovered.db 'SELECT COUNT(*) FROM voice_sessions' 2>/dev/null || echo 'ERROR')"
echo "Web Actions:    $(sqlite3 cotabot_dev_recovered.db 'SELECT COUNT(*) FROM web_bot_actions' 2>/dev/null || echo 'ERROR')"
echo ""

# 6. Prompt for replacement
echo "=========================================="
echo "⚠️  Ready to replace database"
echo "=========================================="
echo "Old database will be kept as: cotabot_dev.db.old"
echo ""
read -p "Continue with replacement? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo ""
    echo "🔄 Step 6: Replacing database..."
    mv cotabot_dev.db cotabot_dev.db.old
    mv cotabot_dev_recovered.db cotabot_dev.db
    echo "✅ Database replaced!"
    echo ""
    
    # 7. Restart bot
    echo "🔄 Step 7: Restarting bot container..."
    sudo docker compose restart cotabot-dev
    echo "✅ Container restarted"
    echo ""
    
    echo "=========================================="
    echo "✅ Recovery Complete!"
    echo "=========================================="
    echo ""
    echo "📝 Next steps:"
    echo "1. Monitor logs: sudo docker logs -f cotabot-dev"
    echo "2. Check for 'malformed' errors"
    echo "3. Test voice sessions, player stats, events"
    echo ""
    echo "📁 Backups:"
    echo "- Corrupt DB: $BACKUP_NAME"
    echo "- Old DB: cotabot_dev.db.old"
    echo ""
else
    echo ""
    echo "❌ Database NOT replaced."
    echo "Recovered database saved as: cotabot_dev_recovered.db"
    echo "You can manually replace it later if needed."
    echo ""
fi

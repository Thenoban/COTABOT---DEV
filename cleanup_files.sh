#!/bin/bash

# Cotabot Code Cleanup Script
# Removes 26 unnecessary migration/fix scripts

set -e

cd /DATA/AppData/COTABOT/COTABOT\ -\ DEV

echo "=========================================="
echo "Cotabot Code Cleanup"
echo "=========================================="
echo ""
echo "This script will DELETE 26 files:"
echo ""
echo "📦 Migration Scripts (6 files)"
echo "🔧 Fix Scripts (13 files)"
echo "➕ Add/Generate Scripts (4 files)"
echo "🗂️  Database redundant (1 file)"
echo "📁 Archive (2 files moved)"
echo ""
echo "⚠️  WARNING: Files will be permanently deleted!"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled."
    exit 0
fi

echo ""
echo "🗑️  Starting cleanup..."
echo ""

# Create archive folder
mkdir -p migration_archive

# Migration Scripts
echo "📦 Deleting migration scripts..."
rm -f migrate_db_indir.py
rm -f migrate_delete.py
rm -f migrate_player_add.py
rm -f migrate_report_logic.py
rm -f migrate_search.py
rm -f migrate_stats_sync.py
echo "✅ 6 migration scripts deleted"

# Fix Scripts
echo "🔧 Deleting fix scripts..."
rm -f fix_action_message.py
rm -f fix_adapter.py
rm -f fix_chart.py
rm -f fix_datetime.py
rm -f fix_detached.py
rm -f fix_dropdown_cache.py
rm -f fix_event.py
rm -f fix_indent.py
rm -f fix_old_events.py
rm -f fix_panel_count.py
rm -f fix_player_hybrid.py
rm -f fix_search_final.py
rm -f fix_select_view.py
echo "✅ 13 fix scripts deleted"

# Add/Generate Scripts
echo "➕ Deleting add/generate scripts..."
rm -f add_adapter_report_methods.py
rm -f add_delete_method.py
rm -f add_report_models.py
rm -f generate_report_methods.py
echo "✅ 4 add/generate scripts deleted"

# Create Scripts
echo "🏗️  Deleting create scripts..."
rm -f create_chart_maker.py
rm -f create_report_tables.py
echo "✅ 2 create scripts deleted"

# Database redundant
echo "🗂️  Deleting redundant database file..."
rm -f database/report_models.py
echo "✅ 1 redundant file deleted"

# Archive final migration files
echo "📁 Archiving final migration files..."
mv -f final_migration_batch.py migration_archive/ 2>/dev/null || echo "  (final_migration_batch.py not found)"
mv -f complete_final_migration.py migration_archive/ 2>/dev/null || echo "  (complete_final_migration.py not found)"
echo "✅ Migration files archived"

# Also delete the helper scripts we just created
echo "🧹 Cleaning up helper scripts..."
rm -f add_post_endpoint.py
rm -f add_activity_endpoint.py
rm -f cleanup_delete.py
echo "✅ Helper scripts deleted"

echo ""
echo "=========================================="
echo "✅ Cleanup Complete!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "  - Migration scripts: 6 deleted"
echo "  - Fix scripts: 13 deleted"
echo "  - Add/Generate scripts: 4 deleted"
echo "  - Create scripts: 2 deleted"
echo "  - Redundant files: 1 deleted"
echo "  - Helper scripts: 3 deleted"
echo "  - Archived: 2 files"
echo ""
echo "  Total: 29 files removed ✨"
echo ""
echo "📁 Files kept:"
echo "  - check_db.py"
echo "  - test_snapshot.py"
echo "  - check_keys.py"
echo "  - check_web_bridge.py (useful for debugging)"
echo ""

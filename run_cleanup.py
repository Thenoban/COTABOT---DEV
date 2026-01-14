"""
Cleanup Script - Gereksiz dosyaları temizler
CLEANUP_LIST.txt'e göre migration ve fix scriptlerini siler
"""
import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path(r'\\192.168.1.174\cotabot\COTABOT - DEV')

# Silinecek dosyalar (CLEANUP_LIST.txt'ten)
FILES_TO_DELETE = [
    # Migration Scripts (6 files)
    'migrate_db_indir.py',
    'migrate_delete.py',
    'migrate_player_add.py',
    'migrate_report_logic.py',
    'migrate_search.py',
    'migrate_stats_sync.py',
    
    # Fix Scripts (13 files)
    'fix_action_message.py',
    'fix_adapter.py',
    'fix_chart.py',
    'fix_datetime.py',
    'fix_detached.py',
    'fix_dropdown_cache.py',
    'fix_event.py',
    'fix_indent.py',
    'fix_old_events.py',
    'fix_panel_count.py',
    'fix_player_hybrid.py',
    'fix_search_final.py',
    'fix_select_view.py',
    
    # Add/Generate Scripts (4 files)
    'add_adapter_report_methods.py',
    'add_delete_method.py',
    'add_report_models.py',
    'generate_report_methods.py',
    
    # Create Scripts (2 files)
    'create_chart_maker.py',
    'create_report_tables.py',
    
    # Database redundant file (1 file)
    'database/report_models.py',
]

# Arşivlenecek dosyalar
FILES_TO_ARCHIVE = [
    'final_migration_batch.py',
    'complete_final_migration.py',
]


def main():
    print("=" * 60)
    print("COTABOT CLEANUP SCRIPT")
    print("=" * 60)
    
    # Archive klasörünü oluştur
    archive_dir = BASE_DIR / 'migration_archive'
    archive_dir.mkdir(exist_ok=True)
    print(f"\n[OK] Archive directory: {archive_dir}")
    
    # Dosyaları sil
    print("\n--- DELETING FILES ---")
    deleted_count = 0
    not_found_count = 0
    
    for filename in FILES_TO_DELETE:
        filepath = BASE_DIR / filename
        
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"[OK] Deleted: {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Error deleting {filename}: {e}")
        else:
            print(f"⚠ Not found: {filename}")
            not_found_count += 1
    
    # Dosyaları arşivle
    print("\n--- ARCHIVING FILES ---")
    archived_count = 0
    
    for filename in FILES_TO_ARCHIVE:
        src_path = BASE_DIR / filename
        dst_path = archive_dir / filename
        
        if src_path.exists():
            try:
                shutil.move(str(src_path), str(dst_path))
                print(f"[OK] Archived: {filename}")
                archived_count += 1
            except Exception as e:
                print(f"[ERROR] Error archiving {filename}: {e}")
        else:
            print(f"⚠ Not found: {filename}")
    
    # Özet
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Files deleted:     {deleted_count}/{len(FILES_TO_DELETE)}")
    print(f"Files not found:   {not_found_count}/{len(FILES_TO_DELETE)}")
    print(f"Files archived:    {archived_count}/{len(FILES_TO_ARCHIVE)}")
    print("\n[OK] Cleanup completed!")
    print("=" * 60)
    
    # Silinmesi gereken ama bulunamayan dosyalar
    if not_found_count > 0:
        print("\nNote: Some files were not found.")
        print("They may have been already deleted or never existed.")


if __name__ == '__main__':
    main()

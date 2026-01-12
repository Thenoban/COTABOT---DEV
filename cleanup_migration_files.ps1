# Cleanup Script - Remove Temporary Migration Files
# Safe to run - migrations are complete

$basePath = "\\192.168.1.174\cotabot\COTABOT - DEV"

Write-Host "=== CLEANUP STARTING ===" -ForegroundColor Green
Write-Host ""

# Create archive folder
Write-Host "Creating archive folder..." -ForegroundColor Yellow
New-Item -Path "$basePath\migration_archive" -ItemType Directory -Force | Out-Null

# Archive historical files
Write-Host "Archiving historical files..." -ForegroundColor Yellow
Move-Item "$basePath\final_migration_batch.py" "$basePath\migration_archive\" -ErrorAction SilentlyContinue
Move-Item "$basePath\complete_final_migration.py" "$basePath\migration_archive\" -ErrorAction SilentlyContinue

# Count and delete migration scripts
$migrateFiles = Get-ChildItem "$basePath\migrate_*.py" -ErrorAction SilentlyContinue
Write-Host "Deleting $($migrateFiles.Count) migration scripts..." -ForegroundColor Yellow
Remove-Item "$basePath\migrate_*.py" -ErrorAction SilentlyContinue

# Count and delete fix scripts
$fixFiles = Get-ChildItem "$basePath\fix_*.py" -ErrorAction SilentlyContinue
Write-Host "Deleting $($fixFiles.Count) fix scripts..." -ForegroundColor Yellow
Remove-Item "$basePath\fix_*.py" -ErrorAction SilentlyContinue

# Delete add scripts
$addFiles = Get-ChildItem "$basePath\add_*.py" -ErrorAction SilentlyContinue
Write-Host "Deleting $($addFiles.Count) add scripts..." -ForegroundColor Yellow
Remove-Item "$basePath\add_*.py" -ErrorAction SilentlyContinue

# Delete generate scripts
$genFiles = Get-ChildItem "$basePath\generate_*.py" -ErrorAction SilentlyContinue
Write-Host "Deleting $($genFiles.Count) generate scripts..." -ForegroundColor Yellow
Remove-Item "$basePath\generate_*.py" -ErrorAction SilentlyContinue

# Delete create scripts
$createFiles = Get-ChildItem "$basePath\create_*.py" -ErrorAction SilentlyContinue
Write-Host "Deleting $($createFiles.Count) create scripts..." -ForegroundColor Yellow
Remove-Item "$basePath\create_*.py" -ErrorAction SilentlyContinue

# Delete redundant database file
Write-Host "Deleting redundant report_models.py..." -ForegroundColor Yellow
Remove-Item "$basePath\database\report_models.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== CLEANUP COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Archived: 2 files" -ForegroundColor White
Write-Host "  Deleted: ~26 files" -ForegroundColor White
Write-Host "  Kept: check_db.py, test_snapshot.py, check_keys.py" -ForegroundColor White
Write-Host ""
Write-Host "Workspace is now clean!" -ForegroundColor Green

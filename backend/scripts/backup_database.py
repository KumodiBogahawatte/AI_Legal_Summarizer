"""
PostgreSQL Database Backup Script

Automated backup script for PostgreSQL database with retention policy.

Usage:
    python backup_database.py [--output-dir DIRECTORY] [--keep-days DAYS]

Examples:
    python backup_database.py
    python backup_database.py --output-dir /backups --keep-days 30
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess
import os
from datetime import datetime, timedelta
from app.config import (
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, 
    POSTGRES_PORT, POSTGRES_DB, BACKUP_DIR, BACKUP_RETENTION_DAYS,
    DATABASE_TYPE
)
import argparse

def create_backup(output_dir: str = None, verbose: bool = True):
    """Create a PostgreSQL database backup"""
    
    if DATABASE_TYPE != "postgresql":
        print("⚠️  Backup script is for PostgreSQL only")
        print(f"Current database type: {DATABASE_TYPE}")
        return None
    
    # Setup backup directory
    backup_path = Path(output_dir) if output_dir else Path(BACKUP_DIR)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"ai_legal_db_backup_{timestamp}.sql"
    
    if verbose:
        print("=" * 60)
        print("PostgreSQL Database Backup")
        print("=" * 60)
        print(f"\n📂 Backup directory: {backup_path}")
        print(f"📄 Backup file: {backup_file.name}")
        print(f"🗄️  Database: {POSTGRES_DB}")
        print(f"🖥️  Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
        print(f"\n⏳ Starting backup...")
    
    # Set environment variable for password
    env = os.environ.copy()
    env['PGPASSWORD'] = POSTGRES_PASSWORD
    
    # Construct pg_dump command
    cmd = [
        'pg_dump',
        '-h', POSTGRES_HOST,
        '-p', str(POSTGRES_PORT),
        '-U', POSTGRES_USER,
        '-d', POSTGRES_DB,
        '-F', 'p',  # Plain text format
        '-f', str(backup_file),
        '--no-owner',
        '--no-privileges',
    ]
    
    try:
        # Run pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if backup file was created
        if backup_file.exists():
            file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
            if verbose:
                print(f"\n✅ Backup completed successfully!")
                print(f"📦 Backup size: {file_size:.2f} MB")
                print(f"📍 Location: {backup_file}")
            return backup_file
        else:
            print(f"\n❌ Backup file was not created")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Backup failed!")
        print(f"Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print(f"\n❌ pg_dump command not found!")
        print("Please ensure PostgreSQL client tools are installed and in PATH")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return None

def cleanup_old_backups(backup_dir: str = None, keep_days: int = None, verbose: bool = True):
    """Delete backups older than retention period"""
    
    backup_path = Path(backup_dir) if backup_dir else Path(BACKUP_DIR)
    retention_days = keep_days if keep_days else BACKUP_RETENTION_DAYS
    
    if not backup_path.exists():
        if verbose:
            print(f"\n⚠️  Backup directory does not exist: {backup_path}")
        return
    
    if verbose:
        print(f"\n🧹 Cleaning up backups older than {retention_days} days...")
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0
    deleted_size = 0
    
    # Find and delete old backups
    for backup_file in backup_path.glob("ai_legal_db_backup_*.sql"):
        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        
        if file_time < cutoff_date:
            file_size = backup_file.stat().st_size
            backup_file.unlink()
            deleted_count += 1
            deleted_size += file_size
            if verbose:
                print(f"   🗑️  Deleted: {backup_file.name} (from {file_time.strftime('%Y-%m-%d')})")
    
    if verbose:
        if deleted_count > 0:
            print(f"\n✅ Cleaned up {deleted_count} old backup(s), freed {deleted_size / (1024*1024):.2f} MB")
        else:
            print(f"\n✅ No old backups to clean up")

def list_backups(backup_dir: str = None):
    """List all available backups"""
    
    backup_path = Path(backup_dir) if backup_dir else Path(BACKUP_DIR)
    
    if not backup_path.exists():
        print(f"\n⚠️  Backup directory does not exist: {backup_path}")
        return
    
    backups = sorted(backup_path.glob("ai_legal_db_backup_*.sql"), reverse=True)
    
    if not backups:
        print(f"\n📂 No backups found in: {backup_path}")
        return
    
    print("\n" + "=" * 80)
    print(f"Available Backups ({len(backups)} total)")
    print("=" * 80)
    print(f"{'Backup File':<45} {'Date':<20} {'Size':<10}")
    print("-" * 80)
    
    for backup in backups:
        stat = backup.stat()
        size_mb = stat.st_size / (1024 * 1024)
        date = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{backup.name:<45} {date:<20} {size_mb:>6.2f} MB")
    
    print("-" * 80)

def restore_backup(backup_file: str, verbose: bool = True):
    """Restore database from a backup file"""
    
    if DATABASE_TYPE != "postgresql":
        print("⚠️  Restore script is for PostgreSQL only")
        return False
    
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        print(f"\n❌ Backup file not found: {backup_file}")
        return False
    
    if verbose:
        print("=" * 60)
        print("PostgreSQL Database Restore")
        print("=" * 60)
        print(f"\n⚠️  WARNING: This will overwrite the current database!")
        print(f"📄 Backup file: {backup_path.name}")
        print(f"🗄️  Target database: {POSTGRES_DB}")
        
        confirm = input("\nType 'YES' to confirm restore: ")
        if confirm != 'YES':
            print("❌ Restore cancelled")
            return False
    
    # Set environment variable for password
    env = os.environ.copy()
    env['PGPASSWORD'] = POSTGRES_PASSWORD
    
    # Construct psql command
    cmd = [
        'psql',
        '-h', POSTGRES_HOST,
        '-p', str(POSTGRES_PORT),
        '-U', POSTGRES_USER,
        '-d', POSTGRES_DB,
        '-f', str(backup_path),
    ]
    
    try:
        if verbose:
            print(f"\n⏳ Restoring database...")
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        if verbose:
            print(f"\n✅ Database restored successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Restore failed!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PostgreSQL Database Backup Manager")
    parser.add_argument('--output-dir', type=str, 
                       help=f'Backup directory (default: {BACKUP_DIR})')
    parser.add_argument('--keep-days', type=int, 
                       help=f'Keep backups for N days (default: {BACKUP_RETENTION_DAYS})')
    parser.add_argument('--list', action='store_true',
                       help='List all available backups')
    parser.add_argument('--restore', type=str, metavar='BACKUP_FILE',
                       help='Restore database from backup file')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Skip cleanup of old backups')
    
    args = parser.parse_args()
    
    if args.list:
        list_backups(args.output_dir)
    elif args.restore:
        restore_backup(args.restore)
    else:
        # Create backup
        backup_file = create_backup(args.output_dir)
        
        # Cleanup old backups unless --no-cleanup is specified
        if backup_file and not args.no_cleanup:
            cleanup_old_backups(args.output_dir, args.keep_days)

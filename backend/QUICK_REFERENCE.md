# Database Migration - Quick Reference

## 🚀 Quick Start

```powershell
# Navigate to backend
cd backend

# Run automated setup
./scripts/setup_database.ps1

# Start application
uvicorn app.main:app --reload
```

## 📋 Manual Steps

### 1. Install PostgreSQL

Download from: https://www.postgresql.org/download/windows/

### 2. Create Database

```sql
psql -U postgres
CREATE DATABASE ai_legal_summarizer;
\q
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Run Migration

```bash
python scripts/migrate_to_postgresql.py
```

## 🔄 Common Commands

### Start Application

```bash
uvicorn app.main:app --reload
```

### Create Backup

```bash
python scripts/backup_database.py
```

### List Backups

```bash
python scripts/backup_database.py --list
```

### Restore Backup

```bash
python scripts/backup_database.py --restore backups/backup_file.sql
```

### Generate Alembic Migration

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Verify Migration

```bash
python scripts/migrate_to_postgresql.py --verify-only
```

## 🗄️ Database Info

**Connection String:**

```
postgresql://postgres:password@localhost:5432/ai_legal_summarizer
```

**Tables:** 12 total

- 5 existing (migrated from SQLite)
- 7 new tables

## 🔧 Troubleshooting

### PostgreSQL not running?

```bash
# Windows: Check Services app
# Or restart service
net stop postgresql-x64-15
net start postgresql-x64-15
```

### Connection issues?

1. Check .env credentials
2. Verify PostgreSQL port (default: 5432)
3. Check firewall settings

### Migration errors?

1. Drop database and recreate
2. Check SQLite file exists
3. Verify all dependencies installed

## 📚 Documentation

- Full Guide: `DATABASE_SETUP.md`
- Completion Summary: `DATABASE_MIGRATION_COMPLETE.md`
- Build Roadmap: `BUILD_ROADMAP.md`

## ✅ What's Done

- [x] PostgreSQL configuration
- [x] 7 new database models
- [x] Migration script
- [x] Backup/restore system
- [x] Alembic setup
- [x] Documentation

## 🎯 Next: Section 1.2

Custom Legal NER Model Training - See `BUILD_ROADMAP.md`

# Database Setup Quick Start Script
# Run this script to quickly setup PostgreSQL database

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "AI Legal Summarizer - Database Setup"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Check if PostgreSQL is installed
$pgVersion = & pg_dump --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ PostgreSQL client tools not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install PostgreSQL from:" -ForegroundColor Yellow
    Write-Host "  https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "✅ PostgreSQL client tools found: $pgVersion" -ForegroundColor Green
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  Please edit .env file with your PostgreSQL credentials!" -ForegroundColor Yellow
    Write-Host ""
    $editNow = Read-Host "Open .env file now? (y/n)"
    if ($editNow -eq "y") {
        notepad .env
        Write-Host ""
        Write-Host "Press Enter after saving .env file..." -ForegroundColor Yellow
        Read-Host
    }
}

Write-Host "🔍 Checking database configuration..." -ForegroundColor Cyan

# Load .env file
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

$dbType = $env:DATABASE_TYPE
$dbName = $env:POSTGRES_DB
$dbUser = $env:POSTGRES_USER
$dbHost = $env:POSTGRES_HOST
$dbPort = $env:POSTGRES_PORT

Write-Host "  Database Type: $dbType" -ForegroundColor White
Write-Host "  Database Name: $dbName" -ForegroundColor White
Write-Host "  User: $dbUser" -ForegroundColor White
Write-Host "  Host: ${dbHost}:${dbPort}" -ForegroundColor White
Write-Host ""

if ($dbType -ne "postgresql") {
    Write-Host "⚠️  Database type is set to: $dbType" -ForegroundColor Yellow
    Write-Host "This script is for PostgreSQL setup." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}

# Test PostgreSQL connection
Write-Host "🔌 Testing PostgreSQL connection..." -ForegroundColor Cyan
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
$testConn = & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "SELECT 1;" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cannot connect to PostgreSQL!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure:" -ForegroundColor Yellow
    Write-Host "  1. PostgreSQL service is running" -ForegroundColor Yellow
    Write-Host "  2. Credentials in .env are correct" -ForegroundColor Yellow
    Write-Host "  3. PostgreSQL is accepting connections on port $dbPort" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host "✅ Connected to PostgreSQL successfully" -ForegroundColor Green
Write-Host ""

# Check if database exists
Write-Host "🔍 Checking if database '$dbName' exists..." -ForegroundColor Cyan
$dbExists = & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbName';" 2>$null
if ($dbExists -eq "1") {
    Write-Host "✅ Database '$dbName' already exists" -ForegroundColor Green
} else {
    Write-Host "📦 Database '$dbName' not found. Creating..." -ForegroundColor Yellow
    & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "CREATE DATABASE $dbName;" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database '$dbName' created successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create database" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Run migration
Write-Host "🚀 Running database migration..." -ForegroundColor Cyan
Write-Host ""
python scripts/migrate_to_postgresql.py

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start the backend: uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  2. Test API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  3. Setup automated backups (see DATABASE_SETUP.md)" -ForegroundColor White
Write-Host ""

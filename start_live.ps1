# DEVA Intelligence Live Launcher Script
# Starts PostgreSQL & Redis services, runs Live Ingestion & Processing, builds frontend and launches server on port 8000

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DEVA INTELLIGENCE • 100% Real-Time Production Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Purge & Seed Production Database
Write-Host "`n[1/3] Seeding Live Production Sources and Admin Account..." -ForegroundColor Yellow
cd c:\Users\ddnan\DEVA_Intelligence\backend
python scripts/purge_and_seed_live.py

# 2. Run Live Pipeline (Fetch arXiv, GitHub, Hugging Face, Blogs)
Write-Host "`n[2/3] Fetching and Processing Real-Time Intelligence..." -ForegroundColor Yellow
python scripts/run_live_pipeline.py

# 3. Build Frontend & Serve
Write-Host "`n[3/3] Building Frontend Production Assets..." -ForegroundColor Yellow
cd c:\Users\ddnan\DEVA_Intelligence\frontend
npm run build

Write-Host "`n[4/4] Launching Persistent Background Celery Worker..." -ForegroundColor Yellow
cd c:\Users\ddnan\DEVA_Intelligence\backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "celery -A app.workers.celery_app worker --pool=solo --loglevel=info -Q ingestion,processing,agents" -WindowStyle Minimized

Write-Host "`n--> DEVA Intelligence is live on http://127.0.0.1:8000" -ForegroundColor Green
cd c:\Users\ddnan\DEVA_Intelligence\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc
from pydantic import BaseModel
import schedule
import time
import threading

from database import get_session, init_db
from models import Site, Category, UrlRecord
from main import job  # Import the monitoring job logic

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Schemas ---
class SiteCreate(BaseModel):
    name: str
    sitemap_url: str
    category_id: int
    active: bool = True

class SiteRead(BaseModel):
    id: int
    name: str
    sitemap_url: str
    active: bool
    category_name: Optional[str] = None
    last_check_time: Optional[datetime] = None
    new_urls_count: int = 0

class CategoryCreate(BaseModel):
    name: str

class CategoryRead(BaseModel):
    id: int
    name: str

class DashboardStats(BaseModel):
    total_sites: int
    total_urls: int
    new_urls_24h: int

# --- Background Scheduler ---
def run_scheduler():
    logging.info("Scheduler thread started")
    schedule.every(1).hours.do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    yield
    # Shutdown logic if needed

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# --- Dependencies ---
def get_db():
    with get_session() as session:
        yield session

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/init")
async def init_data(db: Session = Depends(get_db)):
    # Ensure General category
    cat = db.exec(select(Category).where(Category.name == "General")).first()
    if not cat:
        db.add(Category(name="General"))
        db.commit()
    return {"status": "ok"}

@app.get("/api/stats", response_model=DashboardStats)
async def get_stats(db: Session = Depends(get_db)):
    total_sites = db.exec(select(func.count(Site.id))).one()
    total_urls = db.exec(select(func.count(UrlRecord.id))).one()
    
    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) # Simple approximation or exactly 24h
    # For actual "last 24 hours":
    cutoff = datetime.now().timestamp() - 86400
    # SQLModel datetime query might vary by DB, doing naive approach for compatibility:
    # Actually UrlRecord.first_seen_time is datetime
    # Let's count records with is_new=True (which reset each run) OR specific time range.
    # The current logic sets is_new=True only for the latest batch. 
    # Let's just count all URLs found in last 24h.
    
    # SQLite/MySQL syntax difference awareness: SQLModel abstracts this mostly.
    # But `datetime.now() - timedelta(days=1)` in Python passed as param is safest.
    import datetime as dt
    cutoff_dt = dt.datetime.now() - dt.timedelta(days=1)
    new_urls_24h = db.exec(select(func.count(UrlRecord.id)).where(UrlRecord.first_seen_time >= cutoff_dt)).one()

    return DashboardStats(total_sites=total_sites, total_urls=total_urls, new_urls_24h=new_urls_24h)

@app.get("/api/categories", response_model=List[CategoryRead])
async def read_categories(db: Session = Depends(get_db)):
    cats = db.exec(select(Category)).all()
    return cats

@app.post("/api/categories", response_model=CategoryRead)
async def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_cat = Category(name=category.name)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@app.get("/api/sites", response_model=List[SiteRead])
async def read_sites(db: Session = Depends(get_db)):
    sites = db.exec(select(Site)).all()
    result = []
    for s in sites:
        # Count new urls for this site (e.g. is_new=True) to show recent activity status
        # new_count = db.exec(select(func.count(UrlRecord.id)).where(UrlRecord.site_id == s.id, UrlRecord.is_new == True)).one()
        # Just simple mapping
        result.append(SiteRead(
            id=s.id, 
            name=s.name, 
            sitemap_url=s.sitemap_url, 
            active=s.active,
            category_name=s.category.name if s.category else "None",
            last_check_time=s.last_check_time,
            new_urls_count=0 # Placeholder or calc if expensive
        ))
    return result

@app.post("/api/sites", response_model=SiteRead)
async def create_site(site: SiteCreate, db: Session = Depends(get_db)):
    db_site = Site.from_orm(site)
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return SiteRead(
        id=db_site.id,
        name=db_site.name,
        sitemap_url=db_site.sitemap_url,
        active=db_site.active,
        category_name=db_site.category.name if db_site.category else "None",
        last_check_time=db_site.last_check_time
    )

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Delete related records
    urls = db.exec(select(UrlRecord).where(UrlRecord.site_id == site_id)).all()
    for u in urls:
        db.delete(u)
        
    db.delete(site)
    db.commit()
    return {"ok": True}

@app.post("/api/run-now")
async def trigger_run():
    # Run job in background thread to avoid blocking API
    threading.Thread(target=job).start()
    return {"status": "Job started in background"}

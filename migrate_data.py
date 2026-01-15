import json
import os
import yaml
from pathlib import Path
from sqlmodel import Session, select
from models import Site, UrlRecord, Category
from database import get_session, init_db

def migrate_data():
    init_db()
    session = get_session()
    
    # 1. Ensure default categories exist
    default_cat_name = "General"
    default_cat = session.exec(select(Category).where(Category.name == default_cat_name)).first()
    if not default_cat:
        default_cat = Category(name=default_cat_name)
        session.add(default_cat)
        session.commit()
        session.refresh(default_cat)
    
    # 2. Sync Sites from config.yaml
    if os.path.exists('config.yaml'):
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        print("Syncing sites from config.yaml...")
        for site_conf in config.get('sites', []):
            name = site_conf.get('name')
            if not name: continue
            
            # Check if site exists
            site = session.exec(select(Site).where(Site.name == name)).first()
            if not site:
                print(f"Creating new site from config: {name}")
                sitemap_urls = site_conf.get('sitemap_urls', [])
                sitemap_url = sitemap_urls[0] if sitemap_urls else ""
                
                site = Site(
                    name=name,
                    sitemap_url=sitemap_url,
                    active=site_conf.get('active', True),
                    category_id=default_cat.id
                )
                session.add(site)
            else:
                # Update existing site config if needed (optional, here we ensure sitemap_url is up to date)
                sitemap_urls = site_conf.get('sitemap_urls', [])
                if sitemap_urls:
                    site.sitemap_url = sitemap_urls[0]
                    session.add(site)
        session.commit()
        print("Config sync complete.")

    # 3. Import Historical Data from JSON files
    base_dir = Path('latest')
    if not base_dir.exists():
        print("No 'latest' directory found. Skipping history import.")
        return

    print("Importing historical data from 'latest/' directory...")
    for file_path in base_dir.glob('*.json'):
        if not file_path.is_file():
            continue
            
        site_name = file_path.stem
        
        # Get Site
        site = session.exec(select(Site).where(Site.name == site_name)).first()
        if not site:
            print(f"Warning: Site '{site_name}' found in latest/ but not in DB (and not in config). Skipping.")
            continue
        
        # Read URLs
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                continue
            urls = content.splitlines()
            
        # Bulk Insert URLs
        # To avoid massive slow-down, we fetch all existing URLs for this site first
        existing_urls = set(session.exec(select(UrlRecord.url).where(UrlRecord.site_id == site.id)).all())
        
        new_records = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            if url not in existing_urls:
                new_records.append(UrlRecord(
                    url=url,
                    site_id=site.id,
                    is_new=False # Historical data
                ))
                existing_urls.add(url) # Update local set to avoid dupes within the file itself
        
        if new_records:
            session.add_all(new_records)
            session.commit()
            print(f"  Imported {len(new_records)} new URLs for {site_name}")
        else:
            print(f"  No new URLs to import for {site_name}")

if __name__ == "__main__":
    migrate_data()

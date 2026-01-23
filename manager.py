import typer
import sys
from typing import Optional
from sqlmodel import select, Session
from models import Site, Category, UrlRecord
from database import get_session, init_db

app = typer.Typer()

@app.command()
def list_sites():
    """List all sites."""
    session = get_session()
    sites = session.exec(select(Site)).all()
    print(f"{'ID':<5} {'Name':<25} {'Category':<15} {'Active':<10} {'Sitemap URL'}")
    print("-" * 80)
    for site in sites:
        cat_name = site.category.name if site.category else "None"
        print(f"{site.id:<5} {site.name:<25} {cat_name:<15} {str(site.active):<10} {site.sitemap_url}")

@app.command()
def add_site(name: str, sitemap_url: str, category: str = "General", active: bool = True):
    """Add a new site."""
    session = get_session()
    
    # Check category
    cat = session.exec(select(Category).where(Category.name == category)).first()
    if not cat:
        print(f"Category '{category}' not found. Creating it.")
        cat = Category(name=category)
        session.add(cat)
        session.commit()
        session.refresh(cat)
    
    site = Site(name=name, sitemap_url=sitemap_url, active=active, category_id=cat.id)
    try:
        session.add(site)
        session.commit()
        print(f"Site '{name}' added successfully.")
    except Exception as e:
        print(f"Error adding site: {e}")

@app.command()
def add_category(name: str):
    """Add a new category."""
    session = get_session()
    if session.exec(select(Category).where(Category.name == name)).first():
        print("Category already exists.")
        return
    session.add(Category(name=name))
    session.commit()
    print(f"Category '{name}' added.")

@app.command()
def stats():
    """Show basic stats."""
    session = get_session()
    from sqlmodel import func
    total_sites = session.exec(select(func.count(Site.id))).one()
    total_urls = session.exec(select(func.count(UrlRecord.id))).one()
    print(f"Total Sites: {total_sites}")
    print(f"Total URLs Tracked: {total_urls}")

if __name__ == "__main__":
    init_db()
    app()

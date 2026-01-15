from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    
    sites: list["Site"] = Relationship(back_populates="category")

class Site(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: Optional[str] = None
    sitemap_url: str
    active: bool = Field(default=True)
    last_check_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="sites")
    url_records: list["UrlRecord"] = Relationship(back_populates="site")

class UrlRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    first_seen_time: datetime = Field(default_factory=datetime.now)
    is_new: bool = Field(default=True) # Flag to indicate if this is a newly discovered URL in the latest batch
    
    site_id: Optional[int] = Field(default=None, foreign_key="site.id")
    site: Optional[Site] = Relationship(back_populates="url_records")

from sqlmodel import create_engine, SQLModel, Session
import pymysql
import yaml
import os

def load_config(config_path='config.yaml'):
    if not os.path.exists(config_path):
         return {}
    with open(config_path) as f:
        return yaml.safe_load(f)

# Global engine variable
engine = None

def get_db_url(config):
    # Validates if running inside Docker or with ENV vars set
    db_type = os.getenv('DB_TYPE', config.get('database', {}).get('type', 'mysql'))
    user = os.getenv('DB_USER', config.get('database', {}).get('user', 'root'))
    password = os.getenv('DB_PASSWORD', config.get('database', {}).get('password', ''))
    host = os.getenv('DB_HOST', config.get('database', {}).get('host', 'localhost'))
    port = os.getenv('DB_PORT', config.get('database', {}).get('port', 3306))
    name = os.getenv('DB_NAME', config.get('database', {}).get('name', 'sitemapmonitor'))
    
    if db_type == 'sqlite':
        return f"sqlite:///{name}.db"
    
    # pymysql connection string
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

def init_db(config_path='config.yaml'):
    global engine
    config = load_config(config_path)
    if 'database' not in config:
        print("Database configuration missing in config.yaml")
        return
        
    db_url = get_db_url(config)
    engine = create_engine(db_url, echo=False)
    
    # Create tables
    SQLModel.metadata.create_all(engine)

def get_session():
    global engine
    if engine is None:
        init_db()
    return Session(engine)

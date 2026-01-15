import os
import json
import requests
import cloudscraper
import yaml
import gzip
import logging
import time
import hmac
import hashlib
import base64
import schedule
import argparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from models import Site, UrlRecord, Category
from database import get_session, init_db

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_sitemap(url):
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30)
        response.raise_for_status()

        content = response.content
        # 智能检测gzip格式
        if content[:2] == b'\x1f\x8b':  # gzip magic number
            content = gzip.decompress(content)

        if b'<urlset' in content:
            return parse_xml(content)
        else:
            return parse_txt(content.decode('utf-8'))
    except requests.RequestException as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error processing {url}: {str(e)}")
        return []

def parse_xml(content):
    urls = []
    soup = BeautifulSoup(content, 'xml')
    for loc in soup.find_all('loc'):
        url = loc.get_text().strip()
        if url:
            urls.append(url)
    return urls

def parse_txt(content):
    return [line.strip() for line in content.splitlines() if line.strip()]

def gen_sign(timestamp, secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def send_feishu_notification(new_urls, config, site_name):
    if not new_urls:
        return
    
    feishu_conf = config.get('feishu', {})
    webhook_url = feishu_conf.get('webhook_url')
    secret = feishu_conf.get('secret')
    
    if not webhook_url:
        logging.warning("Feishu webhook_url not configured.")
        return
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"🎮 {site_name} 游戏上新通知"},
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**今日新增 {len(new_urls)} 款游戏**\n\n" + "\n".join(f"• {url}" for url in new_urls[:10])
                    }
                }
            ]
        }
    }

    if secret:
        timestamp = int(time.time())
        sign = gen_sign(timestamp, secret)
        message["timestamp"] = str(timestamp)
        message["sign"] = sign
    
    # logging.info(f"Payload: {json.dumps(message, ensure_ascii=False)}")

    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=message)
            resp.raise_for_status()
            resp_json = resp.json()
            if resp_json.get("code") != 0:
                logging.error(f"飞书API报错: {resp_json}")
                continue
            logging.info("飞书通知发送成功")
            return
        except requests.RequestException as e:
            logging.error(f"飞书通知发送失败: {str(e)}")
            time.sleep(2)

def check_site(session: Session, site: Site, config):
    logging.info(f"Checking site: {site.name}")
    
    current_urls = []
    # Currently assuming single sitemap URL in DB, but model supports one. 
    # If multiple sitemaps needed per site, we need to iterate or change model.
    # For now, using site.sitemap_url
    
    sitemap_list = [site.sitemap_url] # Simplify for now
    
    all_qs = []
    for sm_url in sitemap_list:
        urls = process_sitemap(sm_url)
        all_qs.extend(urls)
        
    unique_urls = set(all_qs)
    
    new_found_urls = []
    
    for url in unique_urls:
        # Check if URL exists in DB
        exists = session.exec(select(UrlRecord).where(UrlRecord.url == url, UrlRecord.site_id == site.id)).first()
        if not exists:
            # Add new record
            record = UrlRecord(
                url=url,
                site_id=site.id,
                is_new=True
            )
            session.add(record)
            new_found_urls.append(url)
    
    site.last_check_time = datetime.now()
    session.add(site)
    session.commit()
    
    if new_found_urls:
        logging.info(f"Found {len(new_found_urls)} new URLs for {site.name}")
        send_feishu_notification(new_found_urls, config, site.name)
    else:
        logging.info(f"No new URLs for {site.name}")

def load_app_config():
    with open('config.yaml') as f:
        return yaml.safe_load(f)

def job():
    init_db()
    session = get_session()
    config = load_app_config()
    
    active_sites = session.exec(select(Site).where(Site.active == True)).all()
    if not active_sites:
        logging.info("No active sites found in database.")
        
        # Fallback: Check if we need to sync from config (for first run if valid)
        # But Manager CLI is preferred for adding sites.
        pass

    for site in active_sites:
        check_site(session, site, config)
    
    session.close()

def run_once():
    logging.info("Starting one-time check...")
    job()
    logging.info("Check complete.")

def run_daemon():
    logging.info("Starting daemon mode...")
    # Schedule to run every 1 hour, or customize via config
    schedule.every(1).hours.do(job)
    
    # Run immediately on start
    job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    args = parser.parse_args()
    
    # Ensure DB is ready
    init_db()
    
    if args.daemon:
        run_daemon()
    else:
        run_once()


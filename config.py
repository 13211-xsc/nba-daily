"""
NBA Daily Bot - 配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).parent / ".env")

# --- 项目路径 ---
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"
SENT_RECORDS_FILE = BASE_DIR / "sent_articles.json"

# --- 邮件配置（QQ邮箱）---
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465

# --- RSS 源列表（NBA 篮球）---
RSS_SOURCES = [
    {
        "name": "ESPN NBA",
        "url": "https://www.espn.com/espn/rss/nba/news",
    },
    {
        "name": "NBA.com",
        "url": "https://www.nba.com/rss",
    },
    {
        "name": "Yahoo Sports NBA",
        "url": "https://sports.yahoo.com/nba/rss.xml",
    },
    {
        "name": "Bleacher Report NBA",
        "url": "https://bleacherreport.com/nba.rss",
    },
]

# --- 文章筛选配置 ---
MIN_WORD_COUNT = 300      # 最少英文单词数
MAX_WORD_COUNT = 5000     # 最多英文单词数
MIN_IMAGE_COUNT = 1       # 最少图片数量

# --- HTTP 请求头 ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

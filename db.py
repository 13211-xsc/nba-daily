"""
NBA Daily Bot - SQLite 数据库层
存储已抓取的文章和翻译，避免重复抓取
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "nba_bot.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT,
            published TEXT,
            text_en TEXT,
            text_zh TEXT,
            image_paths TEXT,
            word_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def article_exists(url: str) -> bool:
    """检查文章URL是否已存在"""
    conn = get_db()
    row = conn.execute("SELECT id FROM articles WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def save_article(article: dict, translations: list[dict], image_paths: list[str]) -> int:
    """
    保存文章到数据库
    返回文章ID
    """
    conn = get_db()
    text_zh = json.dumps([t.get("zh", "") for t in translations], ensure_ascii=False)
    images = json.dumps(image_paths, ensure_ascii=False)

    pub = article.get("published")
    if hasattr(pub, "strftime"):
        published_str = pub.strftime("%Y-%m-%d %H:%M:%S")
    else:
        published_str = str(pub) if pub else ""

    cursor = conn.execute("""
        INSERT OR REPLACE INTO articles (title, url, source, published, text_en, text_zh, image_paths, word_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        article["title"],
        article["url"],
        article.get("source", ""),
        published_str,
        article.get("text", ""),
        text_zh,
        images,
        article.get("word_count", 0),
    ))
    conn.commit()
    article_id = cursor.lastrowid
    conn.close()
    return article_id


def get_today_article() -> dict | None:
    """获取今天的最新文章"""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute("""
        SELECT * FROM articles
        WHERE created_at LIKE ?
        ORDER BY id DESC LIMIT 1
    """, (f"{today}%",)).fetchone()
    conn.close()

    if row:
        return _row_to_dict(row)
    return None


def get_latest_article() -> dict | None:
    """获取最新一篇文章（不限日期）"""
    conn = get_db()
    row = conn.execute("SELECT * FROM articles ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return _row_to_dict(row)
    return None


def get_article_by_id(article_id: int) -> dict | None:
    """根据ID获取文章"""
    conn = get_db()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    if row:
        return _row_to_dict(row)
    return None


def get_history(limit: int = 30) -> list[dict]:
    """获取历史文章列表"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, source, published, word_count, created_at FROM articles ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    """将数据库行转为字典，并解析JSON字段"""
    d = dict(row)
    if d.get("text_zh"):
        try:
            d["translations"] = [
                {"en": "", "zh": zh}
                for zh in json.loads(d["text_zh"])
            ]
        except json.JSONDecodeError:
            d["translations"] = []
    if d.get("image_paths"):
        try:
            d["image_paths"] = json.loads(d["image_paths"])
        except json.JSONDecodeError:
            d["image_paths"] = []
    return d


# 启动时自动初始化
init_db()

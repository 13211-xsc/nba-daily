"""
🏀 NBA Daily - 手机App服务器
Flask + PWA，手机上点一下就看NBA双语新闻
"""
import io
import sys
import json
import socket
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_file

from config import BASE_DIR, OUTPUT_DIR
from db import (
    get_today_article, get_latest_article, get_article_by_id,
    get_history, save_article, article_exists,
)
from fetcher import (
    get_daily_article, download_article_images,
)
from translator import split_into_paragraphs, translate_article

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

app = Flask(__name__)
STATIC_DIR = BASE_DIR / "static"


# ─── 页面路由 ───

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


# ─── API ───

@app.route("/api/today")
def api_today():
    """获取今天的文章"""
    article = get_today_article()
    if not article:
        article = get_latest_article()

    if not article:
        return jsonify({"status": "empty", "message": "还没有文章，请先刷新"})

    # 将英文原文按段落分割
    en_paragraphs = article.get("text_en", "").split("\n\n")
    zh_list = article.get("translations", [])

    # 组合段落
    paragraphs = []
    for i, en in enumerate(en_paragraphs):
        zh = zh_list[i] if i < len(zh_list) else {"zh": ""}
        paragraphs.append({
            "en": en,
            "zh": zh.get("zh", "") if isinstance(zh, dict) else str(zh),
        })

    return jsonify({
        "status": "ok",
        "article": {
            "id": article["id"],
            "title": article["title"],
            "source": article["source"],
            "url": article["url"],
            "published": article.get("published", ""),
            "word_count": article.get("word_count", 0),
            "paragraphs": paragraphs,
            "images": article.get("image_paths", []),
        }
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """强制获取新文章"""
    logger.info("🔄 用户请求刷新...")

    # 1. 抓取
    article = get_daily_article()
    if not article:
        return jsonify({"status": "error", "message": "没找到合适的文章，请稍后再试"})

    # 2. 检查是否已存在
    if article_exists(article["url"]):
        return jsonify({"status": "ok", "message": "文章已存在", "cached": True})

    # 3. 翻译
    paragraphs = split_into_paragraphs(article["text"])
    translations = translate_article(paragraphs)

    # 4. 下载图片
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = OUTPUT_DIR / today_str
    date_dir.mkdir(parents=True, exist_ok=True)
    article = download_article_images(article, date_dir)

    image_paths = [
        {"path": img["local_path"], "alt": img.get("alt", "")}
        for img in article.get("local_images", [])
    ]

    # 5. 存数据库
    article_id = save_article(article, translations, image_paths)

    logger.info(f"✅ 新文章已保存 ID={article_id}: {article['title'][:60]}")

    return jsonify({
        "status": "ok",
        "message": "文章已更新",
        "article_id": article_id,
        "title": article["title"],
        "cached": False,
    })


@app.route("/api/history")
def api_history():
    """历史文章列表"""
    articles = get_history(30)
    return jsonify({"status": "ok", "articles": articles})


@app.route("/api/article/<int:article_id>")
def api_article(article_id):
    """获取指定文章详情"""
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({"status": "error", "message": "文章不存在"}), 404

    en_paragraphs = article.get("text_en", "").split("\n\n")
    zh_list = article.get("translations", [])

    paragraphs = []
    for i, en in enumerate(en_paragraphs):
        zh = zh_list[i] if i < len(zh_list) else {"zh": ""}
        paragraphs.append({
            "en": en,
            "zh": zh.get("zh", "") if isinstance(zh, dict) else str(zh),
        })

    return jsonify({
        "status": "ok",
        "article": {
            "id": article["id"],
            "title": article["title"],
            "source": article["source"],
            "url": article["url"],
            "published": article.get("published", ""),
            "word_count": article.get("word_count", 0),
            "paragraphs": paragraphs,
            "images": article.get("image_paths", []),
        }
    })


@app.route("/api/image/<path:date>/<path:filename>")
def serve_image(date, filename):
    """提供文章图片"""
    img_path = OUTPUT_DIR / date / "images" / filename
    if img_path.exists():
        return send_file(str(img_path))
    return "Not found", 404


# ─── PWA ───

@app.route("/manifest.json")
def manifest():
    """PWA manifest"""
    return send_file(str(STATIC_DIR / "manifest.json"))


@app.route("/sw.js")
def service_worker():
    """Service Worker"""
    return send_file(str(STATIC_DIR / "sw.js"))


# ─── 启动 ───

def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    print("")
    print("=" * 55)
    print("  🏀 NBA Daily - 手机App服务器已启动!")
    print("=" * 55)
    print("")
    print(f"  📱 访问地址:  http://{ip}:{port}")
    print("")
    print("=" * 55)
    print("")

    app.run(host="0.0.0.0", port=port, debug=False)

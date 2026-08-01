"""
NBA Daily Bot - 文章抓取模块
从多个RSS源获取NBA英文文章，提取全文和图片
"""
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    RSS_SOURCES,
    HEADERS,
    MIN_WORD_COUNT,
    MAX_WORD_COUNT,
    MIN_IMAGE_COUNT,
    SENT_RECORDS_FILE,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


def _load_sent_records() -> set:
    """加载已发送文章URL集合，用于去重"""
    if not SENT_RECORDS_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_RECORDS_FILE.read_text(encoding="utf-8"))
        return set(data.get("urls", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def _save_sent_record(url: str, title: str) -> None:
    """记录已发送的文章URL"""
    records = {"urls": []}
    if SENT_RECORDS_FILE.exists():
        try:
            records = json.loads(SENT_RECORDS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records = {"urls": []}

    if url not in records["urls"]:
        records["urls"].append(url)
        # 只保留最近500条记录，防止文件无限增长
        records["urls"] = records["urls"][-500:]
        SENT_RECORDS_FILE.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _url_to_filename(url: str) -> str:
    """将URL转换为安全的文件名"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _is_byline_or_meta(text: str) -> bool:
    """判断文本是否是作者信息/元数据而非正文"""
    meta_patterns = [
        "story by", "min read", "hour read", "hours ago", "day ago", "days ago",
        "©", "copyright", "all rights reserved", "published", "updated",
        "share this", "tweet", "facebook", "linkedin", "pinterest",
        "newsletter", "subscribe", "sign up for", "advertisement",
        "cookie", "privacy policy", "terms of",
        "click to", "tap to", "follow us", "related stories",
        "recommended for you", "sponsored", "promoted",
    ]
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in meta_patterns)


def _is_real_content(text: str) -> bool:
    """判断文本是否是真正的文章内容（而非元数据）"""
    # 太短的不是正文
    if len(text) < 60:
        return False
    # 包含元数据关键词的不是正文
    if _is_byline_or_meta(text):
        return False
    return True


def _extract_article_text(soup: BeautifulSoup) -> str:
    """从BeautifulSoup对象中提取正文内容"""
    # 移除脚本和样式
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                      "noscript", "iframe", "form", "time"]):
        tag.decompose()

    # 策略1: 直接找 class="content-body" 的 p 标签（Yahoo文章特征）
    content_paragraphs = soup.select("p.content-body, [class*='content-body'] p, p[class*='content-body']")
    if not content_paragraphs:
        # 策略2: 尝试找 caas-body 或其他常见文章容器
        content_paragraphs = soup.select(
            '[class*="caas-body"] p, '
            '[class*="article-body"] p, '
            'article p, '
            '[class*="post-content"] p, '
            '[class*="story-body"] p, '
            'main p'
        )

    # 策略3: 如果还是没找到，从article或body中提取所有p
    if not content_paragraphs:
        article_el = soup.select_one(
            "article, [class*='article'], [class*='post'], main, [role='main']"
        )
        if article_el:
            content_paragraphs = article_el.find_all("p")
        else:
            content_paragraphs = soup.find_all("p")

    # 过滤：只保留真正的正文段落
    paragraphs = []
    for p in content_paragraphs:
        # 跳过在导航/页脚/侧边栏里的
        if p.find_parent(["nav", "footer", "header", "aside", "time"]):
            continue
        text = p.get_text(strip=True)
        if _is_real_content(text):
            paragraphs.append(text)

    # 去重（有时候同一段内容出现在多个标签里）
    seen = set()
    unique_paragraphs = []
    for p in paragraphs:
        # 用前60个字符做去重
        key = p[:60]
        if key not in seen:
            seen.add(key)
            unique_paragraphs.append(p)

    return "\n\n".join(unique_paragraphs)


def _extract_images(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """从文章正文区域提取有效图片（排除广告、图标、侧边栏缩略图）"""
    images = []
    seen_urls = set()

    # 只从文章正文容器中找图片，不搜整个页面
    content_selectors = [
        "article",
        '[class*="article-body"]',
        '[class*="article-content"]',
        '[class*="ArticleBody"]',
        '[class*="post-content"]',
        '[class*="story-body"]',
        '[class*="content-body"]',
        '[class*="caas-body"]',
        "main",
        '[role="main"]',
    ]

    content_area = None
    for sel in content_selectors:
        content_area = soup.select_one(sel)
        if content_area:
            break

    if not content_area:
        content_area = soup

    for img in content_area.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src:
            continue

        full_url = urljoin(base_url, src)
        url_lower = full_url.lower()

        # 过滤：路径关键词
        skip_keywords = [
            "icon", "logo", "avatar", "pixel", "1x1", "ad.", "spacer",
            "sprite", "blank", "transparent", "placeholder", "badge",
            "favicon", "share", "social", "twitter", "facebook",
            "newsletter", "subscribe", "author-headshot", "headshot",
            "50x50", "60x60", "80x80", "100x100",
        ]
        if any(x in url_lower for x in skip_keywords):
            continue

        # 过滤：图片尺寸属性（太小的跳过）
        width = img.get("width") or ""
        height = img.get("height") or ""
        try:
            w = int(width) if width else 0
            h = int(height) if height else 0
            if w > 0 and h > 0 and (w < 200 or h < 150):
                continue
        except (ValueError, TypeError):
            pass  # 无法解析尺寸，继续

        # 去重
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        alt = img.get("alt", "") or img.get("title", "")

        # 过滤无意义的alt文本
        skip_alts = ["thumbnail", "icon", "logo", "avatar", "photo", "image"]
        if alt.lower().strip() in skip_alts:
            alt = ""

        images.append({"url": full_url, "alt": alt})

    # 最多取5张，优先保留有alt描述的
    with_alt = [i for i in images if i["alt"]]
    without_alt = [i for i in images if not i["alt"]]
    images = (with_alt + without_alt)[:5]

    return images


def _download_image(url: str, save_dir: Path) -> Optional[Path]:
    """下载单张图片到本地目录"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 从URL或Content-Type确定扩展名
        content_type = resp.headers.get("Content-Type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        elif "gif" in content_type:
            ext = ".gif"
        else:
            # 从URL后缀推断
            parsed = urlparse(url)
            ext = Path(parsed.path).suffix or ".jpg"

        filename = hashlib.md5(url.encode()).hexdigest()[:12] + ext
        filepath = save_dir / filename
        filepath.write_bytes(resp.content)

        return filepath
    except Exception as e:
        logger.warning(f"图片下载失败 {url}: {e}")
        return None


def fetch_articles() -> list[dict]:
    """
    从所有RSS源获取文章列表，按发布时间排序
    返回: [{title, url, source, published, summary}, ...]
    """
    all_articles = []
    sent_urls = _load_sent_records()

    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in sent_urls:
                    continue

                # 解析发布时间
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_date = datetime(*published[:6])
                else:
                    pub_date = datetime.now()

                all_articles.append({
                    "title": entry.get("title", "Untitled"),
                    "url": url,
                    "source": source["name"],
                    "published": pub_date,
                    "summary": entry.get("summary", entry.get("description", "")),
                })
        except Exception as e:
            logger.warning(f"无法解析RSS源 {source['name']}: {e}")

    # 按发布时间降序排列
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    return all_articles


def fetch_full_article(article: dict) -> Optional[dict]:
    """
    抓取文章全文和图片
    返回: {title, url, source, published, text, images[], word_count}
    """
    try:
        resp = requests.get(article["url"], headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 提取正文
        text = _extract_article_text(soup)
        word_count = len(text.split())

        # 提取图片
        images = _extract_images(soup, article["url"])

        return {
            "title": article["title"],
            "url": article["url"],
            "source": article["source"],
            "published": article["published"],
            "text": text,
            "images": images,
            "word_count": word_count,
        }
    except Exception as e:
        logger.warning(f"无法抓取文章 {article['title']}: {e}")
        return None


def _prefilter_by_summary(article: dict) -> bool:
    """通过RSS摘要预筛选：摘要太短或明显是链接列表的跳过"""
    summary = article.get("summary", "")
    # 清理HTML标签
    from bs4 import BeautifulSoup
    clean = BeautifulSoup(summary, "html.parser").get_text(strip=True) if summary else ""
    # 摘要至少要有些内容
    return len(clean) > 100


def select_best_article(articles: list[dict]) -> Optional[dict]:
    """
    从文章列表中选出最佳的一篇
    标准: 字数适中 + 有图片 + 最新
    """
    candidates = []
    max_attempts = 30  # 最多尝试30篇文章

    for i, article in enumerate(articles):
        if i >= max_attempts:
            break

        # 预筛选：RSS摘要太短的不抓取
        if not _prefilter_by_summary(article):
            continue

        full = fetch_full_article(article)
        if not full:
            continue

        # 字数筛选
        if full["word_count"] < MIN_WORD_COUNT or full["word_count"] > MAX_WORD_COUNT:
            logger.info(f"文章 '{full['title'][:50]}...' 字数 {full['word_count']}，跳过")
            continue

        # 图片筛选
        if len(full["images"]) < MIN_IMAGE_COUNT:
            logger.info(f"文章 '{full['title'][:50]}...' 图片不足 ({len(full['images'])}张)，跳过")
            continue

        logger.info(f"✅ 候选: '{full['title'][:60]}...' ({full['word_count']}词, {len(full['images'])}图)")
        candidates.append(full)

        # 找到10个候选再选最优
        if len(candidates) >= 10:
            break

    if not candidates:
        logger.warning("没有找到符合条件的文章")
        return None

    # 评分: 字数权重最高，然后图片，最后时效
    def score(article: dict) -> float:
        # 字数分: 核心指标，300词=3分，800词=8分，以此类推
        word_score = min(article["word_count"] / 100, 10)
        # 图片分: 每张0.5分，最多3分
        img_score = min(len(article["images"]) * 0.5, 3)
        # 时效分: 24小时内2分，每多一天减0.5
        hours_ago = (datetime.now() - article["published"]).total_seconds() / 3600
        time_score = max(0, 2 - hours_ago / 24 * 0.5)
        return word_score + img_score + time_score

    candidates.sort(key=score, reverse=True)
    logger.info(f"🏆 最优选择: {candidates[0]['word_count']}词 (共{len(candidates)}个候选)")
    return candidates[0]


def download_article_images(article: dict, date_dir: Path) -> dict:
    """下载文章中的所有图片到本地"""
    images_dir = date_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    local_images = []
    for img in article.get("images", []):
        local_path = _download_image(img["url"], images_dir)
        if local_path:
            local_images.append({
                "original_url": img["url"],
                "local_path": str(local_path.relative_to(date_dir)),
                "alt": img.get("alt", ""),
            })

    article["local_images"] = local_images
    return article


def get_daily_article() -> Optional[dict]:
    """
    主入口: 获取每日最佳NBA文章
    返回完整的文章字典（含本地图片路径），或 None
    """
    logger.info("🔍 开始获取NBA文章...")

    # 1. 获取文章列表
    articles = fetch_articles()
    logger.info(f"📋 从 {len(RSS_SOURCES)} 个源获取到 {len(articles)} 篇文章")

    if not articles:
        logger.warning("❌ 没有获取到任何文章")
        return None

    # 2. 筛选最佳文章
    best = select_best_article(articles)
    if not best:
        logger.warning("❌ 没有找到合适的文章")
        return None

    logger.info(f"✅ 选中文章: {best['title'][:80]}")
    logger.info(f"   📍 来源: {best['source']}")
    logger.info(f"   📝 字数: {best['word_count']}")
    logger.info(f"   🖼️  图片: {len(best['images'])} 张")

    return best


def mark_article_sent(article: dict) -> None:
    """标记文章已发送"""
    _save_sent_record(article["url"], article["title"])
    logger.info(f"📌 已记录发送: {article['title'][:60]}")

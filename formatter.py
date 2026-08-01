"""
NBA Daily Bot - HTML生成模块
生成图文并茂的中英双语NBA文章HTML
"""
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional


def _image_to_base64(image_path: Path) -> Optional[str]:
    """将图片转换为base64编码，用于嵌入HTML"""
    try:
        content = image_path.read_bytes()
        ext = image_path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_map.get(ext, "image/jpeg")
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def generate_html(article: dict, translations: list[dict], date_dir: Path) -> str:
    """
    生成双语HTML文章
    参数:
        article: 文章元数据 {title, url, source, published, local_images[]}
        translations: 翻译结果 [{"en": "...", "zh": "..."}, ...]
        date_dir: 当日输出目录
    返回: HTML文件路径
    """
    title_en = article.get("title", "NBA Daily Article")
    source = article.get("source", "Unknown")
    article_url = article.get("url", "#")
    pub_date = article.get("published", datetime.now())
    if hasattr(pub_date, "strftime"):
        date_str = pub_date.strftime("%Y-%m-%d")
    else:
        date_str = str(pub_date)[:10]

    images_dir = date_dir / "images"

    # 处理图片
    image_html_blocks = []
    local_images = article.get("local_images", [])

    # 封面图（第一张图片）
    cover_img_html = ""
    if local_images:
        cover_path = date_dir / local_images[0]["local_path"]
        cover_b64 = _image_to_base64(cover_path)
        if cover_b64:
            cover_img_html = f'<img class="cover-image" src="{cover_b64}" alt="{local_images[0].get("alt", "Cover")}">'

    # 内容图片（插入到段落之间）
    # 将图片分布到文章的不同位置
    content_images = []
    for i, img_info in enumerate(local_images):
        img_path = date_dir / img_info["local_path"]
        img_b64 = _image_to_base64(img_path)
        if img_b64:
            content_images.append({
                "b64": img_b64,
                "alt": img_info.get("alt", f"Image {i+1}"),
                "index": i,
            })

    # 构建段落HTML
    paragraphs_html = ""
    img_idx = 0
    img_interval = max(1, len(translations) // max(1, len(content_images)))

    for i, trans in enumerate(translations):
        en_text = trans.get("en", "")
        zh_text = trans.get("zh", "")

        if not en_text:
            continue

        paragraphs_html += f"""
                <div class="paragraph-pair">
                    <div class="en-paragraph">
                        <span class="lang-tag">🇺🇸 EN</span>
                        <p>{en_text}</p>
                    </div>
                    <div class="zh-paragraph">
                        <span class="lang-tag">🇨🇳 中文</span>
                        <p>{zh_text or '(翻译中...)'}</p>
                    </div>
                </div>"""

        # 在适当位置插入图片
        if img_idx < len(content_images) and (i + 1) % img_interval == 0:
            img = content_images[img_idx]
            paragraphs_html += f"""
                <div class="article-image">
                    <img src="{img['b64']}" alt="{img['alt']}" loading="lazy">
                    <span class="image-caption">{img['alt']}</span>
                </div>"""
            img_idx += 1

    # 如果有剩余图片，追加到末尾
    while img_idx < len(content_images):
        img = content_images[img_idx]
        paragraphs_html += f"""
                <div class="article-image">
                    <img src="{img['b64']}" alt="{img['alt']}" loading="lazy">
                    <span class="image-caption">{img['alt']}</span>
                </div>"""
        img_idx += 1

    # 完整HTML模板
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_en} | NBA每日精选</title>
    <style>
        :root {{
            --nba-blue: #1D428A;
            --nba-red: #C8102E;
            --nba-dark: #0A0A0A;
            --text-dark: #1a1a1a;
            --text-gray: #555;
            --bg-light: #f8f9fa;
            --card-bg: #ffffff;
            --border: #e8e8e8;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                         "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
            color: var(--text-dark);
            line-height: 1.8;
            min-height: 100vh;
        }}

        /* ===== 顶部导航栏 ===== */
        .header {{
            background: linear-gradient(135deg, var(--nba-blue) 0%, #143166 100%);
            color: white;
            padding: 20px 0;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(29,66,138,0.3);
        }}

        .header-content {{
            max-width: 800px;
            margin: 0 auto;
            padding: 0 20px;
        }}

        .header-logo {{
            font-size: 2em;
            margin-bottom: 4px;
        }}

        .header h1 {{
            font-size: 1.2em;
            font-weight: 500;
            letter-spacing: 2px;
            opacity: 0.9;
        }}

        /* ===== 主容器 ===== */
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* ===== 文章卡片 ===== */
        .article-card {{
            background: var(--card-bg);
            border-radius: 16px;
            box-shadow: 0 8px 40px rgba(0,0,0,0.08);
            overflow: hidden;
            margin-bottom: 30px;
        }}

        /* ===== 文章头部 ===== */
        .article-header {{
            padding: 30px 30px 20px;
            border-bottom: 1px solid var(--border);
        }}

        .article-meta {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}

        .meta-tag {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 0.85em;
            color: var(--text-gray);
            background: var(--bg-light);
            padding: 4px 12px;
            border-radius: 20px;
        }}

        .article-title-en {{
            font-size: 1.8em;
            font-weight: 700;
            color: var(--nba-dark);
            line-height: 1.3;
            margin-bottom: 10px;
        }}

        .article-title-zh {{
            font-size: 1.3em;
            color: var(--nba-blue);
            font-weight: 500;
        }}

        /* ===== 封面图 ===== */
        .cover-image {{
            width: 100%;
            max-height: 450px;
            object-fit: cover;
            display: block;
        }}

        /* ===== 文章正文 ===== */
        .article-body {{
            padding: 25px 30px;
        }}

        .paragraph-pair {{
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px dashed #eee;
        }}

        .paragraph-pair:last-child {{
            border-bottom: none;
        }}

        .lang-tag {{
            display: inline-block;
            font-size: 0.7em;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 3px 10px;
            border-radius: 12px;
            margin-bottom: 8px;
        }}

        .en-paragraph {{
            margin-bottom: 12px;
        }}

        .en-paragraph .lang-tag {{
            background: #e3f2fd;
            color: #1565c0;
        }}

        .en-paragraph p {{
            color: #333;
            font-size: 1em;
            line-height: 1.9;
        }}

        .zh-paragraph .lang-tag {{
            background: #fce4ec;
            color: #c62828;
        }}

        .zh-paragraph p {{
            color: #444;
            font-size: 1em;
            line-height: 1.9;
        }}

        /* ===== 文章图片 ===== */
        .article-image {{
            margin: 25px 0;
            text-align: center;
        }}

        .article-image img {{
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}

        .article-image img:hover {{
            transform: scale(1.02);
        }}

        .image-caption {{
            display: block;
            margin-top: 8px;
            font-size: 0.85em;
            color: #888;
            font-style: italic;
        }}

        /* ===== 底部 ===== */
        .article-footer {{
            background: var(--bg-light);
            padding: 20px 30px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .source-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--nba-blue);
            text-decoration: none;
            font-weight: 500;
            font-size: 0.9em;
            transition: color 0.2s;
        }}

        .source-link:hover {{
            color: var(--nba-red);
            text-decoration: underline;
        }}

        .gen-time {{
            font-size: 0.8em;
            color: #999;
        }}

        /* ===== 响应式 ===== */
        @media (max-width: 600px) {{
            .container {{
                padding: 10px;
            }}

            .article-header {{
                padding: 20px 15px 15px;
            }}

            .article-body {{
                padding: 15px;
            }}

            .article-title-en {{
                font-size: 1.4em;
            }}

            .article-title-zh {{
                font-size: 1.1em;
            }}

            .article-footer {{
                padding: 15px;
                flex-direction: column;
                align-items: flex-start;
            }}
        }}

        /* ===== 打印样式 ===== */
        @media print {{
            body {{
                background: white;
            }}
            .header {{
                position: static;
            }}
            .article-card {{
                box-shadow: none;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="header-logo">🏀</div>
            <h1>NBA DAILY · 每日NBA精选</h1>
        </div>
    </header>

    <div class="container">
        <article class="article-card">
            <header class="article-header">
                <div class="article-meta">
                    <span class="meta-tag">📅 {date_str}</span>
                    <span class="meta-tag">📍 {source}</span>
                    <span class="meta-tag">📝 {len(translations)} 段</span>
                </div>
                <h1 class="article-title-en">{title_en}</h1>
                <p class="article-title-zh">🏀 中英双语对照阅读</p>
            </header>

            {cover_img_html}

            <div class="article-body">
                {paragraphs_html}
            </div>

            <footer class="article-footer">
                <a href="{article_url}" target="_blank" rel="noopener" class="source-link">
                    🔗 阅读英文原文
                </a>
                <span class="gen-time">🤖 翻译 by Claude · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            </footer>
        </article>
    </div>
</body>
</html>"""

    # 保存HTML文件
    html_path = date_dir / "article.html"
    html_path.write_text(html, encoding="utf-8")
    return str(html_path)


def generate_metadata(article: dict, html_path: str) -> str:
    """生成文章元数据JSON，方便后续处理"""
    meta = {
        "title": article.get("title"),
        "url": article.get("url"),
        "source": article.get("source"),
        "published": str(article.get("published", "")),
        "word_count": article.get("word_count"),
        "image_count": len(article.get("local_images", [])),
        "html_path": html_path,
        "generated_at": datetime.now().isoformat(),
    }

    meta_path = Path(html_path).parent / "article.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(meta_path)

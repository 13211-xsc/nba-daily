"""
NBA Daily Bot - 邮件发送模块
生成邮件专用HTML（兼容QQ邮箱等主流邮箱），通过QQ邮箱SMTP发送
"""
import smtplib
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

from config import MAIL_TO, MAIL_FROM, MAIL_PASSWORD, SMTP_SERVER, SMTP_PORT

logger = logging.getLogger(__name__)


def _img_to_base64(path: Path) -> str:
    """图片转base64"""
    content = path.read_bytes()
    ext = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime = mime_map.get(ext, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(content).decode()}"


def _build_email_html(article: dict, translations: list[dict], html_path: str) -> str:
    """
    构建邮件兼容的HTML（全部内联样式 + table布局）
    这是关键：邮件客户端只认这种老式写法
    """
    title_en = article.get("title", "NBA Daily")
    source = article.get("source", "Unknown")
    article_url = article.get("url", "#")
    date_str = datetime.now().strftime("%Y-%m-%d")
    local_images = article.get("local_images", [])
    date_dir = Path(html_path).parent

    # ── 封面图 ──
    cover_html = ""
    if local_images:
        cover_path = date_dir / local_images[0]["local_path"]
        if cover_path.exists():
            try:
                cover_b64 = _img_to_base64(cover_path)
                cover_html = f"""
        <tr><td style="padding:0;">
          <img src="{cover_b64}" width="100%" style="display:block;max-width:100%;border:0;">
        </td></tr>"""
            except Exception:
                pass

    # ── 段落内容 ──
    paragraphs_html = ""
    for i, trans in enumerate(translations):
        en_text = trans.get("en", "")
        zh_text = trans.get("zh", "")
        if not en_text:
            continue

        paragraphs_html += f"""
        <tr><td style="padding:16px 20px 8px 20px;">
          <span style="display:inline-block;font-size:11px;font-weight:bold;color:#fff;
                       background:#1D428A;padding:3px 10px;border-radius:10px;">EN</span>
          <p style="color:#333;font-size:15px;line-height:1.8;margin:8px 0 0 0;
                    font-family:Arial,Helvetica,sans-serif;">
            {en_text}
          </p>
        </td></tr>
        <tr><td style="padding:4px 20px 16px 20px;">
          <span style="display:inline-block;font-size:11px;font-weight:bold;color:#fff;
                       background:#C8102E;padding:3px 10px;border-radius:10px;">中文</span>
          <p style="color:#444;font-size:15px;line-height:1.8;margin:8px 0 0 0;
                    font-family:'PingFang SC','Microsoft YaHei','微软雅黑',Arial,sans-serif;">
            {zh_text or '(翻译中...)'}
          </p>
        </td></tr>"""

        # 在段落间插入图片
        img_idx = i
        if local_images and img_idx < len(local_images) and img_idx > 0:
            img_info = local_images[img_idx]
            img_path = date_dir / img_info["local_path"]
            if img_path.exists():
                try:
                    img_b64 = _img_to_base64(img_path)
                    alt = img_info.get("alt", "")
                    paragraphs_html += f"""
        <tr><td style="padding:12px 20px;text-align:center;">
          <img src="{img_b64}" width="90%" style="display:block;max-width:100%;
               margin:0 auto;border-radius:8px;border:1px solid #e0e0e0;">
          <span style="display:block;font-size:12px;color:#999;margin-top:6px;">{alt}</span>
        </td></tr>"""
                except Exception:
                    pass

    # ── 组装完整邮件HTML ──
    email_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#f2f2f2;">

<!-- 外层容器 -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f2f2f2;">
<tr><td align="center" style="padding:20px 10px;">

  <!-- 主卡片 600px -->
  <table width="600" cellpadding="0" cellspacing="0"
         style="background:#fff;border-radius:12px;overflow:hidden;
                box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:600px;">

    <!-- 头部 -->
    <tr><td style="background:#1D428A;padding:24px 20px;text-align:center;">
      <div style="font-size:32px;">🏀</div>
      <div style="color:#fff;font-size:16px;font-weight:bold;letter-spacing:2px;
                  margin-top:6px;font-family:Arial,Helvetica,sans-serif;">
        NBA DAILY · 每日NBA精选
      </div>
    </td></tr>

    <!-- 标题区 -->
    <tr><td style="padding:20px 24px 0 24px;">
      <div style="color:#888;font-size:13px;margin-bottom:8px;
                  font-family:Arial,Helvetica,sans-serif;">
        📅 {date_str} &nbsp;·&nbsp; 📍 {source}
      </div>
      <h1 style="color:#111;font-size:20px;line-height:1.4;margin:0 0 4px 0;
                 font-family:Arial,Helvetica,sans-serif;">
        {title_en}
      </h1>
      <div style="height:3px;background:linear-gradient(to right,#1D428A,#C8102E);
                  margin-top:16px;border-radius:2px;"></div>
    </td></tr>

    <!-- 封面图 -->
    {cover_html}

    <!-- 文章正文 -->
    {paragraphs_html}

    <!-- 分隔线 -->
    <tr><td style="padding:0 20px;">
      <div style="border-top:1px dashed #ddd;margin:8px 0 16px 0;"></div>
    </td></tr>

    <!-- 底部 -->
    <tr><td style="padding:8px 24px 20px 24px;text-align:center;">
      <p style="color:#999;font-size:12px;margin:0 0 8px 0;
                font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
        📂 完整文章已保存至本地 &nbsp;|&nbsp; 🤖 翻译由Google提供
      </p>
      <a href="{article_url}" target="_blank"
         style="color:#1D428A;font-size:13px;font-weight:bold;text-decoration:none;
                font-family:Arial,Helvetica,sans-serif;">
        🔗 阅读英文原文 →
      </a>
      <p style="color:#bbb;font-size:11px;margin:10px 0 0 0;
                font-family:Arial,Helvetica,sans-serif;">
        生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </p>
    </td></tr>

  </table>

</td></tr>
</table>

</body>
</html>"""

    return email_html


def send_daily_article(article: dict, translations: list[dict], html_path: str) -> bool:
    """
    通过QQ邮箱发送双语NBA文章
    使用邮件兼容的HTML模板（table布局+内联样式）
    """
    if not MAIL_TO or MAIL_TO == "你的QQ号@qq.com":
        logger.error("❌ 请先在 .env 文件中配置 MAIL_TO（你的QQ邮箱地址）")
        return False

    if not MAIL_PASSWORD or "这里填" in MAIL_PASSWORD:
        logger.error("❌ 请先在 .env 文件中配置 MAIL_PASSWORD（QQ邮箱授权码）")
        return False

    title_en = article.get("title", "NBA Daily Article")

    # 生成邮件专用HTML
    email_html = _build_email_html(article, translations, html_path)

    # 构建邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏀 {title_en[:80]}"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(email_html, "html", "utf-8"))

    try:
        logger.info(f"📧 正在发送邮件到 {MAIL_TO}...")

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(MAIL_FROM, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, MAIL_TO, msg.as_string())
        server.quit()

        logger.info(f"✅ 邮件发送成功!")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ QQ邮箱登录失败，请检查授权码是否正确")
        return False
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {e}")
        return False

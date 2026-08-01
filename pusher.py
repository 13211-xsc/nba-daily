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
    构建邮件HTML — "The Fourth Quarter" 设计
    灵感: NBA比赛末节的紧张感 — 暗色基调 + 冠军金点缀
    签名元素: NBA数据线 (PTS/REB/AST) 展示文章统计
    """
    title_en = article.get("title", "NBA Daily")
    source = article.get("source", "Unknown")
    article_url = article.get("url", "#")
    date_str = datetime.now().strftime("%Y-%m-%d")
    local_images = article.get("local_images", [])
    date_dir = Path(html_path).parent
    word_count = article.get("word_count", 0)
    para_count = len(translations)
    img_count = len(local_images)

    # ═══ "Fourth Quarter" 色彩体系 ═══
    # Arena Black: 球场熄灯后的暗色
    # Championship Gold: Larry O'Brien冠军奖杯的金
    # Intensity Red: 计时器的红
    # Timeout White: 暂停时刻的白板
    C = {
        "bg":        "#e8e6e3",
        "card":      "#ffffff",
        "arena":     "#0d0d0d",   # 球馆暗色
        "gold":      "#b8860b",   # 冠军金 (dark goldenrod)
        "red":       "#c0392b",   # 强度红
        "en_bg":     "#f7f5f2",   # 暖白 — 像战术板纸
        "zh_bg":     "#fafafa",   # 冷白 — 中文区
        "text":      "#262626",
        "muted":     "#8c8c8c",
        "border":    "#e0ddd9",
        "film_bg":   "#f2f0ed",   # 图片衬底
    }

    # ── 封面图 ──
    cover_html = ""
    if local_images:
        cover_path = date_dir / local_images[0]["local_path"]
        if cover_path.exists():
            try:
                cover_b64 = _img_to_base64(cover_path)
                cover_html = f"""
        <tr><td bgcolor="{C['arena']}" style="padding:0;line-height:0;">
          <img src="{cover_b64}" width="100%" style="display:block;width:100%;border:0;">
        </td></tr>"""
            except Exception:
                pass

    # ── 计算图片插入位置 ──
    # 封面已用第一张，剩余的均匀分布
    inline_images = local_images[1:] if len(local_images) > 1 else []
    total_paras = len([t for t in translations if t.get("en")])
    # 计算每张图应该在第几个段落后插入
    if inline_images and total_paras > 0:
        img_positions = []
        step = total_paras / (len(inline_images) + 1)
        for k in range(1, len(inline_images) + 1):
            img_positions.append(int(k * step))
    else:
        img_positions = []

    # ── 段落内容 ──
    paragraphs_html = ""
    para_index = 0  # 有内容的段落计数

    for i, trans in enumerate(translations):
        en_text = trans.get("en", "")
        zh_text = trans.get("zh", "")
        if not en_text:
            continue

        # 英文: 暖白底 + 金色左边线, Georgia 衬线体
        paragraphs_html += f"""
        <tr><td style="padding:0 28px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="margin:16px 0 0 0;background:{C['en_bg']};
                        border-left:2px solid {C['gold']};">
            <tr><td style="padding:16px 18px 16px 18px;">
              <span style="font-size:9px;font-weight:700;letter-spacing:2px;
                           color:{C['gold']};text-transform:uppercase;
                           font-family:Arial,Helvetica,sans-serif;">English</span>
              <p style="color:{C['text']};font-size:15px;line-height:1.9;margin:6px 0 0 0;
                        font-family:Georgia,'Times New Roman','Songti SC',serif;">
                {en_text}
              </p>
            </td></tr>
          </table>
        </td></tr>"""

        # 中文: 白底 + 红色左边线
        if zh_text:
            paragraphs_html += f"""
        <tr><td style="padding:0 28px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="margin:6px 0 0 0;background:{C['zh_bg']};
                        border-left:2px solid {C['red']};">
            <tr><td style="padding:14px 18px 14px 18px;">
              <span style="font-size:9px;font-weight:700;letter-spacing:2px;
                           color:{C['red']};text-transform:uppercase;
                           font-family:Arial,Helvetica,sans-serif;">中文翻译</span>
              <p style="color:#333;font-size:15px;line-height:1.9;margin:6px 0 0 0;
                        font-family:'PingFang SC','Microsoft YaHei','微软雅黑',
                        'Hiragino Sans GB',sans-serif;">
                {zh_text}
              </p>
            </td></tr>
          </table>
        </td></tr>"""

        # 在计算好的位置插入图片
        if para_index in img_positions:
            img_idx_inline = img_positions.index(para_index)
            if img_idx_inline < len(inline_images):
                img_info = inline_images[img_idx_inline]
                img_path = date_dir / img_info["local_path"]
                if img_path.exists():
                    try:
                        img_b64 = _img_to_base64(img_path)
                        alt = img_info.get("alt", "")
                        paragraphs_html += f"""
        <tr><td style="padding:24px 28px 4px 28px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td bgcolor="{C['film_bg']}" style="padding:3px;text-align:center;">
              <img src="{img_b64}" width="100%"
                   style="display:block;width:100%;border:0;">
            </td></tr>"""
                        if alt:
                            paragraphs_html += f"""
            <tr><td style="padding:8px 6px 0 6px;">
              <span style="font-size:11px;color:{C['muted']};
                           font-family:'PingFang SC','Microsoft YaHei',sans-serif;">
                {alt}
              </span>
            </td></tr>"""
                        paragraphs_html += """
          </table>
        </td></tr>"""
                    except Exception:
                        pass

        para_index += 1

    # ═══ 组装邮件 ═══
    email_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:{C['bg']};-webkit-font-smoothing:antialiased;">

<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{C['bg']}">
<tr><td align="center" style="padding:20px 10px 40px 10px;">

  <!-- ═══ 主卡片 ═══ -->
  <table width="600" cellpadding="0" cellspacing="0"
         style="background:{C['card']};max-width:600px;
                box-shadow:0 2px 16px rgba(0,0,0,0.06);">

    <!-- ── 头部: 暗色球馆风 ── -->
    <tr><td bgcolor="{C['arena']}"
            style="padding:32px 24px 24px 24px;text-align:center;">
      <div style="font-size:36px;line-height:1;letter-spacing:-1px;">&#127936;</div>
      <div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:4px;
                  margin-top:8px;font-family:Arial,Helvetica,sans-serif;">
        NBA DAILY
      </div>
      <div style="width:36px;height:2px;background:{C['gold']};margin:12px auto 0 auto;"></div>
      <div style="color:rgba(255,255,255,0.45);font-size:10px;letter-spacing:3px;
                  margin-top:8px;font-family:Arial,Helvetica,sans-serif;">
        每日精选 &middot; 双语阅读
      </div>
    </td></tr>

    <!-- ── NBA数据线 (签名元素) ── -->
    <tr><td style="padding:0 24px;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-bottom:1px solid {C['border']};">
        <tr>
          <td align="center" style="padding:18px 0 14px 0;width:33%;">
            <div style="font-size:24px;font-weight:700;color:{C['arena']};
                        font-family:Arial,Helvetica,sans-serif;">{word_count}</div>
            <div style="font-size:9px;color:{C['muted']};letter-spacing:2px;
                        text-transform:uppercase;font-family:Arial,sans-serif;">PTS</div>
          </td>
          <td align="center" style="padding:18px 0 14px 0;width:33%;
                     border-left:1px solid {C['border']};border-right:1px solid {C['border']};">
            <div style="font-size:24px;font-weight:700;color:{C['arena']};
                        font-family:Arial,Helvetica,sans-serif;">{para_count}</div>
            <div style="font-size:9px;color:{C['muted']};letter-spacing:2px;
                        text-transform:uppercase;font-family:Arial,sans-serif;">REB</div>
          </td>
          <td align="center" style="padding:18px 0 14px 0;width:33%;">
            <div style="font-size:24px;font-weight:700;color:{C['arena']};
                        font-family:Arial,Helvetica,sans-serif;">{img_count}</div>
            <div style="font-size:9px;color:{C['muted']};letter-spacing:2px;
                        text-transform:uppercase;font-family:Arial,sans-serif;">AST</div>
          </td>
        </tr>
      </table>
    </td></tr>

    <!-- ── 日期来源 ── -->
    <tr><td style="padding:16px 28px 0 28px;">
      <span style="font-size:11px;color:{C['muted']};
                   font-family:Arial,Helvetica,sans-serif;">
        {date_str} &nbsp;&middot;&nbsp; {source}
      </span>
    </td></tr>

    <!-- ── 标题: Georgia 衬线体, 杂志感 ── -->
    <tr><td style="padding:10px 28px 0 28px;">
      <h1 style="color:{C['arena']};font-size:22px;line-height:1.3;margin:0;
                 font-family:Georgia,'Times New Roman','Songti SC',serif;
                 font-weight:700;letter-spacing:-0.2px;">
        {title_en}
      </h1>
    </td></tr>

    <!-- ── 装饰线 ── -->
    <tr><td style="padding:14px 28px 4px 28px;">
      <table width="48" cellpadding="0" cellspacing="0">
        <tr>
          <td width="28" height="2" bgcolor="{C['arena']}"></td>
          <td width="4"></td>
          <td width="16" height="2" bgcolor="{C['gold']}"></td>
        </tr>
      </table>
    </td></tr>

    <!-- ── 封面图 ── -->
    {cover_html}

    <!-- ── 正文 ── -->
    {paragraphs_html}

    <!-- ── 结尾 ── -->
    <tr><td style="padding:28px 28px 0 28px;">
      <div style="border-top:1px solid {C['border']};"></div>
    </td></tr>

    <tr><td style="padding:20px 28px 28px 28px;text-align:center;">
      <a href="{article_url}" target="_blank" rel="noopener"
         style="display:inline-block;background:{C['arena']};color:#fff;
                text-decoration:none;padding:12px 32px;font-size:12px;
                font-weight:600;letter-spacing:0.5px;
                font-family:Arial,Helvetica,sans-serif;">
        阅读英文原文 &rarr;
      </a>
      <p style="color:{C['muted']};font-size:10px;margin:16px 0 0 0;
                font-family:'PingFang SC','Microsoft YaHei','微软雅黑',sans-serif;">
        翻译由 Google 提供 &nbsp;&middot;&nbsp;
        {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </p>
    </td></tr>

  </table>

  <!-- ── 尾注 ── -->
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;margin-top:14px;">
    <tr><td style="text-align:center;padding:6px 0;">
      <span style="font-size:10px;color:#c0bdb8;font-family:Arial,sans-serif;">
        NBA Daily Bot &mdash; Python + Google Translate
      </span>
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

"""
🏀 NBA Daily Bot - 主入口（邮件版）
每天自动获取NBA英文文章 → Google翻译 → 生成双语HTML → 发送邮件

用法:
    python main.py              # 正常运行（发邮件）
    python main.py --dry-run    # 测试模式，不发邮件
    python main.py --open       # 浏览器打开（不发邮件）
"""
import sys
import io
import logging
import webbrowser
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR, BASE_DIR
from fetcher import get_daily_article, mark_article_sent, download_article_images
from translator import split_into_paragraphs, translate_article
from formatter import generate_html, generate_metadata
from pusher import send_daily_article

# 修复Windows控制台UTF-8编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "nba_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def main(dry_run: bool = False, open_browser: bool = False):
    """主流程"""
    logger.info("=" * 50)
    logger.info("🏀 NBA Daily Bot 启动 (Google翻译 + 邮件发送)")
    logger.info(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        logger.info("⚠️  测试模式，不会发送邮件")
    if open_browser:
        logger.info("🌐 浏览器模式，不会发送邮件")
    logger.info("=" * 50)

    # ── 步骤1: 获取文章 ──
    logger.info("")
    logger.info("📥 [1/4] 获取NBA文章...")
    article = get_daily_article()
    if not article:
        logger.error("❌ 未能获取到合适的文章，退出")
        return False

    # ── 步骤2: 分割段落 ──
    logger.info("")
    logger.info("✂️  [2/4] 分割文章段落...")
    paragraphs = split_into_paragraphs(article["text"])
    logger.info(f"   共分割为 {len(paragraphs)} 个段落")

    if not paragraphs:
        logger.error("❌ 文章内容为空，退出")
        return False

    # ── 步骤3: 谷歌翻译 ──
    logger.info("")
    logger.info("🌐 [3/4] Google 免费翻译中...")
    try:
        translations = translate_article(paragraphs)
    except Exception as e:
        logger.error(f"❌ 翻译失败: {e}")
        return False

    # ── 步骤4: 生成HTML + 发送邮件 ──
    logger.info("")
    logger.info("📄 [4/4] 生成HTML文章...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = OUTPUT_DIR / today_str
    date_dir.mkdir(parents=True, exist_ok=True)

    # 下载图片
    article = download_article_images(article, date_dir)
    logger.info(f"   🖼️  下载了 {len(article.get('local_images', []))} 张图片")

    # 生成HTML
    html_path = generate_html(article, translations, date_dir)
    logger.info(f"   ✅ HTML已生成: {html_path}")

    # 生成元数据
    generate_metadata(article, html_path)

    # 发送或打开
    logger.info("")
    if dry_run:
        logger.info("📤 ⏭️  测试模式，跳过发送")
        push_ok = True
    elif open_browser:
        logger.info("🌐 在浏览器中打开文章...")
        webbrowser.open(str(Path(html_path)))
        push_ok = True
    else:
        logger.info("📧 [发送邮件]...")
        push_ok = send_daily_article(article, translations, html_path)

    # 记录
    if push_ok or dry_run:
        mark_article_sent(article)

    # ── 完成 ──
    logger.info("")
    logger.info("=" * 50)
    logger.info("🎉 NBA Daily Bot 执行完毕!")
    logger.info(f"📂 HTML文件: {html_path}")
    logger.info(f"📧 邮件发送: {'✅ 成功' if push_ok else '❌ 失败'}")
    logger.info("=" * 50)

    return True


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    open_browser = "--open" in sys.argv
    success = main(dry_run=dry_run, open_browser=open_browser)
    sys.exit(0 if success else 1)

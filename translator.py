"""
NBA Daily Bot - 免费翻译模块
使用 deep_translator (Google Translate) 免费翻译
"""
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

# 篮球术语对照表（Google翻译后修正）
BASKETBALL_TERMS = {
    # Google翻译有时会逐字翻译，这里做后处理修正
    "挑选和滚动": "挡拆",
    "挑选和卷": "挡拆",
    "接球": "空接",  # alley-oop context
    "三倍双倍": "三双",
    "快速休息": "快攻",
    "快速突破": "快攻",
    "罚球": "罚球",  # 这个通常正确
    "三点": "三分球",
    "猛击": "扣篮",
    "大满贯扣篮": "扣篮",
    "反弹": "篮板",
    "协助": "助攻",
    "偷": "抢断",
    "块": "盖帽",
    "周转": "失误",
    "加班": "加时赛",
    "季后赛": "季后赛",
    "全明星": "全明星",
    "锦标赛": "锦标赛",
    "自由球员": "自由球员",
}


def _post_process(text: str) -> str:
    """后处理：修正常见篮球术语的翻译"""
    for wrong, correct in BASKETBALL_TERMS.items():
        text = text.replace(wrong, correct)
    return text


def translate_article(paragraphs: list[str]) -> list[dict]:
    """
    使用Google翻译免费翻译文章所有段落
    参数: paragraphs - 英文段落列表
    返回: [{"en": "英文段落", "zh": "中文翻译"}, ...]
    """
    results = []

    for i, paragraph in enumerate(paragraphs):
        logger.info(f"🔄 翻译中... 第 {i+1}/{len(paragraphs)} 段")

        try:
            # Google Translate 免费翻译
            translated = GoogleTranslator(source="en", target="zh-CN").translate(paragraph)

            # 后处理修正篮球术语
            translated = _post_process(translated)

            results.append({"en": paragraph, "zh": translated})

        except Exception as e:
            logger.warning(f"翻译第 {i+1} 段失败: {e}，保留原文")
            results.append({"en": paragraph, "zh": ""})

    translated_count = sum(1 for r in results if r["zh"])
    logger.info(f"   翻译完成: {translated_count}/{len(paragraphs)} 段")
    return results


def split_into_paragraphs(text: str) -> list[str]:
    """
    将文章文本分割为适合手机阅读的短段落
    按句子分割，每2-3句一组
    """
    import re

    # 先按双换行粗分
    raw = text.split("\n\n")

    paragraphs = []
    for chunk in raw:
        chunk = chunk.strip()
        if len(chunk) < 30:
            continue

        # 如果chunk太长，按句子再分
        if len(chunk) > 500:
            # 按句子分割 (句号、问号、感叹号后跟空格)
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            # 合并短句，每2-3句一组
            buffer = ""
            count = 0
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                buffer += s + " "
                count += 1
                if count >= 3 and len(buffer) > 200:
                    paragraphs.append(buffer.strip())
                    buffer = ""
                    count = 0
            if buffer.strip():
                paragraphs.append(buffer.strip())
        else:
            paragraphs.append(chunk)

    return paragraphs

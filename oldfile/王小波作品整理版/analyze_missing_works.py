#!/usr/bin/env python3
"""
王小波作品整理版 - EPUB备份文件分析补全脚本
处理13部缺失分析文档的作品，从TXT/PDF/EPUB源提取文本，
生成 作品分析.md 和 训练数据/ 目录，格式与现有作品完全一致。
"""

import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from collections import Counter

BASE_DIR = Path("/home/wy/code1/王小波作品整理版")
BACKUP_DIR = BASE_DIR / "原始EPUB备份"

WORKS = [
    {
        "name": "我的阴阳两界",
        "category": "长篇小说",
        "source": "我的阴阳两界-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "未来世界",
        "category": "长篇小说",
        "source": "未来世界-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "革命时期的爱情",
        "category": "长篇小说",
        "source": "革命时期的爱情-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "不成功的爱情",
        "category": "中短篇小说",
        "source": "不成功的爱情-王小波-迅捷PDF转换器.pdf",
        "format": "PDF",
    },
    {
        "name": "大学四年级",
        "category": "中短篇小说",
        "source": "大学四年级-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "人为什么活着",
        "category": "杂文随笔",
        "source": "人为什么活着-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "思维的乐趣",
        "category": "杂文随笔",
        "source": "思维的乐趣-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "我的精神家园",
        "category": "杂文随笔",
        "source": "我的精神家园-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "沉默的大多数",
        "category": "杂文随笔",
        "source": "沉默的大多数王小波杂文随笔全编-迅捷PDF转换器.pdf",
        "format": "PDF",
    },
    {
        "name": "爱你就像爱生命",
        "category": "书信集",
        "source": "爱你就像爱生命-王小波李银河-迅捷PDF转换器.pdf",
        "format": "PDF",
    },
    {
        "name": "王小波书信集",
        "category": "书信集",
        "source": "王小波全集.第九卷·书信-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "怀疑三部曲",
        "category": "学术研究",
        "source": "怀疑三部曲-王小波.txt",
        "format": "TXT",
    },
    {
        "name": "未竟稿",
        "category": "学术研究",
        "source": None,
        "format": "EPUB",
        "epub_path": BASE_DIR / "学术研究" / "未竟稿" / "王小波全集.第十卷.未竟稿-王小波.epub",
    },
]

KEYWORDS = ["爱", "存在", "性", "逻辑", "智慧", "痛苦"]
PUNCTUATION = ["。", "！", "？", "，", "；", "："]
CN_NUMS = "一二三四五六七八九十百千万"


def extract_txt(filepath):
    for enc in ["utf-8", "gbk", "gb18030", "gb2312"]:
        try:
            with open(filepath, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"Cannot decode {filepath}")


def extract_pdf(filepath):
    result = subprocess.run(
        ["pdftotext", str(filepath), "-"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed for {filepath}: {result.stderr}")
    return result.stdout


def extract_epub(filepath):
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(filepath))
    parts = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        parts.append(soup.get_text(separator="\n"))
    return "\n".join(parts)


def extract_text(work):
    if work["format"] == "TXT":
        return extract_txt(BACKUP_DIR / work["source"])
    elif work["format"] == "PDF":
        return extract_pdf(BACKUP_DIR / work["source"])
    elif work["format"] == "EPUB":
        return extract_epub(work["epub_path"])
    else:
        raise ValueError(f"Unknown format: {work['format']}")


def clean_text(text):
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def detect_chapters(text):
    patterns = [
        r"^(第[一二三四五六七八九十百千万零\d]+[章节篇回])\s*(.*)$",
        r"^(\d+[\s、．.].*)$",
        r"^([一二三四五六七八九十]+[\s、．.].*)$",
        r"^((?:序言|前言|引子|尾声|后记|附录))$",
    ]
    chapters = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pat in patterns:
            m = re.match(pat, stripped, re.MULTILINE)
            if m:
                title = stripped[:60]
                chapters.append({"title": title, "line_index": i})
                break
    return chapters


def split_into_chapters(text):
    chapters = detect_chapters(text)
    lines = text.split("\n")

    if not chapters:
        return [{"title": "全文", "content": text}]

    result = []
    for idx, ch in enumerate(chapters):
        start = ch["line_index"]
        if idx + 1 < len(chapters):
            end = chapters[idx + 1]["line_index"]
        else:
            end = len(lines)
        content = "\n".join(lines[start:end]).strip()
        if content:
            result.append({"title": ch["title"], "content": content})
    return result


def count_sentences(text):
    sents = re.split(r"[。！？]", text)
    sents = [s.strip() for s in sents if s.strip()]
    return sents


def count_paragraphs(text):
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return paras


def analyze_style(text):
    sents = count_sentences(text)
    paras = count_paragraphs(text)
    total_chars = len(text.replace("\n", "").replace(" ", ""))

    sent_lengths = [len(s) for s in sents] if sents else [0]
    para_lengths = [len(p) for p in paras] if paras else [0]

    punct_counts = {}
    for p in PUNCTUATION:
        punct_counts[p] = text.count(p)

    keyword_counts = {}
    for kw in KEYWORDS:
        keyword_counts[kw] = len(re.findall(kw, text))

    has_first_person = bool(re.search(r"[我咱]", text[:5000]))
    has_third_person = bool(re.search(r"[他她它]", text[:5000]))

    if has_first_person and not has_third_person:
        narrative_view = "第一人称"
    elif has_third_person and not has_first_person:
        narrative_view = "第三人称"
    elif has_first_person and has_third_person:
        narrative_view = "第一人称"
    else:
        narrative_view = "不确定"

    avg_sent_len = sum(sent_lengths) / len(sent_lengths) if sent_lengths else 0
    avg_para_len = sum(para_lengths) / len(para_lengths) if para_lengths else 0

    if avg_sent_len > 25:
        sentence_style = "长句为主，节奏舒缓"
    elif avg_sent_len > 15:
        sentence_style = "长短句结合，节奏适中"
    else:
        sentence_style = "短句为主，节奏紧凑"

    return {
        "total_chars": total_chars,
        "sentence_count": len(sents),
        "avg_sent_len": round(avg_sent_len, 2),
        "paragraph_count": len(paras),
        "avg_para_len": round(avg_para_len, 2),
        "punctuation": punct_counts,
        "keywords": keyword_counts,
        "narrative_view": narrative_view,
        "sentence_style": sentence_style,
    }


def detect_themes(text, work_name, category):
    themes = []
    sample = text[:10000]

    if re.search(r"爱情|爱|恋|情", sample):
        themes.append("情感探讨")
    if re.search(r"自由|解放|反抗", sample):
        themes.append("自由解放")
    if re.search(r"思考|理性|逻辑|道理", sample):
        themes.append("理性思考")
    if re.search(r"身体|性|欲望", sample):
        themes.append("身体意识")
    if re.search(r"智慧|聪明|知识", sample):
        themes.append("智慧启迪")
    if re.search(r"社会|体制|制度|权力", sample):
        themes.append("社会批判")
    if re.search(r"幽默|笑|讽刺|荒诞", sample):
        themes.append("黑色幽默")
    if re.search(r"历史|传统|文化", sample):
        themes.append("文化反思")
    if re.search(r"信|信件|通信|亲爱的", sample):
        themes.append("书信情感")
    if re.search(r"怀疑|追问|质疑", sample):
        themes.append("怀疑精神")

    if category == "杂文随笔":
        if "社会批判" not in themes:
            themes.append("社会批判")
        if "理性思考" not in themes:
            themes.append("理性思考")
    elif category == "书信集":
        if "书信情感" not in themes:
            themes.append("书信情感")
    elif category == "学术研究":
        if "怀疑精神" not in themes:
            themes.append("怀疑精神")

    if not themes:
        themes = ["理性思考", "情感探讨", "自由解放"]
    return themes


def split_training_sections(text, work_name, chapter_title, section_start=1, min_len=1000, max_len=2000):
    sections = []
    paras = [p for p in text.split("\n") if p.strip()]

    current_text = ""
    section_num = section_start

    for para in paras:
        if len(current_text) + len(para) + 1 > max_len and len(current_text) >= min_len:
            sections.append(
                {
                    "work_name": work_name,
                    "chapter": chapter_title,
                    "section_num": section_num,
                    "text": current_text.strip(),
                }
            )
            section_num += 1
            current_text = para
        else:
            current_text += "\n" + para if current_text else para

    if current_text.strip():
        if len(current_text.strip()) < min_len and sections:
            sections[-1]["text"] += "\n" + current_text.strip()
            sections[-1]["text"] = sections[-1]["text"].strip()
        else:
            sections.append(
                {
                    "work_name": work_name,
                    "chapter": chapter_title,
                    "section_num": section_num,
                    "text": current_text.strip(),
                }
            )

    return sections, section_num


def has_dialogue(text):
    return bool(re.search(r"[""「」『』]", text) or re.search(r"[：:]\s*「", text))


def has_description(text):
    return bool(re.search(r"[像如仿佛好似]", text))


def generate_analysis_md(work_name, category, style, chapters, themes):
    lines = []
    lines.append(f"# {work_name} - 作品分析")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **作品名**: {work_name}")
    lines.append(f"- **总字数**: {style['total_chars']:,} 字")
    lines.append(f"- **章节数**: {len(chapters)} 章")
    lines.append(f"- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 文风特征")
    lines.append("")
    lines.append("### 句式特征")
    lines.append(f"- **句子总数**: {style['sentence_count']}")
    lines.append(f"- **平均句长**: {style['avg_sent_len']} 字")
    lines.append(f"- **段落总数**: {style['paragraph_count']}")
    lines.append(f"- **平均段落长**: {style['avg_para_len']} 字")
    lines.append("")
    lines.append("### 标点符号统计")
    for p in PUNCTUATION:
        lines.append(f"- **{p}**: {style['punctuation'].get(p, 0)} 次")
    lines.append("")
    lines.append("### 关键词出现频率")
    for kw in KEYWORDS:
        lines.append(f"- **{kw}**: {style['keywords'].get(kw, 0)} 次")
    lines.append("")
    lines.append("## 章节结构")
    lines.append("")
    for i, ch in enumerate(chapters, 1):
        ch_chars = len(ch["content"].replace("\n", "").replace(" ", ""))
        pct = (ch_chars / style["total_chars"] * 100) if style["total_chars"] > 0 else 0
        lines.append(f"### {i}. {ch['title']}")
        lines.append(f"- 字数: {ch_chars:,} 字")
        lines.append(f"- 占比: {pct:.1f}%")
        lines.append("")
    lines.append("")
    lines.append("## 逻辑结构分析")
    lines.append("")
    lines.append("### 叙事特点")
    lines.append(f"- **叙事视角**: {style['narrative_view']}")
    lines.append(f"- **句式特点**: {style['sentence_style']}")
    lines.append("")
    lines.append("### 主题元素")
    for theme in themes:
        lines.append(f"- {theme}")
    lines.append("")
    lines.append("## 文风总结")
    lines.append("")
    lines.append("王小波的写作风格独特，具有以下特点：")
    lines.append("")
    lines.append("1. **理性与情感的融合**: 在理性思考中融入深刻的人文关怀")
    lines.append("2. **黑色幽默**: 用冷峻的幽默感解构严肃主题")
    lines.append("3. **哲学思辨**: 将哲学思考自然融入叙事")
    lines.append("4. **语言简洁**: 文字简洁有力，避免过度修饰")
    lines.append("5. **结构创新**: 经常采用非线性叙事或嵌套结构")
    lines.append("")
    lines.append(
        f"本作品体现了王小波一贯的文风特征，通过独特的叙事视角和语言风格，展现了对人生、社会、文化的深度思考。"
    )
    lines.append("")
    return "\n".join(lines)


def generate_section_md(section):
    text = section["text"]
    char_count = len(text.replace("\n", "").replace(" ", ""))
    dialogue = "是" if has_dialogue(text) else "否"
    description = "是" if has_description(text) else "否"

    lines = []
    lines.append(f"# {section['work_name']}_section_{section['section_num']:03d}")
    lines.append("")
    lines.append("## 元数据")
    lines.append("")
    lines.append(f"- **作品名**: {section['work_name']}")
    lines.append(f"- **章节**: {section['chapter']}")
    lines.append(f"- **小节序号**: {section['section_num']}")
    lines.append(f"- **字数**: {char_count} 字")
    lines.append("")
    lines.append("## 叙事特征")
    lines.append("")
    lines.append(f"- **包含对话**: {dialogue}")
    lines.append(f"- **描述性内容**: {description}")
    lines.append(f"- **叙事视角**: {section.get('narrative_view', '第一人称')}")
    lines.append("")
    lines.append("## 原文内容")
    lines.append("")
    lines.append(text)
    lines.append("")
    return "\n".join(lines)


def process_work(work):
    name = work["name"]
    category = work["category"]
    work_dir = BASE_DIR / category / name

    print(f"\n{'='*60}")
    print(f"处理: {name} ({category}) - 来源: {work['format']}")
    print(f"{'='*60}")

    text = extract_text(work)
    text = clean_text(text)
    print(f"  提取文本: {len(text):,} 字符")

    txt_path = work_dir / f"{name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  保存文本副本: {txt_path.name}")

    style = analyze_style(text)
    print(f"  文风分析: 总字数={style['total_chars']:,}, 句子={style['sentence_count']}, 段落={style['paragraph_count']}")

    chapters = split_into_chapters(text)
    print(f"  识别章节: {len(chapters)} 章")

    themes = detect_themes(text, name, category)

    analysis_md = generate_analysis_md(name, category, style, chapters, themes)
    analysis_path = work_dir / "作品分析.md"
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(analysis_md)
    print(f"  生成分析文档: 作品分析.md")

    train_dir = work_dir / "训练数据"
    train_dir.mkdir(exist_ok=True)

    all_sections = []
    next_section = 1
    for ch in chapters:
        sections, next_section = split_training_sections(
            ch["content"], name, ch["title"], section_start=next_section
        )
        for s in sections:
            s["narrative_view"] = style["narrative_view"]
        all_sections.extend(sections)

    for section in all_sections:
        section_md = generate_section_md(section)
        filename = f"{name}_section_{section['section_num']:03d}.md"
        with open(train_dir / filename, "w", encoding="utf-8") as f:
            f.write(section_md)

    print(f"  生成训练数据: {len(all_sections)} 个小节")

    return {
        "name": name,
        "category": category,
        "total_chars": style["total_chars"],
        "chapters": len(chapters),
        "sections": len(all_sections),
        "source_format": work["format"],
    }


def main():
    print("=" * 60)
    print("王小波作品整理版 - EPUB备份文件分析补全")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"待处理作品: {len(WORKS)} 部")
    print("=" * 60)

    results = []
    for i, work in enumerate(WORKS, 1):
        print(f"\n[{i}/{len(WORKS)}] ", end="")
        try:
            result = process_work(work)
            results.append(result)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("处理完成汇总")
    print("=" * 60)

    total_chars = 0
    total_sections = 0
    for r in results:
        print(f"  ✅ {r['name']}: {r['total_chars']:,}字, {r['chapters']}章, {r['sections']}小节 (来源:{r['source_format']})")
        total_chars += r["total_chars"]
        total_sections += r["sections"]

    print(f"\n  总计: {len(results)}部作品, {total_chars:,}字, {total_sections}个训练小节")
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results


if __name__ == "__main__":
    main()

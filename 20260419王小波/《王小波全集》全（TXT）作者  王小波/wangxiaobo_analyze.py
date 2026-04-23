#!/usr/bin/env python3
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

try:
    import ebooklib
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False

ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'cp936', 'iso-8859-1']
KEYWORDS = ['爱', '存在', '性', '逻辑', '智慧', '痛苦', '自由', '理性', '快乐', '荒诞', '沉默', '思想', '知识', '科学', '艺术', '死亡', '生活', '真实', '虚构', '权力']
PUNCTUATION = {'。': 0, '！': 0, '？': 0, '，': 0, '；': 0, '：': 0, '——': 0, '"': 0, '"': 0, '…': 0}

CHAPTER_PATTERNS = [
    re.compile(r'^第[一二三四五六七八九十百千万零\d]+[章节回卷部篇]', re.MULTILINE),
    re.compile(r'^Chapter\s+\d+', re.MULTILINE | re.IGNORECASE),
]

SPECIAL_CHAPTER_TITLES = {'序', '序言', '序子', '自序', '后记', '附录', '前言', '引言', '尾声', '楔子'}

BACKUP_DIR = '/home/wy/code1/王小波作品整理版/原始EPUB备份'
PROJECT_DIR = '/home/wy/code1/王小波作品整理版'


def read_txt(filepath):
    for enc in ENCODINGS:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            if any('\u4e00' <= c <= '\u9fff' for c in content[:500]):
                return content
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def read_pdf(filepath):
    try:
        result = subprocess.run(
            ['pdftotext', filepath, '-'],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except Exception as e:
        print(f"  PDF extraction error: {e}")
        return ""


def read_epub(filepath):
    if not HAS_EBOOKLIB:
        return ""
    try:
        book = epub.read_epub(filepath)
        texts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            texts.append(soup.get_text())
        return '\n'.join(texts)
    except Exception as e:
        print(f"  EPUB extraction error: {e}")
        return ""


def detect_chapters(text):
    chapters = []
    for pattern in CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) >= 2:
            for i, m in enumerate(matches):
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                title = text[start:text.find('\n', start)].strip()[:80]
                chapters.append((title, start, end))
            return chapters

    lines = text.split('\n')
    chapter_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in SPECIAL_CHAPTER_TITLES:
            pos = sum(len(l) + 1 for l in lines[:i])
            chapter_starts.append((stripped, pos))
            continue
        if len(stripped) <= 30 and not stripped[0] in '，。！？、；：""''（）—…' and not stripped.endswith(('，', '。', '！', '？', '、', '；', '：')):
            if re.match(r'^第[一二三四五六七八九十百千万零\d]+[章节回卷部篇]', stripped):
                pos = sum(len(l) + 1 for l in lines[:i])
                chapter_starts.append((stripped, pos))

    if len(chapter_starts) >= 2:
        chapters = []
        for i, (title, start) in enumerate(chapter_starts):
            end = chapter_starts[i + 1][1] if i + 1 < len(chapter_starts) else len(text)
            chapters.append((title, start, end))
        return chapters

    return []


def analyze_text(text, work_name):
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    total_sentences = len(sentences)

    total_chars = len(text.replace('\n', '').replace(' ', ''))
    avg_sent_len = total_chars / total_sentences if total_sentences > 0 else 0

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    total_paragraphs = len(paragraphs)
    avg_para_len = total_chars / total_paragraphs if total_paragraphs > 0 else 0

    punct_stats = {}
    for p in list(PUNCTUATION.keys()):
        punct_stats[p] = text.count(p)

    keyword_freq = {}
    for kw in KEYWORDS:
        count = text.count(kw)
        if count > 0:
            keyword_freq[kw] = count
    sorted_keywords = sorted(keyword_freq.items(), key=lambda x: -x[1])

    chapters = detect_chapters(text)

    has_dialog = bool(re.search(r'[「""][^""」]+[」""]', text))
    first_person = bool(re.search(r'我[是说看想觉得认为]', text[:5000]))

    return {
        'total_chars': total_chars,
        'total_sentences': total_sentences,
        'avg_sent_len': round(avg_sent_len, 2),
        'total_paragraphs': total_paragraphs,
        'avg_para_len': round(avg_para_len, 2),
        'punctuation': punct_stats,
        'keywords': sorted_keywords,
        'chapters': chapters,
        'has_dialog': has_dialog,
        'first_person': first_person,
        'total_words_est': total_chars,
    }


def generate_analysis_md(work_name, analysis, output_path):
    lines = [
        f'# {work_name} - 作品分析',
        '',
        '## 基本信息',
        '',
        f'- **作品名**: {work_name}',
        f'- **总字数**: {analysis["total_chars"]:,} 字',
        f'- **章节数**: {len(analysis["chapters"])} 章' if analysis["chapters"] else f'- **章节数**: 未识别明确章节',
        f'- **分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        '## 文风特征',
        '',
        '### 句式特征',
        f'- **句子总数**: {analysis["total_sentences"]}',
        f'- **平均句长**: {analysis["avg_sent_len"]} 字',
        f'- **段落总数**: {analysis["total_paragraphs"]}',
        f'- **平均段落长**: {analysis["avg_para_len"]} 字',
        '',
        '### 标点符号统计',
    ]
    for p, count in analysis['punctuation'].items():
        display_p = p if p not in ('——',) else '——'
        lines.append(f'- **{display_p}**: {count} 次')

    lines.append('')
    lines.append('### 关键词出现频率')
    for kw, count in analysis['keywords'][:10]:
        lines.append(f'- **{kw}**: {count} 次')

    if analysis['chapters']:
        lines.extend(['', '## 章节结构', ''])
        for i, (title, start, end) in enumerate(analysis['chapters']):
            ch_text = title[:60]
            ch_chars = end - start
            pct = round(ch_chars / analysis['total_chars'] * 100, 1) if analysis['total_chars'] > 0 else 0
            lines.append(f'### {i + 1}. {ch_text}')
            lines.append(f'- 字数: {ch_chars:,} 字')
            lines.append(f'- 占比: {pct}%')
            lines.append('')

    lines.extend([
        '', '## 逻辑结构分析', '',
        '### 叙事特点',
        f'- **叙事视角**: {"第一人称" if analysis["first_person"] else "第三人称"}',
        f'- **句式特点**: 长短句结合，节奏{"较快" if analysis["avg_sent_len"] < 25 else "适中" if analysis["avg_sent_len"] < 35 else "舒缓"}',
        '',
        '### 主题元素',
    ])
    theme_keywords = [kw for kw, _ in analysis['keywords'][:6]]
    for kw in theme_keywords:
        lines.append(f'- {kw}')

    lines.extend([
        '', '## 文风总结', '',
        '王小波的写作风格独特，具有以下特点：',
        '',
        '1. **理性与情感的融合**: 在理性思考中融入深刻的人文关怀',
        '2. **黑色幽默**: 用冷峻的幽默感解构严肃主题',
        '3. **哲学思辨**: 将哲学思考自然融入叙事',
        '4. **语言简洁**: 文字简洁有力，避免过度修饰',
        '5. **结构创新**: 经常采用非线性叙事或嵌套结构',
        '',
        f'本作品体现了王小波一贯的文风特征，通过独特的叙事视角和语言风格，展现了对人生、社会、文化的深度思考。',
        '',
    ])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Generated: {output_path}")


def split_into_sections(text, min_chars=1000, max_chars=2000):
    sections = []
    paragraphs = re.split(r'\n\s*\n|\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        if len(text.strip()) >= min_chars * 0.5:
            sections.append(text.strip())
        return sections

    merged_paras = []
    for p in paragraphs:
        if merged_paras and len(merged_paras[-1]) < 50:
            merged_paras[-1] = merged_paras[-1] + ' ' + p
        else:
            merged_paras.append(p)

    current_section = []
    current_len = 0

    for para in merged_paras:
        para_len = len(para)

        if current_len + para_len > max_chars and current_len >= min_chars:
            sections.append('\n'.join(current_section))
            current_section = [para]
            current_len = para_len
        else:
            current_section.append(para)
            current_len += para_len

    if current_section:
        remaining = '\n'.join(current_section)
        if len(remaining.strip()) >= min_chars * 0.3:
            sections.append(remaining.strip())

    return sections


def generate_training_data(work_name, text, output_dir, chapters):
    os.makedirs(output_dir, exist_ok=True)

    section_num = 0

    if chapters:
        for ch_title, ch_start, ch_end in chapters:
            ch_text = text[ch_start:ch_end]
            sections = split_into_sections(ch_text)
            for sec_text in sections:
                section_num += 1
                write_section_file(work_name, ch_title, section_num, sec_text, output_dir)
    else:
        sections = split_into_sections(text)
        for sec_text in sections:
            section_num += 1
            write_section_file(work_name, "全文", section_num, sec_text, output_dir)

    print(f"  Generated {section_num} training sections in {output_dir}")
    return section_num


def write_section_file(work_name, chapter, section_num, text, output_dir):
    has_dialog = bool(re.search(r'[「""][^""」]+[」""]', text))
    is_descriptive = len(re.findall(r'[的地得]', text)) > 5
    is_first_person = bool(re.search(r'我[是说看想觉得认为]', text[:500]))

    char_count = len(text.replace('\n', '').replace(' ', ''))

    filename = f'{work_name}_section_{section_num:03d}.md'
    filepath = os.path.join(output_dir, filename)

    lines = [
        f'# {work_name}_section_{section_num:03d}',
        '',
        '## 元数据',
        '',
        f'- **作品名**: {work_name}',
        f'- **章节**: {chapter}',
        f'- **小节序号**: {section_num}',
        f'- **字数**: {char_count} 字',
        '',
        '## 叙事特征',
        '',
        f'- **包含对话**: {"是" if has_dialog else "否"}',
        f'- **描述性内容**: {"是" if is_descriptive else "否"}',
        f'- **叙事视角**: {"第一人称" if is_first_person else "第三人称"}',
        '',
        '## 原文内容',
        '',
        text,
        '',
    ]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def process_work(work_name, category_dir, source_file, source_type):
    work_dir = os.path.join(PROJECT_DIR, category_dir, work_name)
    os.makedirs(work_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Processing: {work_name} ({category_dir})")
    print(f"Source: {source_file} ({source_type})")
    print(f"Target: {work_dir}")

    if source_type == 'txt':
        text = read_txt(source_file)
    elif source_type == 'pdf':
        text = read_pdf(source_file)
    elif source_type == 'epub':
        text = read_epub(source_file)
    else:
        print(f"  Unknown source type: {source_type}")
        return False

    if not text or len(text.strip()) < 100:
        print(f"  ERROR: Text extraction failed or too short ({len(text)} chars)")
        return False

    print(f"  Extracted {len(text):,} characters")

    analysis = analyze_text(text, work_name)
    print(f"  Analysis: {analysis['total_chars']:,} chars, {analysis['total_sentences']} sentences, {len(analysis['chapters'])} chapters")

    analysis_path = os.path.join(work_dir, '作品分析.md')
    generate_analysis_md(work_name, analysis, analysis_path)

    training_dir = os.path.join(work_dir, '训练数据')
    section_count = generate_training_data(work_name, text, training_dir, analysis['chapters'])

    txt_copy_path = os.path.join(work_dir, f'{work_name}.txt')
    with open(txt_copy_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"  Saved text copy: {txt_copy_path}")

    print(f"  DONE: {section_count} sections generated")
    return True


def main():
    works = [
        {
            'name': '我的阴阳两界',
            'category': '长篇小说',
            'source': os.path.join(BACKUP_DIR, '我的阴阳两界-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '未来世界',
            'category': '长篇小说',
            'source': os.path.join(BACKUP_DIR, '未来世界-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '革命时期的爱情',
            'category': '长篇小说',
            'source': os.path.join(BACKUP_DIR, '革命时期的爱情-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '不成功的爱情',
            'category': '中短篇小说',
            'source': os.path.join(BACKUP_DIR, '不成功的爱情-王小波-迅捷PDF转换器.pdf'),
            'type': 'pdf',
        },
        {
            'name': '大学四年级',
            'category': '中短篇小说',
            'source': os.path.join(BACKUP_DIR, '大学四年级-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '人为什么活着',
            'category': '杂文随笔',
            'source': os.path.join(BACKUP_DIR, '人为什么活着-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '思维的乐趣',
            'category': '杂文随笔',
            'source': os.path.join(BACKUP_DIR, '思维的乐趣-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '我的精神家园',
            'category': '杂文随笔',
            'source': os.path.join(BACKUP_DIR, '我的精神家园-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '沉默的大多数',
            'category': '杂文随笔',
            'source': os.path.join(BACKUP_DIR, '沉默的大多数王小波杂文随笔全编-迅捷PDF转换器.pdf'),
            'type': 'pdf',
        },
        {
            'name': '爱你就像爱生命',
            'category': '书信集',
            'source': os.path.join(BACKUP_DIR, '爱你就像爱生命-王小波李银河-迅捷PDF转换器.pdf'),
            'type': 'pdf',
        },
        {
            'name': '王小波书信集',
            'category': '书信集',
            'source': os.path.join(BACKUP_DIR, '王小波全集.第九卷·书信-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '怀疑三部曲',
            'category': '学术研究',
            'source': os.path.join(BACKUP_DIR, '怀疑三部曲-王小波.txt'),
            'type': 'txt',
        },
        {
            'name': '未竟稿',
            'category': '学术研究',
            'source': os.path.join(PROJECT_DIR, '学术研究', '未竟稿', '王小波全集.第十卷.未竟稿-王小波.epub'),
            'type': 'epub',
        },
    ]

    results = []
    for work in works:
        success = process_work(work['name'], work['category'], work['source'], work['type'])
        results.append((work['name'], work['category'], success))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    success_count = 0
    for name, cat, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {cat}/{name}")
        if ok:
            success_count += 1
    print(f"\nTotal: {success_count}/{len(results)} succeeded")


if __name__ == '__main__':
    main()

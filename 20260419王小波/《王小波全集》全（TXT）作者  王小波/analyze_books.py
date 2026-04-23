#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
王小波作品深度分析脚本
功能：EPUB文本提取、结构分析、训练数据生成
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# 尝试导入EPUB处理库
try:
    import ebooklib
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False
    print("警告: ebooklib未安装，EPUB文本提取功能不可用")

class TextAnalyzer:
    def __init__(self, output_dir, min_words=1000, max_words=2000):
        self.output_dir = Path(output_dir)
        self.min_words = min_words
        self.max_words = max_words

        # 章节识别模式
        self.chapter_patterns = [
            r'^[第零一二三四五六七八九十百千]+\s*[章节卷部篇]',
            r'^Chapter\s+\d+',
            r'^Chapter\s+[IVXLCM]+',
            r'^第\d+\s*[章节卷部篇]',
            r'^【[^】]+】',
            r'^\d+[、\.]\s*[^\n\r]+',  # 数字开头的标题
            r'^[一二三四五六七八九十百]+[、\s]+[^\n\r]+'  # 中文数字开头的标题
        ]

        # 处理统计
        self.stats = {
            'epub_processed': 0,
            'epub_failed': 0,
            'txt_processed': 0,
            'total_words': 0,
            'total_sections': 0,
            'analysis_generated': 0
        }

    def extract_text_from_epub(self, epub_path):
        """从EPUB文件提取纯文本"""
        if not EPUB_AVAILABLE:
            return None

        try:
            book = epub.read_epub(str(epub_path))
            text_content = []

            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_body_content()
                    # 简单的HTML标签清理
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'&nbsp;', ' ', content)
                    content = re.sub(r'&quot;', '"', content)
                    content = re.sub(r'&amp;', '&', content)
                    content = re.sub(r'&lt;', '<', content)
                    content = re.sub(r'&gt;', '>', content)

                    # 清理空白字符
                    content = re.sub(r'\s+', ' ', content)
                    content = content.strip()

                    if content:
                        text_content.append(content)

            full_text = '\n'.join(text_content)
            self.stats['epub_processed'] += 1
            return full_text

        except Exception as e:
            print(f"EPUB提取失败 {epub_path}: {e}")
            self.stats['epub_failed'] += 1
            return None

    def extract_text_from_txt(self, txt_path):
        """从TXT文件提取文本，处理编码问题"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1', 'cp936']

        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as f:
                    text = f.read()
                self.stats['txt_processed'] += 1
                return text
            except (UnicodeDecodeError, LookupError):
                continue
            except Exception as e:
                print(f"TXT读取失败 {txt_path}: {e}")
                break

        print(f"无法读取文件: {txt_path}")
        return None

    def detect_chapters(self, text):
        """检测章节边界"""
        lines = text.split('\n')
        chapters = []
        current_chapter = []
        current_title = "序言"

        for line in lines:
            line = line.strip()

            # 检测是否为章节标题
            is_chapter = False
            for pattern in self.chapter_patterns:
                if re.match(pattern, line) and len(line) < 50:
                    # 保存当前章节
                    if current_chapter:
                        chapters.append({
                            'title': current_title,
                            'content': '\n'.join(current_chapter)
                        })

                    # 开始新章节
                    current_title = line
                    current_chapter = []
                    is_chapter = True
                    break

            if not is_chapter and line:
                current_chapter.append(line)

        # 添加最后一个章节
        if current_chapter:
            chapters.append({
                'title': current_title,
                'content': '\n'.join(current_chapter)
            })

        return chapters if chapters else [{'title': '全文', 'content': text}]

    def analyze_writing_style(self, text):
        """分析文风特征"""
        # 句子长度分析
        sentences = re.split(r'[。！？；]', text)
        sentence_lengths = [len(s.strip()) for s in sentences if s.strip()]

        if not sentence_lengths:
            return {}

        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)

        # 段落分析
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        avg_paragraph_length = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0

        # 标点符号统计
        punctuation_stats = {
            '。': text.count('。'),
            '！': text.count('！'),
            '？': text.count('？'),
            '，': text.count('，'),
            '；': text.count('；'),
            '：': text.count('：'),
        }

        # 关键词识别（简化版）
        keywords = ['理性', '逻辑', '自由', '智慧', '思维', '性', '爱',
                   '痛苦', '存在', '意义', '荒谬', '现实', '理想']
        keyword_counts = {kw: text.count(kw) for kw in keywords}

        return {
            'sentence_count': len(sentence_lengths),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'paragraph_count': len(paragraphs),
            'avg_paragraph_length': round(avg_paragraph_length, 2),
            'punctuation': punctuation_stats,
            'keywords': keyword_counts
        }

    def split_into_sections(self, text):
        """将文本拆分为训练小字"""
        sections = []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        current_section = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            # 如果当前段落超过最大长度，先保存当前节
            if current_length + para_length > self.max_words and current_section:
                sections.append('\n\n'.join(current_section))
                current_section = []
                current_length = 0

            # 如果单个段落就超过最大长度，需要进一步拆分
            if para_length > self.max_words:
                # 按句号拆分
                sentences = re.split(r'([。！？])', para)
                sentence_group = []
                sent_length = 0

                for i in range(0, len(sentences) - 1, 2):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
                    sent_len = len(sentence)

                    if sent_length + sent_len > self.max_words and sentence_group:
                        sections.append(''.join(sentence_group))
                        sentence_group = []
                        sent_length = 0

                    sentence_group.append(sentence)
                    sent_length += sent_len

                if sentence_group:
                    sections.append(''.join(sentence_group))

                current_section = []
                current_length = 0
            else:
                current_section.append(para)
                current_length += para_length

        # 添加最后一个节
        if current_section:
            sections.append('\n\n'.join(current_section))

        return sections

    def generate_training_data(self, book_name, text, chapter_title=""):
        """生成训练数据"""
        sections = self.split_into_sections(text)
        training_data = []

        for i, section in enumerate(sections, 1):
            section_data = {
                'section_id': f"{book_name}_section_{i:03d}",
                'book_name': book_name,
                'chapter_title': chapter_title,
                'section_number': i,
                'word_count': len(section),
                'content': section,
                'metadata': {
                    'has_dialogue': '说' in section or '道' in section,
                    'has_description': len(section) > 200,
                    'narrative_style': 'first_person' if '我' in section else 'third_person'
                }
            }
            training_data.append(section_data)

        return training_data

    def generate_analysis_document(self, book_name, text, style_analysis, chapters):
        """生成分析文档"""
        word_count = len(text)
        chapter_count = len(chapters)

        analysis_content = f"""# {book_name} - 作品分析

## 基本信息

- **作品名**: {book_name}
- **总字数**: {word_count:,} 字
- **章节数**: {chapter_count} 章
- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 文风特征

### 句式特征
- **句子总数**: {style_analysis.get('sentence_count', 0)}
- **平均句长**: {style_analysis.get('avg_sentence_length', 0)} 字
- **段落总数**: {style_analysis.get('paragraph_count', 0)}
- **平均段落长**: {style_analysis.get('avg_paragraph_length', 0)} 字

### 标点符号统计
"""

        punctuation = style_analysis.get('punctuation', {})
        for punct, count in punctuation.items():
            analysis_content += f"- **{punct}**: {count} 次\n"

        analysis_content += "\n### 关键词出现频率\n"

        keywords = style_analysis.get('keywords', {})
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        for kw, count in sorted_keywords[:10]:  # 显示前10个
            if count > 0:
                analysis_content += f"- **{kw}**: {count} 次\n"

        analysis_content += "\n## 章节结构\n\n"

        for i, chapter in enumerate(chapters, 1):
            chapter_word_count = len(chapter['content'])
            analysis_content += f"### {i}. {chapter['title']}\n"
            analysis_content += f"- 字数: {chapter_word_count:,} 字\n"
            analysis_content += f"- 占比: {chapter_word_count/word_count*100:.1f}%\n\n"

        analysis_content += """
## 逻辑结构分析

### 叙事特点
"""

        if '我' in text:
            analysis_content += "- **叙事视角**: 第一人称\n"
        else:
            analysis_content += "- **叙事视角**: 第三人称\n"

        if style_analysis.get('sentence_count', 0) > 0:
            avg_len = style_analysis.get('avg_sentence_length', 0)
            if avg_len < 15:
                analysis_content += "- **句式特点**: 短句为主，节奏明快\n"
            elif avg_len > 30:
                analysis_content += "- **句式特点**: 长句为主，逻辑缜密\n"
            else:
                analysis_content += "- **句式特点**: 长短句结合，节奏适中\n"

        analysis_content += """
### 主题元素
"""

        theme_elements = []
        if '理性' in text or '逻辑' in text:
            theme_elements.append('理性思考')
        if '爱' in text or '情感' in text:
            theme_elements.append('情感探讨')
        if '自由' in text or '解放' in text:
            theme_elements.append('自由解放')
        if '性' in text:
            theme_elements.append('身体意识')
        if '智慧' in text or '思想' in text:
            theme_elements.append('智慧启迪')

        for element in theme_elements:
            analysis_content += f"- {element}\n"

        if not theme_elements:
            analysis_content += "- 待进一步分析\n"

        analysis_content += "\n## 文风总结\n\n"

        analysis_content += """王小波的写作风格独特，具有以下特点：

1. **理性与情感的融合**: 在理性思考中融入深刻的人文关怀
2. **黑色幽默**: 用冷峻的幽默感解构严肃主题
3. **哲学思辨**: 将哲学思考自然融入叙事
4. **语言简洁**: 文字简洁有力，避免过度修饰
5. **结构创新**: 经常采用非线性叙事或嵌套结构

本作品体现了王小波一贯的文风特征，通过独特的叙事视角和语言风格，展现了对人生、社会、文化的深度思考。
"""

        return analysis_content

    def process_book(self, book_path):
        """处理单个作品"""
        book_name = book_path.parent.name
        file_ext = book_path.suffix.lower()

        print(f"\n处理作品: {book_name}")

        # 提取文本
        text = None
        if file_ext == '.epub':
            text = self.extract_text_from_epub(book_path)
        elif file_ext == '.txt':
            text = self.extract_text_from_txt(book_path)

        if not text:
            print(f"  ❌ 文本提取失败")
            return False

        # 基础统计
        word_count = len(text)
        self.stats['total_words'] += word_count
        print(f"  ✓ 提取文本: {word_count:,} 字")

        # 检测章节
        chapters = self.detect_chapters(text)
        print(f"  ✓ 检测到 {len(chapters)} 个章节")

        # 文风分析
        style_analysis = self.analyze_writing_style(text)
        print(f"  ✓ 文风分析完成")

        # 生成分析文档
        analysis_content = self.generate_analysis_document(
            book_name, text, style_analysis, chapters
        )

       

        analysis_path = book_path.parent / '作品分析.md'
        analysis_path.write_text(analysis_content, encoding='utf-8')
        print(f"  ✓ 生成分析文档: {analysis_path.name}")

        # 生成训练数据
        training_dir = book_path.parent / '训练数据'
        training_dir.mkdir(exist_ok=True)

        all_training_data = []
        for chapter in chapters:
            training_data = self.generate_training_data(
                book_name, chapter['content'], chapter['title']
            )
            all_training_data.extend(training_data)

        # 保存训练数据
        for data in all_training_data:
            section_file = training_dir / f"{data['section_id']}.md"

            # 生成训练数据文件
            training_content = f"""# {data['section_id']}

## 元数据

- **作品名**: {data['book_name']}
- **章节**: {data['chapter_title']}
- **小节序号**: {data['section_number']}
- **字数**: {data['word_count']} 字

## 叙事特征

- **包含对话**: {'是' if data['metadata']['has_dialogue'] else '否'}
- **描述性内容**: {'是' if data['metadata']['has_description'] else '否'}
- **叙事视角**: {'第一人称' if data['metadata']['narrative_style'] == 'first_person' else '第三人称'}

## 原文内容

{data['content']}
"""

            section_file.write_text(training_content, encoding='utf-8')

        self.stats['total_sections'] += len(all_training_data)
        self.stats['analysis_generated'] += 1
        print(f"  ✓ 生成 {len(all_training_data)} 个训练小节")

        return True

    def process_all_books(self):
        """处理所有作品"""
        print("=" * 60)
        print("王小波作品深度分析")
        print("=" * 60)

        # 遍历所有作品目录
        for category_dir in self.output_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.'):
                continue

            print(f"\n处理分类: {category_dir.name}")

            for book_dir in category_dir.iterdir():
                if not book_dir.is_dir():
                    continue

                # 跳过训练数据目录
                if book_dir.name == '训练数据':
                    continue

                # 查找主文件
                main_file = None
                for ext in ['.epub', '.txt']:
                    potential_file = book_dir / f"{book_dir.name}{ext}"
                    if potential_file.exists():
                        main_file = potential_file
                        break

                if not main_file:
                    # 尝试找到第一个支持格式的文件
                    for file in book_dir.iterdir():
                        if file.is_file() and file.suffix.lower() in ['.epub', '.txt']:
                            main_file = file
                            break

                if main_file:
                    self.process_book(main_file)

        # 生成统计报告
        self.generate_final_report()

    def generate_final_report(self):
        """生成最终报告"""
        report_content = f"""# 深度分析完成报告

## 处理统计

- **EPUB文件处理数**: {self.stats['epub_processed']}
- **EPUB文件失败数**: {self.stats['epub_failed']}
- **TXT文件处理数**: {self.stats['txt_processed']}
- **总字数**: {self.stats['total_words']:,} 字
- **生成分析文档数**: {self.stats['analysis_generated']}
- **生成训练小节数**: {self.stats['total_sections']}

## 配置参数

- **输出目录**: {self.output_dir}
- **小节最小字数**: {self.min_words}
- **小节最大字数**: {self.max_words}

## 完成时间

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        report_path = self.output_dir / '深度分析报告.md'
        report_path.write_text(report_content, encoding='utf-8')

        print("\n" + "=" * 60)
        print("深度分析完成!")
        print("=" * 60)
        print(f"分析报告: {report_path}")
        print(f"总字数: {self.stats['total_words']:,}")
        print(f"训练小节: {self.stats['total_sections']}")
        print("=" * 60)


if __name__ == "__main__":
    output_dir = "/home/wy/code1/王小波作品整理版"

    analyzer = TextAnalyzer(
        output_dir=output_dir,
        min_words=1000,
        max_words=2000
    )

    analyzer.process_all_books()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
王小波作品替代文件分析工具
功能：分析已找到的同名TXT/PDF文件，为后续处理做准备
"""

import os
import re
from pathlib import Path
from datetime import datetime
import sys

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')

class AlternativeFileAnalyzer:
    def __init__(self, source_dir, organized_dir):
        self.source_dir = Path(source_dir)
        self.organized_dir = Path(organized_dir)
        self.analysis_results = {
            'total_txt_files': 0,
            'total_pdf_files': 0,
            'analyzed_txt_files': [],
            'analyzed_pdf_files': [],
            'encoding_stats': {},
            'size_stats': {}
        }

    def find_all_alternatives(self):
        """查找所有TXT和PDF文件"""
        txt_files = list(self.source_dir.rglob("*.txt"))
        pdf_files = list(self.source_dir.rglob("*.pdf"))

        self.analysis_results['total_txt_files'] = len(txt_files)
        self.analysis_results['total_pdf_files'] = len(pdf_files)

        return txt_files, pdf_files

    def analyze_txt_file(self, txt_path):
        """深度分析TXT文件"""
        analysis = {
            'file_name': txt_path.name,
            'file_path': str(txt_path),
            'file_size': txt_path.stat().st_size,
            'encoding': 'unknown',
            'readable': False,
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'contains_chinese': False,
            'quality_score': 0
        }

        # 尝试多种编码读取
        encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1', 'cp936']
        content = None
        used_encoding = None

        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    used_encoding = encoding
                    break
            except (UnicodeDecodeError, LookupError):
                continue
            except Exception:
                break

        if content:
            analysis['encoding'] = used_encoding
            analysis['readable'] = True
            analysis['char_count'] = len(content)
            analysis['line_count'] = len(content.split('\n'))
            analysis['word_count'] = len(re.findall(r'[\w\u4e00-\u9fff]+', content))
            
            # 检测中文字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            analysis['contains_chinese'] = chinese_chars > 0
            analysis['chinese_char_count'] = chinese_chars

            # 统计段落
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            analysis['paragraph_count'] = len(paragraphs)

            # 质量评分（基于多个因素）
            score = 0
            if analysis['readable']: score += 40
            if analysis['contains_chinese']: score += 30
            if analysis['word_count'] > 100: score += 15
            if analysis['line_count'] > 10: score += 10
            if used_encoding == 'utf-8': score += 5
            analysis['quality_score'] = min(score, 100)

        return analysis

    def analyze_pdf_file(self, pdf_path):
        """分析PDF文件"""
        analysis = {
            'file_name': pdf_path.name,
            'file_path': str(pdf_path),
            'file_size': pdf_path.stat().st_size,
            'file_type': 'pdf',
            'quality_score': 50
        }

        # 基于文件大小进行简单评估
        size_kb = analysis['file_size'] / 1024
        if size_kb > 100:
            analysis['quality_score'] = 70
            analysis['notes'] = "大文件，可能包含完整内容"
        elif size_kb > 10:
            analysis['quality_score'] = 60
            analysis['notes'] = "中等大小文件"
        else:
            analysis['quality_score'] = 40
            analysis['notes'] = "小文件，可能不完整"

        return analysis

    def categorize_file(self, file_name):
        """根据文件名分类作品类型"""
        file_name_lower = file_name.lower()

        if '沉默的大多数' in file_name_lower:
            return '杂文集'
        elif '思维的乐趣' in file_name_lower:
            return '杂文集'
        elif '我的精神家园' in file_name_lower:
            return '杂文集'
        elif '人为什么活着' in file_name_lower:
            return '杂文集'
        elif '爱你就像爱生命' in file_name_lower:
            return '书信集'
        elif '王小波全集.第九卷' in file_name_lower:
            return '书信集'
        elif '王小波全集.第十卷' in file_name_lower:
            return '学术研究'
        elif '怀疑三部曲' in file_name_lower:
            return '学术研究'
        elif '大学四年级' in file_name_lower:
            return '学术研究'
        elif '不成功的爱情' in file_name_lower:
            return '学术研究'
        elif '我的阴阳两界' in file_name_lower:
            return '长篇小说'
        elif '未来世界' in file_name_lower:
            return '长篇小说'
        elif '革命时期的爱情' in file_name_lower:
            return '长篇小说'
        else:
            return '其他'

    def generate_analysis_report(self, txt_analyses, pdf_analyses):
        """生成分析报告"""
        report_content = f"""# 王小波作品替代文件分析报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析目的：为EPUB解析失败的作品寻找同名的TXT/PDF替代文件

## 执行摘要

- **TXT文件总数**: {self.analysis_results['total_txt_files']}
- **PDF文件总数**: {self.analysis_results['total_pdf_files']}
- **成功分析TXT**: {len(txt_analyses)}
- **成功分析PDF**: {len(pdf_analyses)}

## TXT文件详细分析

"""

        for i, analysis in enumerate(txt_analyses, 1):
            category = self.categorize_file(analysis['file_name'])
            
            report_content += f"""
### {i}. {analysis['file_name']}

#### 基本信息
- **文件路径**: {analysis['file_path']}
- **文件大小**: {analysis['file_size']:,} bytes ({analysis['file_size'] / 1024:.1f} KB)
- **文件编码**: {analysis['encoding']}
- **作品分类**: {category}
- **可读性**: {'可读' if analysis['readable'] else '不可读'}
- **质量评分**: {analysis['quality_score']}/100

#### 内容统计
- **字符总数**: {analysis.get('char_count', 0):,} 字符
- **单词总数**: {analysis['word_count']:,} 词
- **行数**: {analysis['line_count']:,} 行
- **段落数**: {analysis['paragraph_count']:,} 段
- **中文字符数**: {analysis.get('chinese_char_count', 0):,} 字

#### 文本特征
- **包含中文**: {'是' if analysis['contains_chinese'] else '否'}
- **内容质量**: {self._quality_assessment(analysis['quality_score'])}

"""

        report_content += """
## PDF文件详细分析

"""

        for i, analysis in enumerate(pdf_analyses, 1):
            category = self.categorize_file(analysis['file_name'])
            
            report_content += f"""
### {i}. {analysis['file_name']}

#### 基本信息
- **文件路径**: {analysis['file_path']}
- **文件大小**: {analysis['file_size']:,} bytes ({analysis['file_size'] / 1024:.1f} KB)
- **文件类型**: PDF
- **作品分类**: {category}
- **质量评分**: {analysis['quality_score']}/100

#### 附加信息
"""

            if 'notes' in analysis:
                report_content += f"- **说明**: {analysis['notes']}\n"

        # 添加分类统计
        report_content += """
## 文件分类统计

### TXT文件分类
"""

        txt_categories = {}
        for analysis in txt_analyses:
            category = self.categorize_file(analysis['file_name'])
            txt_categories[category] = txt_categories.get(category, 0) + 1

        for category, count in sorted(txt_categories.items()):
            report_content += f"- **{category}**: {count} 个文件\n"

        report_content += """
### PDF文件分类
"""

        pdf_categories = {}
        for analysis in pdf_analyses:
            category = self.categorize_file(analysis['file_name'])
            pdf_categories[category] = pdf_categories.get(category, 0) + 1

        for category, count in sorted(pdf_categories.items()):
            report_content += f"- **{category}**: {count} 个文件\n"

        # 添加编码统计
        report_content += """
## 文件编码统计
"""

        encoding_stats = {}
        for analysis in txt_analyses:
            encoding = analysis['encoding']
            encoding_stats[encoding] = encoding_stats.get(encoding, 0) + 1

        for encoding, count in sorted(encoding_stats.items()):
            report_content += f"- **{encoding}**: {count} 个文件\n"

        # 添加质量统计
        report_content += """
## 文件质量统计
"""

        high_quality = sum(1 for a in txt_analyses if a['quality_score'] >= 70)
        medium_quality = sum(1 for a in txt_analyses if 50 <= a['quality_score'] < 70)
        low_quality = sum(1 for a in txt_analyses if a['quality_score'] < 50)

        report_content += f"- **高质量 (≥70分)**: {high_quality} 个文件\n"
        report_content += f"- **中等质量 (50-69分)**: {medium_quality} 个文件\n"
        report_content += f"- **低质量 (<50分)**: {low_quality} 个文件\n"

        # 添加处理建议
        report_content += """
## 处理建议

### 高质量TXT文件
1. **直接使用**: 这些文件可以直接作为EPUB的替代内容
2. **编码统一**: 建议将非UTF-8编码的文件转换为UTF-8
3. **元数据提取**: 从文件内容中提取标题、作者等元数据信息
4. **章节识别**: 自动识别章节结构，为EPUB生成做准备

### 中等质量TXT文件
1. **内容检查**: 手工检查文件内容是否完整
2. **格式清理**: 清理多余的空白字符和格式化问题
3. **编码转换**:可能需要进行编码转换才能正确读取

### 低质量TXT文件
1. **内容验证**: 验证文件是否包含有效内容
2. **格式修复**: 可能需要重新格式化
3. **人工处理**: 可能需要人工干预修复

### PDF文件
1. **文本提取**: 使用PDF提取工具获取纯文本内容
2. **内容验证**: 验证提取的文本质量和完整性
3. **格式转换**: 考虑转换为TXT格式以保持一致性
4. **元数据补充**: 从PDF中提取或手工添加元数据信息

## 后续处理计划

1. **文件映射**: 建立TXT/PDF文件与原始EPUB文件的对应关系
2. **批量处理**: 对高质量文件进行批量处理
3. **质量验证**: 验证每个处理结果的准确性
4. **一致性检查**: 确保处理后的文件与原始作品的对应关系

---

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 保存报告
        report_path = self.organized_dir / '替代文件分析报告.md'
        report_path.write_text(report_content, encoding='utf-8')

        print(f"\n{'='*60}")
        print(f"替代文件分析报告已生成: {report_path}")
        print(f"{'='*60}")

        return report_path

    def _quality_assessment(self, score):
        """质量评估描述"""
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "一般"
        else:
            return "较差"

    def run_analysis(self):
        """运行完整的替代文件分析"""
        print("="*80)
        print("王小波作品替代文件分析")
        print("="*80)

        # 1. 查找所有替代文件
        txt_files, pdf_files = self.find_all_alternatives()

        print(f"\n找到 {len(txt_files)} 个TXT文件")
        print(f"找到 {len(pdf_files)} 个PDF文件")

        # 2. 分析TXT文件
        print("\n分析TXT文件...")
        txt_analyses = []
        for txt_file in txt_files:
            print(f"  分析: {txt_file.name}")
            analysis = self.analyze_txt_file(txt_file)
            txt_analyses.append(analysis)
            self.analysis_results['analyzed_txt_files'].append(analysis)

        # 3. 分析PDF文件
        print("\n分析PDF文件...")
        pdf_analyses = []
        for pdf_file in pdf_files:
            print(f"  分析: {pdf_file.name}")
            analysis = self.analyze_pdf_file(pdf_file)
            pdf_analyses.append(analysis)
            self.analysis_results['analyzed_pdf_files'].append(analysis)

        # 4. 生成分析报告
        print("\n生成分析报告...")
        report_path = self.generate_analysis_report(txt_analyses, pdf_analyses)

        # 5. 总结
        print(f"\n{'='*80}")
        print("替代文件分析完成")
        print(f"{'='*80}")
        print(f"TXT文件: {len(txt_analyses)}")
        print(f"PDF文件: {len(pdf_analyses)}")
        print(f"分析报告: {report_path}")
        print(f"{'='*80}")


if __name__ == "__main__":
    source_dir = "/home/wy/code1/20260419王小波"
    organized_dir = "/home/wy/code1/王小波作品整理版"

    analyzer = AlternativeFileAnalyzer(source_dir, organized_dir)
    analyzer.run_analysis()
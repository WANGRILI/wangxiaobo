#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
王小波作品弥补性分析工具
功能：基于EPUB解析失败的记录，查找同名的TXTTXT/PDF文件进行弥补性分析
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
import sys

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')

class SupplementaryAnalyzer:
    def __init__(self, backup_dir, organized_dir):
        self.backup_dir = Path(backup_dir)
        self.organized_dir = Path(organized_dir)
        self.analysis_results = {
            'total_epub_files': 0,
            'replaced_with_txt': 0,
            'replaced_with_pdf': 0,
            'no_alternative': 0,
            'analyzed_files': []
        }

    def find_replacement_files(self, epub_filename):
        """查找同名的替代文件"""
        # 提取基础文件名（去掉扩展名和"fixed_"前缀）
        base_name = epub_filename.name
        if base_name.startswith('fixed_'):
            base_name = base_name[6:]  # 去掉fixed_前缀

        # 去掉.epub扩展名
        if base_name.endswith('.epub'):
            base_name = base_name[:-4]

        # 可能的替代文件名
        txt_filename = base_name + '.txt'
        pdf_filename = base_name + '.pdf'

        # 在备份目录和源目录查找
        replacement_files = []

        # 检查TXT文件
        txt_paths = list(self.backup_dir.glob(f"*{base_name}*.txt"))
        if txt_paths:
            replacement_files.append(('txt', txt_paths[0]))

        # 检查PDF文件
        pdf_paths = list(self.backup_dir.glob(f"*{base_name}*.pdf"))
        if pdf_paths:
            replacement_files.append(('pdf', pdf_paths[0]))

        # 在已组织目录中查找
        organized_txt = list(self.organized_dir.rglob(f"**/{base_name}.txt"))
        if organized_txt:
            replacement_files.append(('txt', organized_txt[0]))

        return replacement_files

    def analyze_text_file(self, txt_path):
        """分析TXT文件"""
        analysis = {
            'file_path': str(txt_path),
            'file_size': txt_path.stat().st_size,
            'encoding': 'unknown',
            'readable': False,
            'word_count': 0,
            'line_count': 0,
            'char_count': 0,
            'content_preview': '',
            'encoding_issues': []
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
            except Exception as e:
                analysis['encoding_issues'].append(f"{encoding}: {str(e)}")
                break

        if content:
            analysis['encoding'] = used_encoding
            analysis['readable'] = True
            analysis['char_count'] = len(content)
            analysis['line_count'] = len(content.split('\n'))
            analysis['word_count'] = len(re.findall(r'[\w\u4e00-\u9fff]+', content))

            # 内容预览（前500字）
            preview = content[:500]
            # 去掉多余空白
            preview = re.sub(r'\s+', ' ', preview).strip()
            analysis['content_preview'] = preview + '...' if len(content) > 500 else preview

        return analysis

    def analyze_pdf_file(self, pdf_path):
        """分析PDF文件"""
        analysis = {
            'file_path': str(pdf_path),
            'file_size': pdf_path.stat().st_size,
            'file_type': 'pdf',
            'extractable': False,
            'notes': []
        }

        # 检查PDF文件大小
        if analysis['file_size'] < 1000:
            analysis['notes'].append("文件异常小，可能不是有效PDF")

        # 基本PDF信息
        analysis['notes'].append(f"PDF文件大小: {analysis['file_size']:,} bytes")
        analysis['extractable'] = True

        return analysis

    def analyze_replacement_file(self, file_type, file_path):
        """根据文件类型进行分析"""
        if file_type == 'txt':
            return self.analyze_text_file(file_path)
        elif file_type == 'pdf':
            return self.analyze_pdf_file(file_path)
        else:
            return {'error': f"未知文件类型: {file_type}"}

    def generate_analysis_report(self, epub_analysis_results):
        """生成弥补性分析报告"""
        report_content = f"""# 王小波作品EPUB弥补性分析报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析目的：基于EPUB解析失败记录，查找同名的TXT/PDF文件进行弥补性分析

## 执行摘要

- **EPUB文件总数**: {self.analysis_results['total_epub_files']}
- **已用TXT替代**: {self.analysis_results['replaced_with_txt']}
- **已用PDF替代**: {self.analysis_results['replaced_with_pdf']}
- **无替代文件**: {self.analysis_results['no_alternative']}
- **成功分析文件**: {len(self.analysis_results['analyzed_files'])}

## 详细分析结果

"""

        for i, result in enumerate(epub_analysis_results, 1):
            report_content += f"""
### {i}. {result['epub_filename']}

#### 基本信息
- **EPUB文件**: {result['epub_filename']}
- **文件大小**: {result['epub_size']:,} bytes
- **解析状态**: {result['parse_status']}
- **替代文件类型**: {result.get('replacement_type', '无')}

#### 替代文件分析
"""

            if 'replacement_analysis' in result:
                replacement = result['replacement_analysis']

                if replacement.get('file_path'):
                    report_content += f"- **文件路径**: {replacement['file_path']}\n"
                    report_content += f"- **文件大小**: {replacement.get('file_size', 0):,} bytes\n"

                if replacement.get('encoding'):
                    report_content += f"- **文件编码**: {replacement['encoding']}\n"

                if replacement.get('readable'):
                    report_content += f"- **可读性**: 可读\n"
                else:
                    report_content += f"- **可读性**: 不可读\n"

                if replacement.get('word_count'):
                    report_content += f"- **字数**: {replacement['word_count']:,} 字\n"

                if replacement.get('line_count'):
                    report_content += f"- **行数**: {replacement['line_count']:,} 行\n"

                if replacement.get('content_preview'):
                    report_content += f"- **内容预览**: {replacement['content_preview'][:200]}...\n"

                if replacement.get('encoding_issues'):
                    report_content += f"- **编码问题**: {', '.join(replacement['encoding_issues'])}\n"

                if replacement.get('notes'):
                    report_content += f"- **说明**: {', '.join(replacement['notes'])}\n"

            elif result.get('no_alternative'):
                report_content += "❌ **未找到可替代的文件**\n"
                report_content += "建议：检查是否有同名的TXT或PDF文件\n"

            report_content += "\n---\n"

        # 添加统计总结
        txt_replaced = [r for r in epub_analysis_results if r.get('replacement_type') == 'txt']
        pdf_replaced = [r for r in epub_analysis_results if r.get('replacement_type') == 'pdf']

        report_content += f"""
## 统计总结

### 替代类型分布
- **TXT文件替代**: {len(txt_replaced)} 个
- **PDF文件替代**: {len(pdf_replaced)} 个
- **无替代文件**: {self.analysis_results['no_alternative']} 个

### TXT文件分析统计
"""

        if txt_replaced:
            total_words = sum(r['replacement_analysis'].get('word_count', 0) for r in txt_replaced)
            total_chars = sum(r['replacement_analysis'].get('char_count', 0) for r in txt_replaced)
            utf8_files = sum(1 for r in txt_replaced if r['replacement_analysis'].get('encoding') == 'utf-8')
            gbk_files = sum(1 for r in txt_replaced if r['replacement_analysis'].get('encoding') == 'gbk')

            report_content += f"- **可读TXT文件**: {len(txt_replaced)} 个\n"
            report_content += f"- **总字数**: {total_words:,} 字\n"
            report_content += f"- **总字符数**: {total_chars:,} 字符\n"
            report_content += f"- **UTF-8编码**: {utf8_files} 个\n"
            report_content += f"- **GBK编码**: {gbk_files} 个\n"

        report_content += """
### PDF文件分析统计
"""

        if pdf_replaced:
            total_pdf_size = sum(r['replacement_analysis'].get('file_size', 0) for r in pdf_replaced)
            report_content += f"- **PDF文件数**: {len(pdf_replaced)} 个\n"
            report_content += f"- **总大小**: {total_pdf_size:,} bytes\n"

        # 添加详细文件清单
        report_content += """
## 替代文件清单
"""

        report_content += "\n### TXT替代文件\n"
        for r in txt_replaced:
            if 'replacement_analysis' in r and 'file_path' in r['replacement_analysis']:
                report_content += f"- {Path(r['replacement_analysis']['file_path']).name} ({r['replacement_analysis'].get('encoding', 'unknown')})\n"

        report_content += "\n### PDF替代文件\n"
        for r in pdf_replaced:
            if 'replacement_analysis' in r and 'file_path' in r['replacement_analysis']:
                report_content += f"- {Path(r['replacement_analysis']['file_path']).name}\n"

        # 添加建议
        report_content += """
## 处理建议

### 对于TXT替代文件
1. **编码统一**: 将非UTF-8编码的文件转换为UTF-8
2. **内容验证**: 检查文件内容是否完整、可读
3. **格式清理**: 清理多余的空白字符和格式化问题
4. **元数据提取**: 从文件内容中提取标题、作者等信息

### 对于PDF替代文件
1. **文本提取**: 使用工具提取PDF中的纯文本
2. **质量控制**: 检查提取的文本质量和完整性
3. **格式转换**: 考虑将PDF转换为TXT以保持一致性

### 对于无替代文件的EPUB
1. **人工检查**: 手工检查EPUB文件的实际内容和结构
2. **格式修复**: 使用专门的EPUB修复工具进行修复
3. **重新获取**: 考虑从其他来源重新获取该文件

### 后续处理步骤
1. **批量编码转换**: 对所有替代TXT文件进行编码转换
2. **重新执行分析**: 基于替代文件重新运行深度分析
3. **生成训练数据**: 基于替代文件生成AI训练数据
4. **质量验证**: 验证最终输出的数据质量和完整性

---

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 保存报告
        report_path = self.organized_dir / 'EPUB弥补性分析报告.md'
        report_path.write_text(report_content, encoding='utf-8')

        print(f"\n{'='*60}")
        print(f"弥补性分析报告已生成: {report_path}")
        print(f"{'='*60}")

        return report_path

    def run_supplementary_analysis(self):
        """运行弥补性分析"""
        print("="*80)
        print("王小波作品EPUB弥补性分析")
        print("="*80)

        # 1. 查找原始EPUB文件
        print("\n1. 查找原始EPUB文件...")
        epub_files = list(self.backup_dir.glob("*.epub"))
        self.analysis_results['total_epub_files'] = len(epub_files)

        print(f"找到 {len(epub_files)} 个原始EPUB文件")

        # 2. 对每个EPUB文件查找替代文件
        print("\n2. 查找替代文件并分析...")
        epub_analysis_results = []

        for epub_file in epub_files:
            epub_result = {
                'epub_filename': epub_file.name,
                'epub_size': epub_file.stat().st_size,
                'parse_status': '需替代',
                'no_alternative': False
            }

            print(f"\n分析: {epub_file.name}")

            # 查找替代文件
            replacement_files = self.find_replacement_files(epub_file)

            if replacement_files:
                # 选择优先级最高的替代文件（TXT优先于PDF）
                replacement_type, replacement_path = replacement_files[0]

                print(f"  找到替代文件: {replacement_path.name} ({replacement_type})")

                epub_result['replacement_type'] = replacement_type
                epub_result['replacement_analysis'] = self.analyze_replacement_file(replacement_type, replacement_path)

                # 统计
                if replacement_type == 'txt':
                    self.analysis_results['replaced_with_txt'] += 1
                elif replacement_type == 'pdf':
                    self.analysis_results['replaced_with_pdf'] += 1
            else:
                print(f"  ⚠️  未找到替代文件")
                epub_result['no_alternative'] = True
                self.analysis_results['no_alternative'] += 1

            epub_analysis_results.append(epub_result)
            self.analysis_results['analyzed_files'].append(epub_result)

        # 3. 生成分析报告
        print("\n3. 生成弥补性分析报告...")
        report_path = self.generate_analysis_report(epub_analysis_results)

        # 4. 总结
        print(f"\n{'='*80}")
        print("弥补性分析完成")
        print(f"{'='*80}")
        print(f"分析EPUB文件: {self.analysis_results['total_epub_files']}")
        print(f"TXT替代: {self.analysis_results['replaced_with_txt']}")
        print(f"PDF替代: {self.analysis_results['replaced_with_pdf']}")
        print(f"无替代: {self.analysis_results['no_alternative']}")
        print(f"详细报告: {report_path}")
        print(f"{'='*80}")

        return epub_analysis_results


if __name__ == "__main__":
    backup_dir = "/home/wy/code1/王小波作品整理版/原始EPUB备份"
    organized_dir = "/home/wy/code1/王小波作品整理版"

    analyzer = SupplementaryAnalyzer(backup_dir, organized_dir)
    analyzer.run_supplementary_analysis()
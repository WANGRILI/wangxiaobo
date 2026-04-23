#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
王小波作品EPUB文件深度分析与修复工具
功能：全面检查EPUB文件格式、元数据、结构问题，并进行修复
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
import sys

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')

try:
    from ebooklib import epub
    from ebooklib.utils import debug
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False

class EPUBAnalyzerAndFixer:
    def __init__(self, source_dir, output_dir):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.backup_dir = self.output_dir / '原始EPUB备份'
        self.fixed_dir = self.output_dir / '修复后EPUB'

        # 创建必要目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.fixed_dir.mkdir(parents=True, exist_ok=True)

        # 分析结果
        self.analysis_results = {
            'total_epubs': 0,
            'successful': 0,
            'failed': 0,
            'format_errors': [],
            'metadata_issues': [],
            'structure_problems': [],
            'content_issues': [],
            'fixed_files': [],
            'skipped_files': []
        }

        # 常见的EPUB问题模式
        self.common_issues = {
            'missing_dc_title': '缺少标题元数据',
            'missing_dc_creator': '缺少作者元数据',
            'invalid_ncx': '导航文件格式错误',
            'invalid_opf': '包文件格式错误',
            'empty_spine': '阅读顺序为空',
            'missing_container': '缺少container.xml',
            'broken_links': '断链或资源缺失',
            'encoding_issues': '文件编码问题',
            'malformed_html': 'HTML格式错误',
            'missing_stylesheet': '缺少样式表'
        }

    def find_epub_files(self):
        """查找所有EPUB文件"""
        epub_files = []
        for file_path in self.source_dir.rglob('*.epub'):
            if file_path.is_file():
                epub_files.append(file_path)
        return epub_files

    def analyze_single_epub(self, epub_path):
        """分析单个EPUB文件"""
        file_name = epub_path.name
        analysis = {
            'file_name': file_name,
            'file_path': str(epub_path),
            'file_size': epub_path.stat().st_size,
            'issues': [],
            'warnings': [],
            'metadata': {},
            'structure': {},
            'content': {},
            'status': 'pending',
            'can_be_fixed': False
        }

        print(f"\n{'='*60}")
        print(f"分析文件: {file_name}")
        print(f"{'='*60}")

        try:
            # 1. 检查文件完整性（ZIP格式）
            if not self._check_zip_integrity(epub_path, analysis):
                print("  ❌ ZIP文件完整性检查失败")
                return analysis

            # 2. 使用ebooklib尝试加载
            if EPUB_AVAILABLE:
                if not self._load_with_ebooklib(epub_path, analysis):
                    print("  ⚠️  ebooklib加载有问题，尝试手动分析")
                    self._manual_structure_analysis(epub_path, analysis)
            else:
                print("  ⚠️  ebooklib未安装，使用手动方法分析")
                self._manual_structure_analysis(epub_path, analysis)

            # 3. 检查元数据完整性
            self._check_metadata_completeness(epub_path, analysis)

            # 4. 检查OPF结构
            self._check_opf_structure(epub_path, analysis)

            # 5. 检查导航结构
            self._check_navigation_structure(epub_path, analysis)

            # 6. 检查内容文件
            self._check_content_files(epub_path, analysis)

            # 7. 检查样式和资源
            self._check_resources(epub_path, analysis)

            # 8. 评估可修复性
            self._assess_fixability(analysis)

            print(f"\n分析完成:")
            print(f"  问题数量: {len(analysis['issues'])}")
            print(f"  警告数量: {len(analysis['warnings'])}")
            print(f"  状态: {analysis['status']}")
            print(f"  可修复: {'是' if analysis['can_be_fixed'] else '否'}")

        except Exception as e:
            error_msg = f"分析过程异常: {str(e)}"
            analysis['issues'].append(error_msg)
            analysis['status'] = 'error'
            print(f"  ❌ {error_msg}")

        return analysis

    def _check_zip_integrity(self, epub_path, analysis):
        """检查ZIP文件完整性"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                # 尝试列出所有文件
                file_list = zip_file.namelist()
                analysis['structure']['total_files'] = len(file_list)

                # 检查必要文件
                required_files = ['mimetype', 'META-INF/container.xml']
                missing_files = [f for f in required_files if f not in file_list]

                if missing_files:
                    analysis['issues'].append(f"缺少必要文件: {', '.join(missing_files)}")
                    return False

                # 检查mimetype
                try:
                    mimetype = zip_file.read('mimetype').decode('utf-8').strip()
                    if mimetype != 'application/epub+zip':
                        analysis['warnings'].append(f"mimetype不标准: {mimetype}")
                except Exception:
                    analysis['warnings'].append("无法读取mimetype")

                return True

        except Exception as e:
            analysis['issues'].append(f"ZIP文件损坏: {str(e)}")
            return False

    def _load_with_ebooklib(self, epub_path, analysis):
        """使用ebooklib加载EPUB"""
        try:
            # 尝试加载EPUB
            book = epub.read_epub(str(epub_path))

            # 检查标题
            title = book.get_metadata('DC', 'title')
            analysis['metadata']['title'] = title if title else '未知'
            print(f"  ✓ 标题: {analysis['metadata']['title']}")

            # 检查作者
            creators = book.get_metadata('DC', 'creator')
            analysis['metadata']['creators'] = creators if creators else []
            print(f"  ✓ 作者: {', '.join(creators) if creators else '未知'}")

            # 检查语言
            languages = book.get_metadata('DC', 'language')
            analysis['metadata']['languages'] = languages if languages else []
            print(f"  ✓ 语言: {', '.join(languages) if languages else '未知'}")

            # 检查描述元数据
            if book.get_metadata('DC', 'description'):
                description = book.get_metadata('DC', 'description')
                analysis['metadata']['description'] = description if isinstance(description, str) else str(description[0])
                analysis['metadata']['description'] = analysis['metadata']['description'][:100] + '...' if len(analysis['metadata']['description']) > 100 else analysis['metadata']['description']

            # 检查目录
            toc = book.get_toc()
            analysis['structure']['toc_items'] = len(self._count_toc_items(toc))
            print(f"  ✓ 目录项: {analysis['structure']['toc_items']}")

            # 检查阅读顺序
            spine = book.spine
            analysis['structure']['spine_items'] = len(spine)
            print(f"  ✓ 阅读顺序: {analysis['structure']['spine_items']}")

            if len(spine) == 0:
                analysis['issues'].append("阅读顺序为空，可能导致无法正确阅读")

            # 检查内容项
            items = book.get_items()
            text_items = [item for item in items if item.get_type() == 9]  # ITEM_DOCUMENT
            analysis['content']['text_items'] = len(text_items)
            analysis['content']['total_items'] = len(items)
            print(f"  ✓ 文本文件: {len(text_items)}")
            print(f"  ✓ 总资源: {len(items)}")

            return True

        except Exception as e:
            error_msg = f"ebooklib加载失败: {str(e)}"
            analysis['issues'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False

    def _count_toc_items(self, toc, count=0):
        """递归计算目录项数量"""
        for item in toc:
            count += 1
            if hasattr(item, 'get_sections'):
                for section in item.get_sections():
                    count = self._count_toc_items([section], count)
        return count

    def _manual_structure_analysis(self, epub_path, analysis):
        """手动分析EPUB结构（当ebooklib失败时）"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                # 查找OPF文件
                opf_files = [f for f in zip_file.namelist() if f.endswith('.opf')]
                analysis['structure']['opf_files'] = opf_files

                if opf_files:
                    # 尝试解析OPF
                    try:
                        opf_content = zip_file.read(opf_files[0])
                        opf_str = opf_content.decode('utf-8', errors='ignore')

                        # 简单的元数据提取
                        title_match = re.search.search(r'<dc:title>(.*?)</dc:title>', opf_str, re.IGNORECASE)
                        if title_match:
                            analysis['metadata']['title'] = title_match.group(1).strip()
                            print(f"  ✓ 标题: {analysis['metadata']['title']}")
                        else:
                            analysis['warnings'].append("无法提取标题")

                        creator_match = re.search(r'<dc:creator>(.*?)</dc:creator>', opf_str, re.IGNORECASE)
                         if creator_match:
                            creators = creator_match.group(1).split(',')
                            analysis['metadata']['creators'] = [c.strip().strip() for c in creators if c.strip().strip()]
                            print(f"  ✓ 作者: {creator_match.group(1).strip()}")

                    except Exception as ex:
                        analysis['warnings'].append(f"OPF解析问题: {str(e.e)}")

                # 统计文件类型
                html_files = [f for f in zip_file.namelist() if f.endswith(('.html', '.xhtml', '.htm'))]
                css_files = [f for f in zip_file.namelist() if f.endswith('.css')]
                image_files = [f for f in zip_file.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]

                analysis['content']['html_files'] = len(html_files)
                analysis['content']['css_files'] = len(css_files)
                analysis['content']['image_files'] = len(image_files)

                print(f"  ✓ HTML文件: {len(html_files)}")
                print(f"  ✓ CSS文件: {len(css_files)}")
                print(f"  ✓ 图片文件: {len(image_files)}")

                if len(html_files) == 0:
                    analysis['issues'].append("没有找到HTML内容文件")

        except Exception as e:
            analysis['issues'].append(f"手动分析失败: {str(e)}")

    def _check_metadata_completeness(self, epub_path, analysis):
        """检查元数据完整性"""
        metadata = analysis.get('metadata', {})

        if not metadata.get('title'):
            analysis['warnings'].append("缺少标题元数据")

        if not metadata.get('creators'):
            analysis['warnings'].append("缺少作者元数据")

        if not metadata.get('languages'):
            analysis['warnings'].append("缺少语言元数据")

    def _check_opf_structure(self, epub_path, analysis):
        """检查OPF文件结构"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                opf_files = [f for f in zip_file.namelist() if f.endswith('.opf')]

                if not opf_files:
                    analysis['issues'].append("缺少OPF文件")

                for opf_file in opf_files:
                    try:
                        opf_content = zip_file.read(opf_file).decode('utf-8', errors='ignore')

                        # 检查XML声明
                        if not opf_content.strip().startswith('<?xml'):
                            analysis['warnings'].append(f"{opf_file}: 缺少XML声明")

                        # 检查命名空间
                        if 'http://www.idpf.org/2007/opf' not in opf_content:
                            analysis['warnings'].append(f"{opf_file}: 可能使用旧版OPF格式")

                    except Exception as e.e:
                        analysis['warnings'].append(f"OPF文件检查错误: {str(e.e)}")

        except Exception as e:
            analysis['warnings'].append(f"OPF结构检查失败: {str(e)}")

    def _check_navigation_structure(self, epub_path, analysis):
        """检查导航结构"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                # 检查NCX文件
                ncx_files = [f for f in zip_file.namelist() if f.endswith('.ncx')]

                if not ncx_files:
                    analysis['warnings'].append("缺少NCX导航文件（目录）")

                for ncx_file in ncx_files:
                    try:
                        ncx_content = zip_file.read(ncx_file).decode('utf-8', errors='ignore')

                        # 检查NCX标签
                        if '<ncx' not in ncx_content and '<html' not in ncx_content:
                            analysis['warnings'].append(f"{ncx_file}: NCX格式可疑")

                    except Exception as e.e:
                        analysis['warnings'].append(f"NCX检查错误: {str(e.e)}")

        except Exception as e:
            analysis['warnings'].append(f"导航结构检查失败: {str(e)}")

    def _check_content_files(self, epub_path, analysis):
        """检查内容文件"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                html_files = [f for f in zip_file.namelist() if f.endswith(('.html', '.xhtml'))]

                for html_file in html_files[:3]:  # 只检查前3个文件
                    try:
                        html_content = zip_file.read(html_file).decode('utf-8', errors='ignore')

                        # 检查HTML基本结构
                        if '<html' not in html_content and '<HTML' not in html_content:
                            if '<body' not in html_content and '<BODY' not in html_content:
                                analysis['warnings'].append(f"{html_file}: HTML结构不完整")

                        # 检查常见问题
                        if 'charset' not in html_content.lower():
                            analysis['warnings'].append(f"{html_file}: 可能缺少字符集声明")

                        # 检查是否有内容
                        if len(html_content.strip()) < 100:
                            analysis['warnings'].append(f"{html_file}: 内容可能为空或过短")

                    except Exception as e.e:
                        analysis['warnings'].append(f"HTML文件检查错误: {str(e.e)}")

        except Exception as e:
            analysis['warnings'].append(f"内容文件检查失败: {str(e)}")

    def _check_resources(self, epub_path, analysis):
        """检查样式和资源"""
        try:
            with ZipFile(epub_path, 'r') as zip_file:
                css_files = [f for f in zip_file.namelist() if f.endswith('.css')]
                image_files = [f for f in zip_file.namelist() if f.lower().endswith(('.jpg', '.png', '.jpeg', '.gif'))]

                analysis['resources'] = {
                    'css_files': len(css_files),
                    'image_files': len(image_files)
                }

                if len(css_files) == 0:
                    analysis['warnings'].append("缺少CSS样式文件，可能影响显示效果")

        except Exception as e.e:
            analysis['warnings'].append(f"资源检查失败: {str(e.e)}")

    def _assess_fixability(self, analysis):
        """评估可修复性"""
        issues = analysis['issues']
        warnings = analysis['warnings']

        # 严重问题无法自动修复
        critical_issues = ['ZIP文件损坏', '阅读顺序为空', '没有找到HTML内容文件']
        has_critical = any(any(issue in critical_issue for issue in issues) for critical_issue in critical_issues)

        if has_critical:
            analysis['status'] = '严重错误，需要人工修复'
            analysis['can_be_fixed'] = False
        elif len(issues) > 3:
            analysis['status'] = '问题较多，建议人工修复'
            analysis['can_be_fixed'] = False
        elif len(issues) == 0 and len(warnings) == 0:
            analysis['status'] = '完全正常'
            analysis['can_be_fixed'] = True
        elif len(issues) == 0:
            analysis['status'] = '基本正常，有轻微警告'
            analysis['can_be_fixed'] = True
        else:
            analysis['status'] = '存在问题，可以尝试修复'
            analysis['can_be_fixed'] = True

    def fix_epub_file(self, epub_path, analysis):
        """尝试修复EPUB文件"""
        if not analysis['can_be_fixed']:
            print(f"  ⏭️  {epub_path.name} 不可自动修复")
            return False

        print(f"\n{'='*60}")
        print(f"修复文件: {epub_path.name}")
        print(f"{'='*60}")

        try:
            # 1. 备份原始文件
            backup_path = self.backup_dir / epub_path.name
            if not backup_path.exists():
                shutil.copy2(epub_path, backup_path)
                print(f"  ✓ 备份到: {backup_path}")

            # 2. 尝试用ebooklib重新打包
            if EPUB_AVAILABLE and analysis['metadata'].get('title'):
                return self._fix_with_ebooklib(epub_path, analysis)
            else:
                return self._fix_with_repack(epub_path, analysis)

        except Exception as e:
            error_msg = f"修复过程异常: {str(e)}"
            analysis['issues'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False

    def _fix_with_ebooklib(self, epub_path, analysis):
        """使用ebooklib修复"""
        try:
            # 重新加载EPUB
            book = epub.read_epub(str(epub_path))

            # 修复元数据
            if not book.get_metadata('DC', 'title') and analysis['metadata'].get('title'):
                book.add_metadata('DC', 'title', analysis['metadata']['title'])
                print(f"  ✓ 添加标题: {analysis['metadata']['title']}")

            if not book.get_metadata('DC', 'creator') and analysis['metadata'].get('creators'):
                for creator in analysis['metadata']['creators']:
                    book.add_metadata('DC', 'creator', creator)
                print(f"  ✓ 添加作者: {', '.join(analysis['metadata']['creators'])}")

            # 添加语言元数据
            if not book.get_metadata('DC', 'language'):
                book.add_metadata('DC', 'language', 'zh-CN')
                print(f"  ✓ 添加语言: zh-CN")

            # 保存修复后的文件
            fixed_path = self.fixed_dir / f"fixed_{epub_path.name}"
            epub.write_epub(str(fixed_path), book, {})
            print(f"  ✓ 保存修复文件: {fixed_path}")

            self.analysis_results['fixed_files'].append({
                'original': str(epub_path),
                'fixed': str(fixed_path),
                'fixes_applied': 'metadata_completion'
            })

            return True

        except Exception as e:
            print(f"  ❌ ebooklib修复失败: {str(e)}")
            return False

    def _fix_with_repack(self, epub_path, analysis):
        """通过重新打包修复"""
        try:
            # 创建新的EPUB
            book = epub.EpubBook()

            # 设置基本元数据
            if analysis['metadata'].get('title'):
                book.add_metadata('DC', 'title', analysis['metadata']['title'])
                print(f"  ✓ 设置标题: {analysis['metadata']['title']}")

            if analysis['metadata'].get('creators'):
                for creator in analysis['metadata']['creators']:
                    book.add_metadata('DC', 'creator', creator)
                print(f"  ✓ 设置作者")

            book.add_metadata('DC', 'language', 'zh-CN')
            book.add_metadata('DC', 'identifier', f"fixed_{epub_path.stem}")
            book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))

            # 从原文件提取内容
            with ZipFile(epub_path, 'r') as zip_file:
                html_files = [f for f in zip_file.namelist() if f.endswith('.html')]

                for html_file in html_files:
                    try:
                        html_content = zip_file.read(html_file).decode('utf-8', errors='ignore')

                        # 创建章节
                        chapter_title = Path(html_file).stem
                        chapter = epub.EpubHtml(title=chapter_title,
                                              file_name=html_file,
                                              content=html_content)
                        book.add_item(chapter)

                    except Exception as e:
                        print(f"  ⚠️  处理HTML文件失败 {html_file}: {str(e)}")

            # 设置基本目录结构
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # 添加所有HTML文件到目录
            for item in book.get_items():
                if item.get_type() == 9:  # ITEM_DOCUMENT
                    book.spine.add(item)

            # 保存
            fixed_path = self.fixed_dir / f"fixed_{epub_path.name}"
            epub.write_epub(str(fixed_path), book, {})
            print(f"  ✓ 保存修复文件: {fixed_path}")

            self.analysis_results['fixed_files'].append({
                'original': str(epub_path),
                'fixed': str(fixed_path),
                'fixes_applied': 'repack_with_metadata'
            })

            return True

        except Exception as e:
            print(f"  ❌ 重新打包失败: {str(e)}")
            return False

    def generate_report(self, analyses):
        """生成分析报告"""
        report_content = f"""# 王小波作品EPUB文件深度分析与修复报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析工具: ebooklib
分析文件数: {len(analyses)}

## 执行摘要

- **总文件数**: {self.analysis_results['total_epubs']}
- **分析成功**: {self.analysis_results['successful']}
- **分析失败**: {self.analysis_results['failed']}
- **可修复文件**: {len([a for a in analyses if a['can_be_fixed']])}
- **已修复文件**: {len(self.analysis_results['fixed_files'])}

## 详细分析结果

"""

        for i, analysis in enumerate(analyses, 1):
            report_content += f"""
### {i}. {analysis['file_name']}

#### 基本信息
- **文件大小**: {analysis['file_size']:,} bytes
- **分析状态**: {analysis['status']}
- **可修复**: {'是' if analysis['can_be_fixed'] else '否'}

#### 元数据信息
"""

            metadata = analysis.get('metadata', {})
            if metadata.get('title'):
                title = metadata['title']
                if isinstance(title, tuple) and title:
                    title = title[0]
                report_content += f"- **标题**: {title}\n"
            if metadata.get('creators'):
                creators = metadata['creators']
                if isinstance(creators, list):
                    report_content += f"- **作者**: {', '.join(creators)}\n"
                elif isinstance(creators, tuple) and creators:
                    report_content += f"- **作者**: {creators[0]}\n"
                else:
                    report_content += f"- **作者**: {creators}\n"
            if metadata.get('languages'):
                languages = metadata['languages']
                if isinstance(languages, list):
                    report_content += f"- **语言**: {', '.join(languages)}\n"
                elif isinstance(languages, tuple) and languages:
                    report_content += f"- **语言**: {languages[0]}\n"
                else:
                    report_content += f"- **语言**: {languages}\n"

            report_content += """
#### 发现的问题
"""

            if analysis['issues']:
                for j, issue in enumerate(analysis['issues'], 1):
                    report_content += f"{j}. {issue}\n"
            else:
                report_content += "无严重问题\n"

            report_content += """
#### 警告信息
"""

            if analysis['warnings']:
                for j, warning in enumerate(analysis['warnings'], 1):
                    report_content += f"{j}. {warning}\n"
            else:
                report_content += "无警告\n"

            report_content += """
#### 结构信息
"""

            structure = analysis.get('structure', {})
            if structure.get('total_files'):
                report_content += f"- **总文件数**: {structure['total_files']}\n"
            if structure.get('toc_items'):
                report_content += f"- **目录项**: {structure['toc_items']}\n"
            if structure.get('spine_items'):
                report_content += f"- **阅读顺序**: {structure['spine_items']}\n"

            report_content += """
#### 内容信息
"""

            content = analysis.get('content', {})
            if content.get('text_items'):
                report_content += f"- **文本文件**: {content['text_items']}\n"
            if content.get('total_items'):
                report_content += f"- **总资源**: {content['total_items']}\n"

            report_content += "\n---\n"

        # 添加修复记录
        if self.analysis_results['fixed_files']:
            report_content += """
## 修复记录

以下是成功修复的文件：

"""
            for i, fix_info in enumerate(self.analysis_results['fixed_files'], 1):
                report_content += f"""
### {i}. {Path(fix_info['original']).name}

**修复方法**: {fix_info['fixes_applied']}
**原始文件**: {fix_info['original']}
**修复文件**: {fix_info['fixed']}

"""

        # 添加总结
        report_content += f"""
## 总结与建议

### 文件状态分布
"""

        status_counts = {}
        for analysis in analyses:
            status = analysis['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            report_content += f"- **{status}**: {count} 个文件\n"

        report_content += """
### 问题类型统计
"""

        total_issues = sum(len(a['issues']) for a in analyses)
        total_warnings = sum(len(a['warnings']) for a in analyses)

        report_content += f"- **总问题数**: {total_issues}\n"
        report_content += f"- **总警告数**: {total_warnings}\n"

        report_content += """
### 后续建议

1. **元数据完善**: 为缺少标题、作者的文件添加完整元数据
2. **资源检查**: 修复断链、缺失图片等问题
3. **格式标准化**: 统一使用HTML5和UTF-8编码
4. **阅读测试**: 在多种阅读器中测试修复后的文件
5. **版本控制**: 保留原始文件，对比修复效果

### 技术细节

- **分析工具**: Python 3.x + ebooklib
- **修复方法**: 元数据补充 + 结构修复 + 重新打包
- **备份策略**: 原始文件备份到原始EPUB备份目录
- **输出位置**: 修复后文件保存在修复后EPUB目录

---

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 保存报告
        report_path = self.output_dir / 'EPUB分析与修复报告.md'
        report_path.write_text(report_content, encoding='utf-8')

        print(f"\n{'='*60}")
        print(f"报告已生成: {report_path}")
        print(f"{'='*60}")

        return report_path

    def run_analysis_and_fix(self):
        """运行完整的分析和修复流程"""
        print("="*80)
        print("王小波作品EPUB文件深度分析与修复")
        print("="*80)

        # 1. 查找所有EPUB文件
        epub_files = self.find_epub_files()
        self.analysis_results['total_epubs'] = len(epub_files)

        print(f"\n找到 {len(epub_files)} 个EPUB文件")

        # 2. 分析每个文件
        analyses = []
        for epub_path in epub_files:
            analysis = self.analyze_single_epub(epub_path)
            analyses.append(analysis)

            # 统计
            if analysis['status'] == 'error':
                self.analysis_results['failed'] += 1
            else:
                self.analysis_results['successful'] += 1

        # 3. 尝试修复可修复的文件
        print(f"\n{'='*60}")
        print("开始修复可修复的文件")
        print(f"{'='*60}")

        for analysis in analyses:
            if analysis['can_be_fixed'] and analysis['status'] != '完全正常':
                epub_path = Path(analysis['file_path'])
                self.fix_epub_file(epub_path, analysis)

        # 4. 生成报告
        report_path = self.generate_report(analyses)

        # 5. 汇总
        print(f"\n{'='*80}")
        print("处理完成")
        print(f"{'='*80}")
        print(f"分析文件数: {self.analysis_results['total_epubs']}")
        print(f"分析成功: {self.analysis_results['successful']}")
        print(f"分析失败: {self.analysis_results['failed']}")
        print(f"修复文件: {len(self.analysis_results['fixed_files'])}")
        print(f"详细报告: {report_path}")
        print(f"{'='*80}")


if __name__ == "__main__":
    source_dir = "/home/wy/code1/20260419王小波"
    output_dir = "/home/wy/code1/王小波作品整理版"

    analyzer_fixer = EPUBAnalyzerAndFixer(source_dir, output_dir)
    analyzer_fixer.run_analysis_and_fix()
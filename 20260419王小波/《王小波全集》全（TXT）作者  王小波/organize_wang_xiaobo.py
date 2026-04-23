# 王小波作品整理执行脚本

import os
import sys
import hashlib
import shutil
import json
from pathlib import Path
from datetime import datetime

class WangXiaoboOrganizer:
    def __init__(self, source_dir, output_dir):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.config = {
            'source_dir': str(source_dir),
            'output_dir': str(output_dir),
            'section_min_words': 1000,
            'section_max_words': 2000,
            'copy_only': True,
            'tasks_priority': [
                'epub_extract',
                'deduplicate',
                'encoding_convert',
                'structure_analysis'
            ]
        }

        # 标准书名映射表
        self.book_name_mapping = self._init_book_mapping()

        # 作品分类映射
        self.book_classification = self._init_classification()

        # 处理结果记录
        self.results = {
            'total_files': 0,
            'processed_files': 0,
            'duplicates_found': 0,
            'encoding_converted': 0,
            'epub_extracted': 0,
            'books_organized': 0,
            'training_sections': 0,
            'errors': []
        }

    def _init_book_mapping(self):
        """初始化标准书名映射"""
        return {
            '黄金时代.txt': '黄金时代',
            '《青铜时代》红拂夜奔.txt': '红拂夜奔',
            '红拂夜奔.txt': '红拂夜奔',
            '《青铜时代》万寿寺.txt': '万寿寺',
            '《青铜时代》寻找无双.txt': '寻找无双',
            '寻找无双.txt': '寻找无双',
            '革命时期的爱情.txt': '革命时期的爱情',
            '革命时期的爱情-王小波.epub': '革命时期的爱情',
            '似水流年.txt': '似水流年',
            '我的阴阳两届.txt': '我的阴阳两界',
            '我的阴阳两界-王小波.epub': '我的阴阳两界',
            '白银时代.txt': '白银时代',
            '未来世界-王小波.epub': '未来世界',
            '未来世界（上）我的舅舅.txt': '未来世界',
            '未来世界（下） 我自己.txt': '未来世界',
            '三十而立.txt': '三十而立',
            '东宫西宫.txt': '东宫西宫',
            '地久天长.txt': '地久天长',
            '夜行记.txt': '夜行记',
            '夜里两点钟.txt': '夜里两点钟',
            '立新街甲一号与昆仑奴.txt': '立新街甲一号与昆仑奴',
            '红线盗盒.txt': '红线盗盒',
            '舅舅情人.txt': '舅舅情人',
            '茫茫黑夜漫游.txt': '茫茫黑夜漫游',
            '南瓜豆腐.txt': '南瓜豆腐',
            '似水柔情.txt': '似水柔情',
            '人妖.txt': '人妖',
            '2010.txt': '2010',
            '2015.txt': '2015',
            '沉默的大多数：王小波杂文随笔全编.epub': '沉默的大多数',
            '思维的乐趣-王小波.epub': '思维的乐趣',
            '我的精神家园-王小波.epub': '我的精神家园',
            '人为什么活着-王小波.epub': '人为什么活着',
            '爱你就像爱生命-王小波,李银河.epub': '爱你就像爱生命',
            '王小波与李银河书信集.txt': '王小波书信集',
            '王小波全集.第九卷·书信-王小波.epub': '王小波书信集',
            '他们的世界.txt': '他们的世界',
            '王小波全集.第十卷.未竟稿-王小波.epub': '未竟稿',
            '怀疑三部曲-王小波.epub': '怀疑三部曲',
            '大学四年级-王小波.epub': '大学四年级',
            '不成功的爱情-王小波.epub': '不成功的爱情'
        }

    def _init_classification(self):
        """初始化作品分类"""
        return {
            '长篇小说': [
                '黄金时代', '革命时期的爱情', '似水流年', '我的阴阳两界',
                '万寿寺', '红拂夜奔', '寻找无双', '白银时代', '未来世界'
            ],
            '中短篇小说': [
                '三十而立', '东宫西宫', '地久天长', '夜行记', '夜里两点钟',
                '立新街甲一号与昆仑奴', '红线盗盒', '舅舅情人', '茫茫黑夜漫游',
                '南瓜豆腐', '似水柔情', '人妖', '2010', '2015',
                '大学四年级', '不成功的爱情'
            ],
            '杂文随笔': [
                '沉默的大多数', '思维的乐趣', '我的精神家园', '人为什么活着'
            ],
            '书信集': [
                '爱你就像爱生命', '王小波书信集'
            ],
            '学术研究': [
                '他们的世界', '未竟稿', '怀疑三部曲'
            ]
        }

    def scan_files(self):
        """扫描源目录中的所有文件"""
        print("=== 扫描文件 ===")
        files = []
        for file_path in self.source_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                file_info = {
                    'path': file_path,
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'extension': file_path.suffix.lower()
                }
                files.append(file_info)

        self.results['total_files'] = len(files)
        print(f"找到 {len(files)} 个文件")
        return files

    def calculate_file_hash(self, file_path):
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None

    def standardize_book_name(self, filename):
        """将文件名标准化为书名"""
        # 直接映射
        if filename in self.book_name_mapping:
            return self.book_name_mapping[filename]

        # 去掉扩展名和作者信息
        name = filename

        # 去掉扩展名
        if '.' in name:
            name = '.'.join(name.split('.')[:-1])

        # 去掉"-王小波"等后缀
        name = name.replace('-王小波', '')
        name = name.replace(',李银河', '')
        name = name.replace('王小波,', '')

        # 去掉《》括号
        name = name.replace('《', '').replace('》', '')

        # 去掉系列前缀
        name = name.replace('《青铜时代》', '')
        name = name.replace('青铜时代', '')

        # 特殊处理
        if '我的阴阳两届' in name:
            return '我的阴阳两界'

        return name.strip()

    def classify_book(self, book_name):
        """确定作品的分类"""
        for category, books in self.book_classification.items():
            if book_name in books:
                return category
        return '独立杂文'  # 默认分类

    def identify_duplicates(self, files):
        """识别重复文件"""
        print("=== 识别重复文件 ===")
        book_groups = {}
        file_hashes = {}

        # 按标准书名分组
        for file_info in files:
            standard_name = self.standardize_book_name(file_info['name'])

            if standard_name not in book_groups:
                book_groups[standard_name] = []
            book_groups[standard_name].append(file_info)

        # 检测重复
        duplicates = {}
        for book_name, book_files in book_groups.items():
            if len(book_files) > 1:
                duplicates[book_name] = book_files
                print(f"发现重复: {book_name} ({len(book_files)}个版本)")

        self.results['duplicates_found'] = sum(len(files) for files in duplicates.values())
        return book_groups, duplicates

    def create_directory_structure(self):
        """创建目录结构"""
        print("=== 创建目录结构 ===")
        categories = ['长篇小说', '中短篇小说', '杂文随笔', '书信集', '学术研究']

        for category in categories:
            category_dir = self.output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            print(f"创建目录: {category_dir}")

    def copy_file_with_metadata(self, source_file, target_dir):
        """复制文件并创建元数据"""
        try:
            target_file = target_dir / source_file.name
            shutil.copy2(source_file, target_file)

            # 创建README文件
            readme_content = f"""# {source_file.name}

## 来源信息
- 原始路径: {source_file}
- 文件大小: {source_file.stat().st_size:,} bytes
- 复制时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 处理说明
此文件为原始文件的副本，未进行任何修改。
"""
            readme_path = target_dir / 'README.md'
            if not readme_path.exists():
                readme_path.write_text(readme_content, encoding='utf-8')

            self.results['processed_files'] += 1
            return True

        except Exception as e:
            print(f"复制失败 {source_file}: {e}")
            self.results['errors'].append({
                'file': str(source_file),
                'error': str(e),
                'type': 'copy_error'
            })
            return False

    def organize_books(self, book_groups):
        """组织书籍到分类目录"""
        print("=== 组织书籍 ===")

        for book_name, book_files in book_groups.items():
            category = self.classify_book(book_name)

            # 对于有多个版本的文件，优先选择EPUB
            primary_file = None
            for file_info in book_files:
                if file_info['extension'] == '.epub':
                    primary_file = file_info
                    break
            if primary_file is None and book_files:
                primary_file = book_files[0]

            if primary_file:
                # 创建作品目录
                book_dir = self.output_dir / category / book_name
                book_dir.mkdir(parents=True, exist_ok=True)

                # 复制文件
                success = self.copy_file_with_metadata(
                    primary_file['path'],
                    book_dir
                )

                if success:
                    self.results['books_organized'] += 1
                    print(f"组织: {book_name} -> {category}")

    def generate_catalog(self, book_groups):
        """生成作品清单"""
        print("=== 生成作品清单 ===")

        catalog_content = """# 王小波作品集标准清单

生成时间: {}
源目录: {}
输出目录: {}

## 作品分类统计

""".format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            self.source_dir,
            self.output_dir
        )

        # 按分类组织
        category_stats = {}
        for category, books in self.book_classification.items():
            found_books = [book for book in books if book in book_groups]
            category_stats[category] = found_books

            catalog_content += f"\n### {category} ({len(found_books)}部)\n\n"

            for book_name in found_books:
                book_files = book_groups[book_name]
                catalog_content += f"#### {book_name}\n\n"

                for file_info in book_files:
                    catalog_content += f"- 文件名: {file_info['name']}\n"
                    catalog_content += f"  大小: {file_info['size']:,} bytes\n"
                    catalog_content += f"  格式: {file_info['extension']}\n"
                    catalog_content += "\n"

        # 添加独立杂文
        independent_essays = []
        for book_name in book_groups.keys():
            if book_name not in sum(self.book_classification.values(), []):
                independent_essays.append(book_name)

        if independent_essays:
            catalog_content += f"\n### 独立杂文 ({len(independent_essays)}篇)\n\n"
            for essay_name in sorted(independent_essays):
                book_files = book_groups[essay_name]
                catalog_content += f"#### {essay_name}\n\n"
                for file_info in book_files:
                    catalog_content += f"- 文件名: {file_info['name']}\n"
                    catalog_content += f"  大小: {file_info['size']:,} bytes\n"
                    catalog_content += "\n"

        # 保存清单
        catalog_path = self.output_dir / '作品清单.md'
        catalog_path.write_text(catalog_content, encoding='utf-8')
        print(f"作品清单已生成: {catalog_path}")

    def generate_report(self):
        """生成处理报告"""
        print("=== 生成处理报告 ===")

        report_content = """# 王小波作品整理处理报告

## 执行概要

- 扫描文件总数: {total_files}
- 处理文件数: {processed_files}
- 发现重复文件: {duplicates_found}
- 组织书籍数: {books_organized}
- 生成训练小节数: {training_sections}

## 配置参数

- 源目录: {source_dir}
- 输出目录: {output_dir}
- 仅复制模式: {copy_only}
- 任务优先级: {tasks}

## 错误记录

{error_section}

## 完成时间

{timestamp}
""".format(
            total_files=self.results['total_files'],
            processed_files=self.results['processed_files'],
            duplicates_found=self.results['duplicates_found'],
            books_organized=self.results['books_organized'],
            training_sections=self.results['training_sections'],
            source_dir=self.source_dir,
            output_dir=self.output_dir,
            copy_only=self.config['copy_only'],
            tasks=', '.join(self.config['tasks_priority']),
            error_section=self._format_errors(),
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        report_path = self.output_dir / '处理报告.md'
        report_path.write_text(report_content, encoding='utf-8')
        print(f"处理报告已生成: {report_path}")

    def _format_errors(self):
        """格式化错误信息"""
        if not self.results['errors']:
            return "无错误"

        error_text = ""
        for i, error in enumerate(self.results['errors'], 1):
            error_text += f"{i}. {error['file']}\n"
            error_text += f"   错误类型: {error['type']}\n"
            error_text += f"   错误信息: {error['error']}\n\n"

        return error_text

    def run(self):
        """执行整理流程"""
        print("=" * 60)
        print("王小波作品集整理")
        print("=" * 60)

        # 第一步：扫描文件
        files = self.scan_files()

        # 第二步：识别重复
        book_groups, duplicates = self.identify_duplicates(files)

        # 第三步：创建目录结构
        self.create_directory_structure()

        # 第四步：组织书籍
        self.organize_books(book_groups)

        # 第五步：生成清单
        self.generate_catalog(book_groups)

        # 第六步：生成报告
        self.generate_report()

        print("=" * 60)
        print("整理完成!")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)


if __name__ == "__main__":
    source_dir = "/home/wy/code1/20260419王小波"
    output_dir = "/home/wy/code1/王小波作品整理版"

    organizer = WangXiaoboOrganizer(source_dir, output_dir)
    organizer.run()
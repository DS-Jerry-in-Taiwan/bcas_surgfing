#!/usr/bin/env python3
"""
現有爬蟲系統分析工具
用於階段 0 的系統分析工作
"""

import os
import sys
import ast
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse

class CrawlerAnalyzer:
    """爬蟲代碼分析器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.crawlers_dir = self.project_root / "src" / "crawlers"
        
    def find_crawler_files(self) -> List[Path]:
        """查找所有爬蟲文件"""
        crawler_files = []
        
        # 查找所有 .py 文件
        for py_file in self.crawlers_dir.rglob("*.py"):
            # 排除 __pycache__ 和測試文件
            if "__pycache__" not in str(py_file) and "test" not in py_file.name.lower():
                crawler_files.append(py_file)
        
        return sorted(crawler_files)
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """分析單個文件"""
        analysis = {
            "file_path": str(file_path.relative_to(self.project_root)),
            "file_name": file_path.name,
            "size_kb": file_path.stat().st_size / 1024,
            "lines": 0,
            "imports": [],
            "functions": [],
            "classes": [],
            "dependencies": set(),
            "issues": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                analysis["lines"] = len(content.split('\n'))
                
                # 解析 AST
                tree = ast.parse(content)
                
                # 分析導入
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis["imports"].append(alias.name)
                            analysis["dependencies"].add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            full_import = f"{module}.{alias.name}" if module else alias.name
                            analysis["imports"].append(full_import)
                            analysis["dependencies"].add(module.split('.')[0] if module else alias.name)
                    
                    # 分析函數定義
                    elif isinstance(node, ast.FunctionDef):
                        func_info = {
                            "name": node.name,
                            "line": node.lineno,
                            "args": len(node.args.args),
                            "decorators": [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []
                        }
                        analysis["functions"].append(func_info)
                    
                    # 分析類定義
                    elif isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "line": node.lineno,
                            "methods": [],
                            "bases": [ast.unparse(base) for base in node.bases]
                        }
                        
                        # 分析類中的方法
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_info["methods"].append(item.name)
                        
                        analysis["classes"].append(class_info)
        
        except Exception as e:
            analysis["issues"].append(f"解析錯誤: {str(e)}")
        
        return analysis
    
    def analyze_dependencies(self, files_analysis: List[Dict]) -> Dict[str, Any]:
        """分析依賴關係"""
        dependencies = {}
        
        for analysis in files_analysis:
            file_name = analysis["file_name"]
            for dep in analysis["dependencies"]:
                if dep:  # 排除空字符串
                    if dep not in dependencies:
                        dependencies[dep] = []
                    dependencies[dep].append(file_name)
        
        # 過濾掉 Python 標準庫
        std_libs = {
            'os', 'sys', 'json', 'time', 'datetime', 're', 'collections',
            'typing', 'pathlib', 'logging', 'math', 'random', 'itertools'
        }
        
        external_deps = {k: v for k, v in dependencies.items() if k not in std_libs}
        
        return {
            "all_dependencies": dependencies,
            "external_dependencies": external_deps,
            "total_external_deps": len(external_deps)
        }
    
    def generate_report(self, output_dir: Path = None):
        """生成分析報告"""
        if output_dir is None:
            output_dir = self.project_root / "docs" / "agent_context" / "spider_migration_plan" / "phase_0_preparation"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("開始分析現有爬蟲系統...")
        print(f"項目根目錄: {self.project_root}")
        print(f"爬蟲目錄: {self.crawlers_dir}")
        
        # 查找爬蟲文件
        crawler_files = self.find_crawler_files()
        print(f"找到 {len(crawler_files)} 個爬蟲文件:")
        
        for file in crawler_files:
            print(f"  - {file.relative_to(self.project_root)}")
        
        # 分析每個文件
        files_analysis = []
        for file in crawler_files:
            print(f"分析文件: {file.name}...")
            analysis = self.analyze_file(file)
            files_analysis.append(analysis)
        
        # 分析依賴關係
        print("分析依賴關係...")
        deps_analysis = self.analyze_dependencies(files_analysis)
        
        # 生成統計數據
        total_lines = sum(a["lines"] for a in files_analysis)
        total_size_kb = sum(a["size_kb"] for a in files_analysis)
        total_functions = sum(len(a["functions"]) for a in files_analysis)
        total_classes = sum(len(a["classes"]) for a in files_analysis)
        
        # 生成報告
        report = {
            "summary": {
                "total_files": len(crawler_files),
                "total_lines": total_lines,
                "total_size_kb": round(total_size_kb, 2),
                "total_functions": total_functions,
                "total_classes": total_classes,
                "total_external_dependencies": deps_analysis["total_external_deps"]
            },
            "files": files_analysis,
            "dependencies": deps_analysis,
            "recommendations": self.generate_recommendations(files_analysis, deps_analysis)
        }
        
        # 保存報告
        report_file = output_dir / "existing_system_analysis.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析完成! 報告已保存到: {report_file}")
        
        # 輸出摘要
        print("\n" + "="*50)
        print("現有系統分析摘要")
        print("="*50)
        print(f"總文件數: {report['summary']['total_files']}")
        print(f"總代碼行數: {report['summary']['total_lines']}")
        print(f"總大小: {report['summary']['total_size_kb']} KB")
        print(f"總函數數: {report['summary']['total_functions']}")
        print(f"總類數: {report['summary']['total_classes']}")
        print(f"外部依賴數: {report['summary']['total_external_dependencies']}")
        
        # 輸出主要爬蟲文件
        print("\n主要爬蟲文件:")
        main_crawlers = ['cb_master.py', 'stock_master.py', 'tpex_daily.py', 'tpex_csv_batch_fetcher.py']
        for crawler in main_crawlers:
            for analysis in files_analysis:
                if analysis["file_name"] == crawler:
                    print(f"  - {crawler}: {analysis['lines']} 行, {len(analysis['functions'])} 個函數")
        
        # 輸出外部依賴
        print("\n主要外部依賴:")
        for dep, files in deps_analysis["external_dependencies"].items():
            if len(files) >= 2:  # 被多個文件使用的依賴
                print(f"  - {dep}: 被 {len(files)} 個文件使用")
        
        return report
    
    def generate_recommendations(self, files_analysis: List[Dict], deps_analysis: Dict) -> List[str]:
        """生成遷移建議"""
        recommendations = []
        
        # 分析主要爬蟲文件
        main_crawlers = {
            'cb_master.py': '可轉債 Master 爬蟲',
            'stock_master.py': '股票 Master 爬蟲',
            'tpex_daily.py': 'TPEX Daily 爬蟲',
            'tpex_csv_batch_fetcher.py': 'TPEX CSV 批次處理'
        }
        
        for filename, description in main_crawlers.items():
            for analysis in files_analysis:
                if analysis["file_name"] == filename:
                    lines = analysis["lines"]
                    functions = len(analysis["functions"])
                    classes = len(analysis["classes"])
                    
                    complexity = "簡單" if lines < 200 else "中等" if lines < 500 else "複雜"
                    
                    recommendations.append(
                        f"{description} ({filename}): {lines} 行代碼, {functions} 個函數, {classes} 個類 - 複雜度: {complexity}"
                    )
        
        # 依賴分析建議
        external_deps = deps_analysis["external_dependencies"]
        if "requests" in external_deps:
            recommendations.append("檢測到 requests 庫使用，遷移到 Feapder 時需要重寫網路請求邏輯")
        
        if "pandas" in external_deps:
            recommendations.append("檢測到 pandas 庫使用，需要確保 Feapder 的 Pipeline 能處理 DataFrame")
        
        if "beautifulsoup4" in external_deps or "bs4" in external_deps:
            recommendations.append("檢測到 BeautifulSoup 使用，Feapder 內建解析器可能需調整")
        
        # 遷移優先級建議
        recommendations.append("\n遷移優先級建議:")
        recommendations.append("1. cb_master.py - 核心業務數據，邏輯相對獨立")
        recommendations.append("2. stock_master.py - 與 cb_master 類似，可重用模式")
        recommendations.append("3. tpex_daily.py - 日級數據，需要排程機制")
        recommendations.append("4. tpex_csv_batch_fetcher.py - 批次處理，需要特殊處理")
        
        return recommendations

def main():
    parser = argparse.ArgumentParser(description="現有爬蟲系統分析工具")
    parser.add_argument("--project-root", default=".", help="項目根目錄路徑")
    parser.add_argument("--output-dir", help="輸出目錄路徑")
    
    args = parser.parse_args()
    
    analyzer = CrawlerAnalyzer(args.project_root)
    
    try:
        report = analyzer.generate_report(
            Path(args.output_dir) if args.output_dir else None
        )
        
        # 生成 Markdown 報告
        if args.output_dir:
            output_dir = Path(args.output_dir)
            md_file = output_dir / "existing_system_analysis.md"
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write("# 現有爬蟲系統分析報告\n\n")
                f.write("## 系統概覽\n\n")
                f.write(f"- **總文件數**: {report['summary']['total_files']}\n")
                f.write(f"- **總代碼行數**: {report['summary']['total_lines']}\n")
                f.write(f"- **總大小**: {report['summary']['total_size_kb']} KB\n")
                f.write(f"- **總函數數**: {report['summary']['total_functions']}\n")
                f.write(f"- **總類數**: {report['summary']['total_classes']}\n")
                f.write(f"- **外部依賴數**: {report['summary']['total_external_dependencies']}\n\n")
                
                f.write("## 主要爬蟲文件\n\n")
                f.write("| 文件名 | 描述 | 行數 | 函數數 | 類數 |\n")
                f.write("|--------|------|------|--------|------|\n")
                
                main_crawlers = {
                    'cb_master.py': '可轉債 Master 爬蟲',
                    'stock_master.py': '股票 Master 爬蟲',
                    'tpex_daily.py': 'TPEX Daily 爬蟲',
                    'tpex_csv_batch_fetcher.py': 'TPEX CSV 批次處理'
                }
                
                for filename, description in main_crawlers.items():
                    for analysis in report['files']:
                        if analysis["file_name"] == filename:
                            f.write(f"| {filename} | {description} | {analysis['lines']} | {len(analysis['functions'])} | {len(analysis['classes'])} |\n")
                
                f.write("\n## 遷移建議\n\n")
                for recommendation in report['recommendations']:
                    f.write(f"- {recommendation}\n")
                
                f.write("\n## 詳細文件分析\n\n")
                for analysis in report['files']:
                    f.write(f"### {analysis['file_name']}\n\n")
                    f.write(f"- **路徑**: {analysis['file_path']}\n")
                    f.write(f"- **大小**: {analysis['size_kb']:.2f} KB\n")
                    f.write(f"- **行數**: {analysis['lines']}\n")
                    f.write(f"- **函數數**: {len(analysis['functions'])}\n")
                    f.write(f"- **類數**: {len(analysis['classes'])}\n")
                    
                    if analysis['imports']:
                        f.write("\n**導入模組**:\n")
                        for imp in sorted(set(analysis['imports']))[:10]:  # 只顯示前10個
                            f.write(f"  - {imp}\n")
                        if len(set(analysis['imports'])) > 10:
                            f.write(f"  - ... 還有 {len(set(analysis['imports'])) - 10} 個\n")
                    
                    f.write("\n")
            
            print(f"\nMarkdown 報告已保存到: {md_file}")
        
    except Exception as e:
        print(f"分析過程中發生錯誤: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
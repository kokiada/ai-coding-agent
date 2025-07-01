"""
レポート生成ツール
JSON、Markdown、HTML形式でのレビュー結果出力
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from langchain.tools import BaseTool
from ..reports.review_result import CReviewResult, CReviewIssue


class ReportGeneratorTool(BaseTool):
    """レビューレポート生成ツール"""
    
    name = "report_generator"
    description = "レビュー結果を様々な形式（JSON/Markdown/HTML）で出力"
    
    def __init__(self, output_dir: str = "./review_reports"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def _run(self, action: str, review_data: str = None, format_type: str = "all", commit_hash: str = None) -> str:
        """レポート生成を実行"""
        try:
            if action == "generate_report":
                if not review_data:
                    return json.dumps({"error": "review_data required"})
                
                # JSON文字列をパース
                if isinstance(review_data, str):
                    data = json.loads(review_data)
                else:
                    data = review_data
                
                result = self._generate_report(data, format_type, commit_hash)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif action == "list_reports":
                reports = self._list_reports()
                return json.dumps(reports, ensure_ascii=False, indent=2)
            
            elif action == "get_report_stats":
                stats = self._get_report_stats()
                return json.dumps(stats, ensure_ascii=False, indent=2)
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
                
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return json.dumps({"error": str(e)})
    
    def _generate_report(self, review_data: Dict, format_type: str, commit_hash: str) -> Dict[str, str]:
        """レビューレポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit_short = commit_hash[:8] if commit_hash else "unknown"
        
        generated_files = {}
        
        if format_type in ["all", "json"]:
            json_file = self._generate_json_report(review_data, timestamp, commit_short)
            generated_files["json"] = json_file
        
        if format_type in ["all", "markdown"]:
            md_file = self._generate_markdown_report(review_data, timestamp, commit_short)
            generated_files["markdown"] = md_file
        
        if format_type in ["all", "html"]:
            html_file = self._generate_html_report(review_data, timestamp, commit_short)
            generated_files["html"] = html_file
        
        if format_type in ["all", "summary"]:
            summary_file = self._generate_summary_report(review_data, timestamp, commit_short)
            generated_files["summary"] = summary_file
        
        return {
            "status": "success",
            "generated_files": generated_files,
            "timestamp": timestamp,
            "commit_hash": commit_hash
        }
    
    def _generate_json_report(self, review_data: Dict, timestamp: str, commit_short: str) -> str:
        """JSON形式のレポートを生成"""
        filename = f"c_review_{commit_short}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # レビューデータを構造化
        structured_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "commit_hash": review_data.get("commit_hash", "unknown"),
                "tool_version": "1.0.0",
                "format_version": "1.0"
            },
            "summary": {
                "total_files": len(review_data.get("reviewed_files", [])),
                "total_issues": len(review_data.get("issues", [])),
                "severity_breakdown": self._calculate_severity_breakdown(review_data.get("issues", [])),
                "category_breakdown": self._calculate_category_breakdown(review_data.get("issues", []))
            },
            "review_data": review_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def _generate_markdown_report(self, review_data: Dict, timestamp: str, commit_short: str) -> str:
        """Markdown形式のレポートを生成"""
        filename = f"c_review_{commit_short}_{timestamp}.md"
        filepath = self.output_dir / filename
        
        issues = review_data.get("issues", [])
        reviewed_files = review_data.get("reviewed_files", [])
        commit_hash = review_data.get("commit_hash", "unknown")
        
        markdown_content = f"""# C言語コードレビュー結果

**コミット**: `{commit_hash}`  
**レビュー実行時刻**: {timestamp}  
**対象ファイル数**: {len(reviewed_files)}  
**検出問題数**: {len(issues)}

## 📊 問題サマリー

| 重要度 | 件数 |
|--------|------|
| 🔴 Critical | {len([i for i in issues if i.get('severity') == 'critical'])} |
| 🟠 High | {len([i for i in issues if i.get('severity') == 'high'])} |
| 🟡 Medium | {len([i for i in issues if i.get('severity') == 'medium'])} |
| 🟢 Low | {len([i for i in issues if i.get('severity') == 'low'])} |

## 📁 レビュー対象ファイル

"""
        
        for file_path in reviewed_files:
            file_issues = [i for i in issues if i.get('file_path') == file_path]
            markdown_content += f"- `{file_path}` ({len(file_issues)}件の問題)\n"
        
        # 重要度別に問題を表示
        for severity in ['critical', 'high', 'medium', 'low']:
            severity_issues = [i for i in issues if i.get('severity') == severity]
            if severity_issues:
                severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
                markdown_content += f"\n## {severity_emoji[severity]} {severity.upper()} Issues\n\n"
                
                for idx, issue in enumerate(severity_issues, 1):
                    markdown_content += f"### {idx}. {issue.get('message', 'Unknown issue')}\n\n"
                    markdown_content += f"**ファイル**: `{issue.get('file_path', 'unknown')}`  \n"
                    
                    if issue.get('line_number'):
                        markdown_content += f"**行番号**: {issue.get('line_number')}  \n"
                    
                    if issue.get('function_name'):
                        markdown_content += f"**関数**: `{issue.get('function_name')}()`  \n"
                    
                    if issue.get('category'):
                        markdown_content += f"**カテゴリ**: {issue.get('category')}  \n"
                    
                    if issue.get('suggestion'):
                        markdown_content += f"\n**改善提案**: {issue.get('suggestion')}\n\n"
                    
                    if issue.get('code_snippet'):
                        markdown_content += f"**問題のあるコード**:\n```c\n{issue.get('code_snippet')}\n```\n\n"
                    
                    if issue.get('fixed_code_example'):
                        markdown_content += f"**修正例**:\n```c\n{issue.get('fixed_code_example')}\n```\n\n"
                    
                    markdown_content += "---\n\n"
        
        # 推奨事項
        if review_data.get('recommendations'):
            markdown_content += "\n## 💡 推奨事項\n\n"
            for rec in review_data['recommendations']:
                markdown_content += f"- {rec}\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(filepath)
    
    def _generate_html_report(self, review_data: Dict, timestamp: str, commit_short: str) -> str:
        """HTML形式のレポートを生成"""
        filename = f"c_review_{commit_short}_{timestamp}.html"
        filepath = self.output_dir / filename
        
        issues = review_data.get("issues", [])
        reviewed_files = review_data.get("reviewed_files", [])
        commit_hash = review_data.get("commit_hash", "unknown")
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>C Code Review Report - {commit_short}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background-color: #f5f5f5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
        }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
        .stat-card {{ 
            background: #fff; 
            border: 1px solid #dee2e6; 
            padding: 15px; 
            border-radius: 8px; 
            flex: 1; 
            min-width: 200px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .issue {{ 
            margin: 20px 0; 
            padding: 15px; 
            border-radius: 8px; 
            background: #fff;
            border-left: 4px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .issue-critical {{ border-left-color: #dc3545; }}
        .issue-high {{ border-left-color: #fd7e14; }}
        .issue-medium {{ border-left-color: #ffc107; }}
        .issue-low {{ border-left-color: #28a745; }}
        .code-block {{ 
            background: #f8f9fa; 
            padding: 10px; 
            border-radius: 4px; 
            font-family: 'Courier New', monospace; 
            overflow-x: auto;
            margin: 10px 0;
        }}
        .file-path {{ color: #6c757d; font-family: monospace; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge-critical {{ background: #dc3545; color: white; }}
        .badge-high {{ background: #fd7e14; color: white; }}
        .badge-medium {{ background: #ffc107; color: black; }}
        .badge-low {{ background: #28a745; color: white; }}
        .nav {{ margin-bottom: 20px; }}
        .nav button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            margin-right: 10px;
            border-radius: 4px;
            cursor: pointer;
        }}
        .nav button:hover {{ background: #0056b3; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 C言語コードレビュー結果</h1>
            <p><strong>コミット:</strong> <code>{commit_hash}</code></p>
            <p><strong>実行時刻:</strong> {timestamp}</p>
            <p><strong>対象ファイル:</strong> {len(reviewed_files)}ファイル</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>総合</h3>
                <h2>{len(issues)}</h2>
                <p>検出問題数</p>
            </div>
            <div class="stat-card">
                <h3>Critical</h3>
                <h2 style="color: #dc3545;">{len([i for i in issues if i.get('severity') == 'critical'])}</h2>
                <p>緊急対応必要</p>
            </div>
            <div class="stat-card">
                <h3>High</h3>
                <h2 style="color: #fd7e14;">{len([i for i in issues if i.get('severity') == 'high'])}</h2>
                <p>高優先度</p>
            </div>
            <div class="stat-card">
                <h3>対象ファイル</h3>
                <h2>{len(reviewed_files)}</h2>
                <p>C言語ファイル</p>
            </div>
        </div>
        
        <div class="nav">
            <button onclick="showAll()">全て表示</button>
            <button onclick="showSeverity('critical')">Critical</button>
            <button onclick="showSeverity('high')">High</button>
            <button onclick="showSeverity('medium')">Medium</button>
            <button onclick="showSeverity('low')">Low</button>
        </div>
        
        <div id="issues-container">
"""
        
        # 問題の詳細をHTML形式で追加
        for idx, issue in enumerate(issues):
            severity = issue.get('severity', 'unknown')
            css_class = f"issue-{severity}"
            
            html_content += f"""
            <div class="issue {css_class}" data-severity="{severity}">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <h3>{issue.get('message', 'Unknown issue')}</h3>
                    <span class="badge badge-{severity}">{severity}</span>
                </div>
                <p class="file-path">{issue.get('file_path', 'unknown')}{':' + str(issue.get('line_number', '')) if issue.get('line_number') else ''}</p>
                {f'<p><strong>関数:</strong> <code>{issue.get("function_name")}()</code></p>' if issue.get('function_name') else ''}
                {f'<p><strong>カテゴリ:</strong> {issue.get("category")}</p>' if issue.get('category') else ''}
                {f'<p><strong>改善提案:</strong> {issue.get("suggestion")}</p>' if issue.get('suggestion') else ''}
                {f'<div class="code-block">{issue.get("code_snippet")}</div>' if issue.get('code_snippet') else ''}
                {f'<h4>修正例:</h4><div class="code-block">{issue.get("fixed_code_example")}</div>' if issue.get('fixed_code_example') else ''}
            </div>
            """
        
        html_content += """
        </div>
    </div>
    
    <script>
        function showAll() {
            const issues = document.querySelectorAll('.issue');
            issues.forEach(issue => issue.style.display = 'block');
        }
        
        function showSeverity(severity) {
            const issues = document.querySelectorAll('.issue');
            issues.forEach(issue => {
                if (issue.dataset.severity === severity) {
                    issue.style.display = 'block';
                } else {
                    issue.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)
    
    def _generate_summary_report(self, review_data: Dict, timestamp: str, commit_short: str) -> str:
        """サマリーレポートを生成"""
        filename = f"c_review_summary_{commit_short}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        issues = review_data.get("issues", [])
        reviewed_files = review_data.get("reviewed_files", [])
        commit_hash = review_data.get("commit_hash", "unknown")
        
        summary = f"""
====================================
C言語コードレビュー結果サマリー
====================================

コミット: {commit_hash}
実行時刻: {timestamp}
対象ファイル: {len(reviewed_files)}ファイル
検出問題数: {len(issues)}件

問題件数（重要度別）:
  🔴 Critical: {len([i for i in issues if i.get('severity') == 'critical'])}件
  🟠 High:     {len([i for i in issues if i.get('severity') == 'high'])}件
  🟡 Medium:   {len([i for i in issues if i.get('severity') == 'medium'])}件
  🟢 Low:      {len([i for i in issues if i.get('severity') == 'low'])}件

対象ファイル一覧:
"""
        
        for file_path in reviewed_files:
            file_issues = [i for i in issues if i.get('file_path') == file_path]
            summary += f"  - {file_path} ({len(file_issues)}件)\n"
        
        # Critical問題があれば詳細表示
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        if critical_issues:
            summary += f"\n緊急対応が必要な問題:\n"
            for issue in critical_issues:
                summary += f"  - {issue.get('file_path', 'unknown')}:{issue.get('line_number', '?')} - {issue.get('message', 'Unknown')}\n"
        else:
            summary += f"\n緊急対応が必要な問題: なし\n"
        
        summary += f"\n詳細レポート:\n"
        summary += f"  - JSON: {self.output_dir}/c_review_{commit_short}_{timestamp}.json\n"
        summary += f"  - Markdown: {self.output_dir}/c_review_{commit_short}_{timestamp}.md\n"
        summary += f"  - HTML: {self.output_dir}/c_review_{commit_short}_{timestamp}.html\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return str(filepath)
    
    def _calculate_severity_breakdown(self, issues: List[Dict]) -> Dict[str, int]:
        """重要度別の問題数を計算"""
        breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for issue in issues:
            severity = issue.get('severity', 'low')
            if severity in breakdown:
                breakdown[severity] += 1
        
        return breakdown
    
    def _calculate_category_breakdown(self, issues: List[Dict]) -> Dict[str, int]:
        """カテゴリ別の問題数を計算"""
        breakdown = {}
        
        for issue in issues:
            category = issue.get('category', 'other')
            breakdown[category] = breakdown.get(category, 0) + 1
        
        return breakdown
    
    def _list_reports(self) -> List[Dict]:
        """生成されたレポートの一覧を取得"""
        reports = []
        
        for report_file in self.output_dir.glob("c_review_*.json"):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                reports.append({
                    "filename": report_file.name,
                    "path": str(report_file),
                    "created": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
                    "size": report_file.stat().st_size,
                    "commit_hash": data.get("review_data", {}).get("commit_hash", "unknown")
                })
            except Exception as e:
                self.logger.warning(f"Failed to read report {report_file}: {e}")
        
        return sorted(reports, key=lambda x: x["created"], reverse=True)
    
    def _get_report_stats(self) -> Dict:
        """レポートの統計情報を取得"""
        reports = self._list_reports()
        
        return {
            "total_reports": len(reports),
            "latest_report": reports[0] if reports else None,
            "total_size_mb": sum(r["size"] for r in reports) / (1024 * 1024),
            "output_directory": str(self.output_dir)
        }
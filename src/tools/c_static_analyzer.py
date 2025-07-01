"""
C言語静的解析ツール
cppcheck、clang-tidy等を使用した静的解析
"""

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import logging

from langchain.tools import BaseTool


class CStaticAnalysisTool(BaseTool):
    """C言語静的解析を実行するツール"""
    
    name = "c_static_analyzer"
    description = "cppcheck、clang-tidy等を使用したC言語静的解析"
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def _run(self, file_path: str) -> str:
        """静的解析を実行"""
        try:
            if not Path(file_path).exists():
                return json.dumps({"error": f"File not found: {file_path}"})
            
            results = {
                "file_path": file_path,
                "cppcheck_results": self._run_cppcheck(file_path),
                "custom_analysis": self._run_custom_analysis(file_path),
                "summary": {}
            }
            
            # サマリーを生成
            results["summary"] = self._generate_summary(results)
            
            return json.dumps(results, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Static analysis failed for {file_path}: {e}")
            return json.dumps({"error": str(e)})
    
    def _run_cppcheck(self, file_path: str) -> List[Dict]:
        """cppcheckによる静的解析"""
        try:
            # cppcheckコマンドを実行
            cmd = [
                'cppcheck',
                '--enable=all',
                '--xml',
                '--xml-version=2',
                file_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            # XML結果を解析
            issues = []
            if result.stderr:
                issues = self._parse_cppcheck_xml(result.stderr)
            
            return issues
            
        except subprocess.TimeoutExpired:
            return [{"error": "cppcheck timeout"}]
        except FileNotFoundError:
            return [{"error": "cppcheck not found - please install cppcheck"}]
        except Exception as e:
            return [{"error": f"cppcheck execution failed: {str(e)}"}]
    
    def _parse_cppcheck_xml(self, xml_output: str) -> List[Dict]:
        """cppcheckのXML出力を解析"""
        issues = []
        
        try:
            # XML要素として解析
            root = ET.fromstring(xml_output)
            
            for error in root.findall('.//error'):
                issue = {
                    "tool": "cppcheck",
                    "id": error.get('id', ''),
                    "severity": error.get('severity', 'unknown'),
                    "message": error.get('msg', ''),
                    "verbose": error.get('verbose', ''),
                    "locations": []
                }
                
                # 位置情報を取得
                for location in error.findall('location'):
                    issue["locations"].append({
                        "file": location.get('file', ''),
                        "line": int(location.get('line', 0)),
                        "column": int(location.get('column', 0))
                    })
                
                issues.append(issue)
                
        except ET.ParseError as e:
            # XMLパースに失敗した場合、テキストから情報を抽出
            self.logger.warning(f"Failed to parse cppcheck XML: {e}")
            issues = self._parse_cppcheck_text(xml_output)
        
        return issues
    
    def _parse_cppcheck_text(self, text_output: str) -> List[Dict]:
        """cppcheckのテキスト出力を解析（XMLパースが失敗した場合）"""
        issues = []
        
        lines = text_output.split('\n')
        for line in lines:
            if 'error' in line.lower() or 'warning' in line.lower():
                issues.append({
                    "tool": "cppcheck",
                    "severity": "unknown",
                    "message": line.strip(),
                    "raw_output": True
                })
        
        return issues
    
    def _run_custom_analysis(self, file_path: str) -> List[Dict]:
        """カスタム静的解析"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # C言語特有のパターンをチェック
            issues.extend(self._check_security_patterns(content, file_path))
            issues.extend(self._check_memory_patterns(content, file_path))
            issues.extend(self._check_performance_patterns(content, file_path))
            issues.extend(self._check_style_patterns(content, file_path))
            
        except Exception as e:
            issues.append({
                "tool": "custom",
                "severity": "error",
                "message": f"Custom analysis failed: {str(e)}"
            })
        
        return issues
    
    def _check_security_patterns(self, content: str, file_path: str) -> List[Dict]:
        """セキュリティパターンをチェック"""
        issues = []
        lines = content.split('\n')
        
        # 危険な関数の使用チェック
        dangerous_functions = {
            'strcpy': {
                'severity': 'high',
                'message': 'strcpy()の使用はバッファオーバーフローの原因となります',
                'suggestion': 'strncpy()またはstrlcpy()を使用してください'
            },
            'strcat': {
                'severity': 'high', 
                'message': 'strcat()の使用はバッファオーバーフローの原因となります',
                'suggestion': 'strncat()またはstrlcat()を使用してください'
            },
            'sprintf': {
                'severity': 'high',
                'message': 'sprintf()の使用はバッファオーバーフローの原因となります',
                'suggestion': 'snprintf()を使用してください'
            },
            'gets': {
                'severity': 'critical',
                'message': 'gets()は非常に危険な関数です',
                'suggestion': 'fgets()を使用してください'
            }
        }
        
        for i, line in enumerate(lines):
            for func, info in dangerous_functions.items():
                if func + '(' in line:
                    issues.append({
                        "tool": "custom",
                        "category": "security",
                        "severity": info['severity'],
                        "line": i + 1,
                        "message": info['message'],
                        "suggestion": info['suggestion'],
                        "code_snippet": line.strip()
                    })
        
        return issues
    
    def _check_memory_patterns(self, content: str, file_path: str) -> List[Dict]:
        """メモリ管理パターンをチェック"""
        issues = []
        lines = content.split('\n')
        
        # malloc/freeのペアをチェック
        malloc_lines = []
        free_lines = []
        
        for i, line in enumerate(lines):
            if 'malloc(' in line or 'calloc(' in line:
                malloc_lines.append(i + 1)
            if 'free(' in line:
                free_lines.append(i + 1)
        
        # malloc/freeの数が合わない場合
        if len(malloc_lines) > len(free_lines):
            issues.append({
                "tool": "custom",
                "category": "memory",
                "severity": "medium",
                "message": f"malloc/calloc({len(malloc_lines)})とfree({len(free_lines)})の数が不一致",
                "suggestion": "メモリリークの可能性があります。全てのmallocに対応するfreeを確認してください"
            })
        
        # NULLポインタチェックの不足
        for i, line in enumerate(lines):
            if ('malloc(' in line or 'calloc(' in line) and '=' in line:
                # 次の数行でNULLチェックがあるかを確認
                null_check_found = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if 'NULL' in lines[j] or 'null' in lines[j]:
                        null_check_found = True
                        break
                
                if not null_check_found:
                    issues.append({
                        "tool": "custom",
                        "category": "memory",
                        "severity": "medium",
                        "line": i + 1,
                        "message": "malloc/calloc後のNULLチェックがありません",
                        "suggestion": "メモリ割り当て失敗時の処理を追加してください",
                        "code_snippet": line.strip()
                    })
        
        return issues
    
    def _check_performance_patterns(self, content: str, file_path: str) -> List[Dict]:
        """パフォーマンスパターンをチェック"""
        issues = []
        lines = content.split('\n')
        
        # ループ内でのmalloc
        in_loop = False
        loop_depth = 0
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # ループの検出
            if any(keyword in line_clean for keyword in ['for(', 'while(', 'do{']):
                in_loop = True
                loop_depth += 1
            elif '}' in line_clean and in_loop:
                loop_depth -= 1
                if loop_depth == 0:
                    in_loop = False
            
            # ループ内でのメモリ割り当て
            if in_loop and ('malloc(' in line or 'calloc(' in line):
                issues.append({
                    "tool": "custom",
                    "category": "performance",
                    "severity": "medium",
                    "line": i + 1,
                    "message": "ループ内でメモリ割り当てを実行しています",
                    "suggestion": "可能であればループ外でメモリを事前割り当てしてください",
                    "code_snippet": line.strip()
                })
        
        return issues
    
    def _check_style_patterns(self, content: str, file_path: str) -> List[Dict]:
        """コードスタイルパターンをチェック"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # 長すぎる行
            if len(line) > 120:
                issues.append({
                    "tool": "custom",
                    "category": "style",
                    "severity": "low",
                    "line": i + 1,
                    "message": "行が長すぎます（120文字超）",
                    "suggestion": "行を分割して可読性を向上させてください"
                })
            
            # ハードコードされた数値
            if any(char.isdigit() for char in line) and not line.strip().startswith('//'):
                # マジックナンバーの検出（簡易版）
                import re
                numbers = re.findall(r'\b\d+\b', line)
                if any(int(num) > 10 for num in numbers if num.isdigit()):
                    issues.append({
                        "tool": "custom", 
                        "category": "style",
                        "severity": "low",
                        "line": i + 1,
                        "message": "マジックナンバーの可能性があります",
                        "suggestion": "定数または#defineを使用してください",
                        "code_snippet": line.strip()
                    })
        
        return issues
    
    def _generate_summary(self, results: Dict) -> Dict:
        """解析結果のサマリーを生成"""
        summary = {
            "total_issues": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_category": {},
            "tools_used": []
        }
        
        # cppcheck結果を集計
        if results.get("cppcheck_results"):
            summary["tools_used"].append("cppcheck")
            for issue in results["cppcheck_results"]:
                if "error" not in issue:
                    summary["total_issues"] += 1
                    severity = issue.get("severity", "unknown")
                    if severity in summary["by_severity"]:
                        summary["by_severity"][severity] += 1
        
        # カスタム解析結果を集計
        if results.get("custom_analysis"):
            summary["tools_used"].append("custom")
            for issue in results["custom_analysis"]:
                if "error" not in issue:
                    summary["total_issues"] += 1
                    severity = issue.get("severity", "unknown")
                    category = issue.get("category", "other")
                    
                    if severity in summary["by_severity"]:
                        summary["by_severity"][severity] += 1
                    
                    if category not in summary["by_category"]:
                        summary["by_category"][category] = 0
                    summary["by_category"][category] += 1
        
        return summary
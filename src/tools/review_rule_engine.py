"""
レビュールールエンジン
設定されたコーディング規約に基づいてコードを評価
"""

import json
import logging
from typing import Dict, List, Any, Optional

from langchain.tools import BaseTool
from ..config.config_manager import ConfigManager


class ReviewRuleEngineTool(BaseTool):
    """レビュールールエンジンツール"""
    
    name = "review_rule_engine"
    description = "設定されたルールに基づいてコードを評価"
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def _run(self, action: str, file_path: str = None, code_content: str = None, rules_category: str = None) -> str:
        """ルールエンジンを実行"""
        try:
            if action == "evaluate_file":
                if not file_path or not code_content:
                    return json.dumps({"error": "file_path and code_content required"})
                
                result = self._evaluate_file(file_path, code_content, rules_category)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif action == "get_applicable_rules":
                if not file_path:
                    return json.dumps({"error": "file_path required"})
                
                rules = self._get_applicable_rules(file_path)
                return json.dumps(rules, ensure_ascii=False, indent=2)
            
            elif action == "list_all_rules":
                rules = self._list_all_rules()
                return json.dumps(rules, ensure_ascii=False, indent=2)
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
                
        except Exception as e:
            self.logger.error(f"Rule engine operation failed: {e}")
            return json.dumps({"error": str(e)})
    
    def _evaluate_file(self, file_path: str, code_content: str, rules_category: str = None) -> Dict:
        """ファイルに対してルールを評価"""
        # 適用可能なルールを取得
        applicable_rules = self._get_applicable_rules(file_path)
        
        if rules_category:
            # 特定のカテゴリのルールのみを適用
            applicable_rules = {
                rules_category: applicable_rules.get(rules_category, [])
            }
        
        evaluation_result = {
            "file_path": file_path,
            "applied_rules": [],
            "violations": [],
            "summary": {
                "total_rules": 0,
                "violations_found": 0,
                "compliance_score": 0.0
            }
        }
        
        total_rules = 0
        violations = 0
        
        # カテゴリ別にルールを評価
        for category, rules in applicable_rules.items():
            for rule in rules:
                total_rules += 1
                evaluation_result["applied_rules"].append({
                    "category": category,
                    "description": rule["description"],
                    "priority": rule["priority"]
                })
                
                # ルールを評価
                violation = self._evaluate_rule(rule, code_content, file_path)
                if violation:
                    violations += 1
                    violation["category"] = category
                    evaluation_result["violations"].append(violation)
        
        # サマリーを計算
        evaluation_result["summary"]["total_rules"] = total_rules
        evaluation_result["summary"]["violations_found"] = violations
        evaluation_result["summary"]["compliance_score"] = (
            (total_rules - violations) / total_rules * 100 if total_rules > 0 else 100.0
        )
        
        return evaluation_result
    
    def _get_applicable_rules(self, file_path: str) -> Dict[str, List[Dict]]:
        """ファイルに適用可能なルールを取得"""
        # 設定からレビュー観点を取得
        standards = self.config_manager.get_review_standards()
        
        if not standards:
            return {}
        
        # ファイルタイプに基づいてルールをフィルタリング
        applicable_rules = {}
        
        for category, rules in standards.items():
            applicable_category_rules = []
            
            for rule in rules:
                # ファイルパターンマッチング
                applicable_files = rule.get("applicable_files", ["*"])
                
                if self._file_matches_patterns(file_path, applicable_files):
                    applicable_category_rules.append(rule)
            
            if applicable_category_rules:
                applicable_rules[category] = applicable_category_rules
        
        return applicable_rules
    
    def _file_matches_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """ファイルがパターンにマッチするかチェック"""
        import fnmatch
        
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False
    
    def _evaluate_rule(self, rule: Dict, code_content: str, file_path: str) -> Optional[Dict]:
        """個別ルールを評価"""
        description = rule["description"]
        category = rule.get("category", "custom")
        
        # ルールの説明文から評価ロジックを決定
        violation = None
        
        if "バッファオーバーフロー" in description or "buffer overflow" in description.lower():
            violation = self._check_buffer_overflow(code_content, description)
        
        elif "メモリリーク" in description or "memory leak" in description.lower():
            violation = self._check_memory_leak(code_content, description)
        
        elif "null" in description.lower() or "ヌル" in description:
            violation = self._check_null_pointer(code_content, description)
        
        elif "危険な関数" in description or "dangerous function" in description.lower():
            violation = self._check_dangerous_functions(code_content, description)
        
        elif "エラーハンドリング" in description or "error handling" in description.lower():
            violation = self._check_error_handling(code_content, description)
        
        elif "パフォーマンス" in description or "performance" in description.lower():
            violation = self._check_performance(code_content, description)
        
        elif "コメント" in description or "comment" in description.lower():
            violation = self._check_comments(code_content, description)
        
        else:
            # 汎用的なキーワードマッチング
            violation = self._check_generic_rule(rule, code_content, description)
        
        return violation
    
    def _check_buffer_overflow(self, code: str, description: str) -> Optional[Dict]:
        """バッファオーバーフロー脆弱性をチェック"""
        dangerous_functions = ['strcpy', 'strcat', 'sprintf', 'gets']
        
        for func in dangerous_functions:
            if func + '(' in code:
                return {
                    "rule_description": description,
                    "violation_type": "buffer_overflow",
                    "severity": "high",
                    "message": f"危険な関数 {func} の使用を検出しました",
                    "suggestion": f"{func} の代わりに安全な関数を使用してください",
                    "detected_pattern": func
                }
        return None
    
    def _check_memory_leak(self, code: str, description: str) -> Optional[Dict]:
        """メモリリークをチェック"""
        malloc_count = code.count('malloc') + code.count('calloc')
        free_count = code.count('free')
        
        if malloc_count > free_count:
            return {
                "rule_description": description,
                "violation_type": "memory_leak",
                "severity": "medium",
                "message": f"malloc/calloc({malloc_count})とfree({free_count})の数が不一致",
                "suggestion": "全てのmalloc/callocに対応するfreeを確認してください",
                "detected_pattern": f"malloc:{malloc_count}, free:{free_count}"
            }
        return None
    
    def _check_null_pointer(self, code: str, description: str) -> Optional[Dict]:
        """NULLポインタチェック"""
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            if ('malloc(' in line or 'calloc(' in line) and '=' in line:
                # 次の数行でNULLチェックがあるか確認
                null_check_found = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if 'NULL' in lines[j] or 'null' in lines[j]:
                        null_check_found = True
                        break
                
                if not null_check_found:
                    return {
                        "rule_description": description,
                        "violation_type": "null_pointer",
                        "severity": "medium",
                        "message": "malloc/calloc後のNULLチェックがありません",
                        "suggestion": "メモリ割り当て失敗時の処理を追加してください",
                        "line_number": i + 1,
                        "detected_pattern": line.strip()
                    }
        return None
    
    def _check_dangerous_functions(self, code: str, description: str) -> Optional[Dict]:
        """危険な関数の使用をチェック"""
        dangerous_funcs = {
            'strcpy': 'strncpy',
            'strcat': 'strncat', 
            'sprintf': 'snprintf',
            'gets': 'fgets'
        }
        
        for dangerous, safe in dangerous_funcs.items():
            if dangerous + '(' in code:
                return {
                    "rule_description": description,
                    "violation_type": "dangerous_function",
                    "severity": "high",
                    "message": f"危険な関数 {dangerous} の使用を検出",
                    "suggestion": f"{safe} を使用してください",
                    "detected_pattern": dangerous
                }
        return None
    
    def _check_error_handling(self, code: str, description: str) -> Optional[Dict]:
        """エラーハンドリングをチェック"""
        if 'return' not in code and 'void' not in code:
            return {
                "rule_description": description,
                "violation_type": "error_handling",
                "severity": "medium",
                "message": "適切なエラーハンドリングが不足している可能性",
                "suggestion": "戻り値やエラーコードでエラー状態を通知してください",
                "detected_pattern": "missing_return_value"
            }
        return None
    
    def _check_performance(self, code: str, description: str) -> Optional[Dict]:
        """パフォーマンス問題をチェック"""
        # ループ内でのmalloc検出
        lines = code.split('\n')
        in_loop = False
        
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ['for(', 'while(', 'do{']):
                in_loop = True
            elif '}' in line:
                in_loop = False
            
            if in_loop and ('malloc(' in line or 'calloc(' in line):
                return {
                    "rule_description": description,
                    "violation_type": "performance",
                    "severity": "medium",
                    "message": "ループ内でメモリ割り当てを実行",
                    "suggestion": "可能であればループ外でメモリを事前割り当てしてください",
                    "line_number": i + 1,
                    "detected_pattern": line.strip()
                }
        return None
    
    def _check_comments(self, code: str, description: str) -> Optional[Dict]:
        """コメントの有無をチェック"""
        comment_count = code.count('//') + code.count('/*')
        line_count = len(code.split('\n'))
        
        if line_count > 20 and comment_count == 0:
            return {
                "rule_description": description,
                "violation_type": "documentation",
                "severity": "low",
                "message": "コメントが不足しています",
                "suggestion": "重要な処理にはコメントを追加してください",
                "detected_pattern": f"lines:{line_count}, comments:{comment_count}"
            }
        return None
    
    def _check_generic_rule(self, rule: Dict, code: str, description: str) -> Optional[Dict]:
        """汎用的なルールチェック"""
        # 簡易的なキーワードベースのチェック
        keywords = description.split()
        
        for keyword in keywords:
            if len(keyword) > 3 and keyword.lower() in code.lower():
                return {
                    "rule_description": description,
                    "violation_type": "generic",
                    "severity": rule.get("priority", "low"),
                    "message": f"ルール '{description}' に関連する可能性のあるパターンを検出",
                    "suggestion": "詳細な確認を行ってください",
                    "detected_pattern": keyword
                }
        return None
    
    def _list_all_rules(self) -> Dict:
        """全てのルールを一覧表示"""
        standards = self.config_manager.get_review_standards()
        
        if not standards:
            return {"message": "No rules configured"}
        
        rule_summary = {
            "total_categories": len(standards),
            "categories": {}
        }
        
        for category, rules in standards.items():
            rule_summary["categories"][category] = {
                "count": len(rules),
                "rules": [
                    {
                        "description": rule["description"],
                        "priority": rule.get("priority", "medium"),
                        "applicable_files": rule.get("applicable_files", ["*"])
                    }
                    for rule in rules
                ]
            }
        
        return rule_summary
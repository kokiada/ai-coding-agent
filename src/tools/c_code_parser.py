"""
C言語コード解析ツール
関数、構造体、マクロ等の抽出と複雑度計算
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain.tools import BaseTool


class CCodeParserTool(BaseTool):
    """C言語ファイルを解析して構造を抽出するツール"""
    
    name = "c_code_parser"
    description = "C言語ファイルを解析して関数、構造体、マクロ等を抽出し、複雑度を計算"
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def _run(self, file_path: str) -> str:
        """C言語ファイルを解析"""
        try:
            if not Path(file_path).exists():
                return json.dumps({"error": f"File not found: {file_path}"})
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file_path": file_path,
                "functions": self._extract_functions(content),
                "structs": self._extract_structs(content),
                "macros": self._extract_macros(content),
                "includes": self._extract_includes(content),
                "global_variables": self._extract_global_vars(content),
                "complexity_metrics": self._calculate_file_complexity(content),
                "potential_issues": self._detect_c_issues(content),
                "line_count": len(content.split('\n')),
                "function_count": content.count('(')  # 簡易カウント
            }
            
            return json.dumps(analysis, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to parse C code {file_path}: {e}")
            return json.dumps({"error": str(e)})
    
    def _extract_functions(self, content: str) -> List[Dict]:
        """関数定義を抽出"""
        functions = []
        
        # 関数定義のパターン（戻り値型 関数名(引数) { の形式）
        func_pattern = r'((?:static\s+|inline\s+|extern\s+)*\w+(?:\s*\*\s*)*)\s+(\w+)\s*\([^)]*\)\s*{'
        
        matches = re.finditer(func_pattern, content, re.MULTILINE)
        
        for match in matches:
            func_start = match.start()
            return_type = match.group(1).strip()
            func_name = match.group(2)
            
            # 関数の終了位置を見つける
            func_end = self._find_function_end(content, func_start)
            func_body = content[func_start:func_end]
            
            # 関数の詳細解析
            functions.append({
                "name": func_name,
                "return_type": return_type,
                "start_line": content[:func_start].count('\n') + 1,
                "end_line": content[:func_end].count('\n') + 1,
                "line_count": func_body.count('\n'),
                "parameters": self._extract_parameters(match.group(0)),
                "complexity": self._calculate_function_complexity(func_body),
                "has_return": "return" in func_body,
                "malloc_count": func_body.count('malloc'),
                "free_count": func_body.count('free'),
                "potential_issues": self._analyze_function_issues(func_body)
            })
        
        return functions
    
    def _extract_structs(self, content: str) -> List[Dict]:
        """構造体定義を抽出"""
        structs = []
        
        # typedef struct パターン
        typedef_pattern = r'typedef\s+struct\s*(\w+)?\s*{([^}]*)}\s*(\w+);?'
        
        for match in re.finditer(typedef_pattern, content, re.DOTALL):
            struct_tag = match.group(1)
            struct_body = match.group(2)
            typedef_name = match.group(3)
            
            structs.append({
                "name": typedef_name,
                "tag": struct_tag,
                "members": self._parse_struct_members(struct_body),
                "line_number": content[:match.start()].count('\n') + 1,
                "size_estimate": len(struct_body.split(';')) - 1  # セミコロンの数から推定
            })
        
        # 通常の struct パターン
        struct_pattern = r'struct\s+(\w+)\s*{([^}]*)};'
        
        for match in re.finditer(struct_pattern, content, re.DOTALL):
            struct_name = match.group(1)
            struct_body = match.group(2)
            
            structs.append({
                "name": struct_name,
                "tag": struct_name,
                "members": self._parse_struct_members(struct_body),
                "line_number": content[:match.start()].count('\n') + 1,
                "size_estimate": len(struct_body.split(';')) - 1
            })
        
        return structs
    
    def _extract_macros(self, content: str) -> List[Dict]:
        """マクロ定義を抽出"""
        macros = []
        
        # #define パターン
        macro_pattern = r'#define\s+(\w+)(?:\([^)]*\))?\s+(.*)$'
        
        for match in re.finditer(macro_pattern, content, re.MULTILINE):
            macro_name = match.group(1)
            macro_value = match.group(2).strip()
            
            macros.append({
                "name": macro_name,
                "value": macro_value,
                "line_number": content[:match.start()].count('\n') + 1,
                "is_function_like": '(' in match.group(0),
                "complexity": "high" if len(macro_value) > 50 else "low"
            })
        
        return macros
    
    def _extract_includes(self, content: str) -> List[Dict]:
        """インクルード文を抽出"""
        includes = []
        
        include_pattern = r'#include\s*[<"](.*?)[>"]'
        
        for match in re.finditer(include_pattern, content):
            header_file = match.group(1)
            
            includes.append({
                "file": header_file,
                "line_number": content[:match.start()].count('\n') + 1,
                "is_system": match.group(0).count('<') > 0,
                "is_local": match.group(0).count('"') > 0
            })
        
        return includes
    
    def _extract_global_vars(self, content: str) -> List[Dict]:
        """グローバル変数を抽出（簡易版）"""
        global_vars = []
        
        # 関数外での変数宣言を検出（簡易的）
        var_pattern = r'^((?:static\s+|extern\s+|const\s+)*\w+(?:\s*\*\s*)*)\s+(\w+)(?:\s*=\s*[^;]+)?;'
        
        lines = content.split('\n')
        in_function = False
        brace_count = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 関数内かどうかの判定
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0 and not in_function:
                match = re.match(var_pattern, line)
                if match and not line.startswith('#'):
                    var_type = match.group(1).strip()
                    var_name = match.group(2)
                    
                    global_vars.append({
                        "name": var_name,
                        "type": var_type,
                        "line_number": i + 1,
                        "is_static": "static" in var_type,
                        "is_const": "const" in var_type,
                        "is_pointer": "*" in var_type
                    })
        
        return global_vars
    
    def _find_function_end(self, content: str, start_pos: int) -> int:
        """関数の終了位置を見つける"""
        brace_count = 0
        pos = start_pos
        found_start = False
        
        while pos < len(content):
            char = content[pos]
            if char == '{':
                brace_count += 1
                found_start = True
            elif char == '}':
                brace_count -= 1
                if found_start and brace_count == 0:
                    return pos + 1
            pos += 1
        
        return len(content)
    
    def _extract_parameters(self, func_declaration: str) -> List[str]:
        """関数のパラメータを抽出"""
        # 括弧内のパラメータを抽出
        param_match = re.search(r'\(([^)]*)\)', func_declaration)
        if not param_match:
            return []
        
        params_str = param_match.group(1).strip()
        if not params_str or params_str == 'void':
            return []
        
        # カンマで分割してクリーンアップ
        params = [param.strip() for param in params_str.split(',')]
        return params
    
    def _parse_struct_members(self, struct_body: str) -> List[Dict]:
        """構造体メンバーを解析"""
        members = []
        
        # セミコロンで区切られた各メンバーを解析
        member_lines = [line.strip() for line in struct_body.split(';') if line.strip()]
        
        for line in member_lines:
            # 基本的な型と変数名のパターン
            member_match = re.match(r'(\w+(?:\s*\*\s*)*)\s+(\w+)(?:\[.*?\])?', line)
            if member_match:
                member_type = member_match.group(1).strip()
                member_name = member_match.group(2)
                
                members.append({
                    "name": member_name,
                    "type": member_type,
                    "is_pointer": "*" in member_type,
                    "is_array": "[" in line and "]" in line
                })
        
        return members
    
    def _calculate_function_complexity(self, func_body: str) -> Dict[str, Any]:
        """関数の複雑度を計算"""
        # サイクロマティック複雑度の計算
        decision_points = 0
        decision_points += func_body.count('if')
        decision_points += func_body.count('while')
        decision_points += func_body.count('for')
        decision_points += func_body.count('switch')
        decision_points += func_body.count('case')
        decision_points += func_body.count('&&')
        decision_points += func_body.count('||')
        
        cyclomatic = decision_points + 1
        
        # その他の複雑度指標
        line_count = func_body.count('\n')
        nested_level = self._calculate_nesting_level(func_body)
        
        return {
            "cyclomatic_complexity": cyclomatic,
            "line_count": line_count,
            "nesting_level": nested_level,
            "complexity_rating": self._rate_complexity(cyclomatic, line_count, nested_level)
        }
    
    def _calculate_file_complexity(self, content: str) -> Dict[str, Any]:
        """ファイル全体の複雑度を計算"""
        functions = self._extract_functions(content)
        
        if not functions:
            return {"average_complexity": 0, "max_complexity": 0, "total_functions": 0}
        
        complexities = [func.get("complexity", {}).get("cyclomatic_complexity", 0) for func in functions]
        
        return {
            "total_functions": len(functions),
            "average_complexity": sum(complexities) / len(complexities) if complexities else 0,
            "max_complexity": max(complexities) if complexities else 0,
            "complex_functions": len([c for c in complexities if c > 10])
        }
    
    def _calculate_nesting_level(self, code: str) -> int:
        """ネストレベルを計算"""
        max_level = 0
        current_level = 0
        
        for char in code:
            if char == '{':
                current_level += 1
                max_level = max(max_level, current_level)
            elif char == '}':
                current_level -= 1
        
        return max_level
    
    def _rate_complexity(self, cyclomatic: int, line_count: int, nesting: int) -> str:
        """複雑度を評価"""
        if cyclomatic > 20 or line_count > 100 or nesting > 5:
            return "very_high"
        elif cyclomatic > 10 or line_count > 50 or nesting > 3:
            return "high"
        elif cyclomatic > 5 or line_count > 25 or nesting > 2:
            return "medium"
        else:
            return "low"
    
    def _detect_c_issues(self, content: str) -> List[Dict]:
        """C言語特有の問題を検出"""
        issues = []
        
        # 危険な関数の使用
        dangerous_funcs = {
            'strcpy': 'strncpy等の安全な関数を使用してください',
            'strcat': 'strncat等の安全な関数を使用してください', 
            'sprintf': 'snprintf等の安全な関数を使用してください',
            'gets': 'fgets等の安全な関数を使用してください',
            'scanf': 'より安全な入力方法を検討してください'
        }
        
        for func, suggestion in dangerous_funcs.items():
            if func in content:
                issues.append({
                    "type": "security",
                    "severity": "high",
                    "function": func,
                    "description": f"危険な関数 {func} の使用を検出",
                    "suggestion": suggestion
                })
        
        # メモリリークの可能性
        malloc_count = content.count('malloc') + content.count('calloc')
        free_count = content.count('free')
        if malloc_count > free_count:
            issues.append({
                "type": "memory_leak",
                "severity": "medium", 
                "description": f"malloc/calloc({malloc_count})とfree({free_count})の数が不一致",
                "suggestion": "全てのmalloc/callocに対応するfreeを確認してください"
            })
        
        # NULLポインタチェックの不足
        if 'malloc' in content and content.count('if') < content.count('malloc'):
            issues.append({
                "type": "null_pointer",
                "severity": "medium",
                "description": "malloc後のNULLチェックが不足している可能性",
                "suggestion": "malloc返り値のNULLチェックを追加してください"
            })
        
        return issues
    
    def _analyze_function_issues(self, func_body: str) -> List[str]:
        """関数固有の問題を分析"""
        issues = []
        
        if func_body.count('\n') > 50:
            issues.append("関数が長すぎます（50行超）")
        
        if self._calculate_function_complexity(func_body)["cyclomatic_complexity"] > 10:
            issues.append("複雑度が高すぎます（サイクロマティック複雑度 > 10）")
        
        if 'return' not in func_body and 'void' not in func_body:
            issues.append("戻り値が設定されていない可能性")
        
        return issues
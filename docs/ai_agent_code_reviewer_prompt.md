## ローカル完結型のGit統合

### Git操作（ローカルのみ）
```python
class LocalGitAnalyzer:
    """ローカルGitリポジトリの解析（外部通信なし）"""
    
    def __init__(self, repo_path: str = "."):
        self.repo = Repo(repo_path)
    
    def get_commit_changes(self, commit_hash: str) -> Dict:
        """指定コミットの変更内容を取得"""
        commit = self.repo.commit(commit_hash)
        
        changes = {
            "commit_info": {
                "hash": commit_hash,
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip()
            },
            "c_files": {
                "modified": [],
                "added": [],
                "deleted": []
            },
            "file_changes": {}
        }
        
        # 変更されたファイルの分析（C言語ファイルのみ）
        for item in commit.diff(commit.parents[0] if commit.parents else None):
            file_path = item.a_path or item.b_path
            
            # C言語ファイルのみを対象
            if not (file_path.endswith('.c') or file_path.endswith('.h')):
                continue
                
            if item.change_type == 'M':
                changes["c_files"]["modified"].append(file_path)
            elif item.change_type == 'A':
                changes["c_files"]["added"].append(file_path)
            elif item.change_type == 'D':
                changes["c_files"]["deleted"].append(file_path)
                
            changes["file_changes"][file_path] = {
                "change_type": item.change_type,
                "diff": item.diff.decode('utf-8') if item.diff else "",
                "added_lines": self._count_added_lines(item),
                "removed_lines": self._count_removed_lines(item)
            }
        
        return changes
    
    def get_file_content(self, file_path: str, commit_hash: str = None) -> str:
        """指定ファイルの内容を取得"""
        if commit_hash:
            commit = self.repo.commit(commit_hash)
            return commit.tree[file_path].data_stream.read().decode('utf-8')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

class LocalGitTool(BaseTool):
    name = "local_git_analyzer"
    description = "ローカルGitリポジトリの解析（外部通信なし）"
    
    def _run(self, action: str, commit_hash: str = None, file_path: str = None) -> str:
        analyzer = LocalGitAnalyzer()
        
        if action == "get_commit_changes":
            changes = analyzer.get_commit_changes(commit_hash)
            return json.dumps(changes, ensure_ascii=False, indent=2)
        
        elif action == "get_file_content":
            content = analyzer.get_file_content(file_path, commit_hash)
            return content
        
        else:
            return f"Unknown action: {action}"
```

### ローカルレポート生成システム
```python
class LocalReportGenerator:
    """ローカルファイルシステムでのレポート生成"""
    
    def __init__(self, output_dir: str = "./review_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_comprehensive_report(self, review_result: CReviewResult) -> Dict[str, str]:
        """包括的なローカルレポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit_short = review_result.commit_hash[:8]
        
        # 複数形式でレポート生成
        reports = {
            "json": self._generate_json_report(review_result, timestamp, commit_short),
            "markdown": self._generate_markdown_report(review_result, timestamp, commit_short),
            "html": self._generate_html_report(review_result, timestamp, commit_short),
            "summary": self._generate_summary_report(review_result, timestamp, commit_short)
        }
        
        return reports
    
    def _generate_json_report(self, review_result: CReviewResult, timestamp: str, commit_short: str) -> str:
        """詳細なJSONレポート"""
        filename = f"c_review_{commit_short}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(review_result.dict(), f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def _generate_markdown_report(self, review_result: CReviewResult, timestamp: str, commit_short: str) -> str:
        """開発者向けMarkdownレポート"""
        filename = f"c_review_{commit_short}_{timestamp}.md"
        filepath = self.output_dir / filename
        
        markdown_content = f"""# C言語コードレビュー結果

**コミット**: `{review_result.commit_hash}`  
**レビュー実行時刻**: {timestamp}  
**対象ファイル数**: {len(review_result.reviewed_files)}  
**総レビュー行数**: {review_result.total_lines_reviewed}

## 📊 品質メトリクス

| 項目 | スコア |
|------|--------|
| 総合品質 | {review_result.overall_quality_score:.1f}/100 |
| 複雑度 | {review_result.complexity_score:.1f}/100 |
| 保守性 | {review_result.maintainability_score:.1f}/100 |

## 🚨 問題サマリー

| 重要度 | 件数 |
|--------|------|
| 🔴 Critical | {sum(1 for i in review_result.issues if i.severity == 'critical')} |
| 🟠 High | {sum(1 for i in review_result.issues if i.severity == 'high')} |
| 🟡 Medium | {sum(1 for i in review_result.issues if i.severity == 'medium')} |
| 🟢 Low | {sum(1 for i in review_result.issues if i.severity == 'low')} |

## 📋 詳細な問題一覧

"""
        
        # 重要度順に問題を表示
        for severity in ['critical', 'high', 'medium', 'low']:
            severity_issues = [i for i in review_result.issues if i.severity == severity]
            if severity_issues:
                severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
                markdown_content += f"\n### {severity_emoji[severity]} {severity.upper()} Issues\n\n"
                
                for idx, issue in enumerate(severity_issues, 1):
                    markdown_content += f"""#### {idx}. {issue.review_point}

**ファイル**: `{issue.file_path}`  
**箇所**: {issue.line_number}行目"""
                    
                    if issue.function_name:
                        markdown_content += f", `{issue.function_name}()` 関数"
                    
                    markdown_content += f"""

**問題**: {issue.message}

**改善提案**: {issue.suggestion}

**問題のあるコード**:
```c
{issue.code_snippet}
```
"""
                    
                    if issue.fixed_code_example:
                        markdown_content += f"""
**修正例**:
```c
{issue.fixed_code_example}
```
"""
                    markdown_content += "\n---\n\n"
        
        # 推奨事項
        if review_result.critical_recommendations:
            markdown_content += "\n## 🔧 緊急対応推奨\n\n"
            for rec in review_result.critical_recommendations:
                markdown_content += f"- {rec}\n"
        
        if review_result.general_recommendations:
            markdown_content += "\n## 💡 一般的な改善提案\n\n"
            for rec in review_result.general_recommendations:
                markdown_content += f"- {rec}\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(filepath)
    
    def _generate_html_report(self, review_result: CReviewResult, timestamp: str, commit_short: str) -> str:
        """視覚的なHTMLレポート"""
        filename = f"c_review_{commit_short}_{timestamp}.html"
        filepath = self.output_dir / filename
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>C Code Review Report - {commit_short}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #fff; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; flex: 1; }}
        .issue-critical {{ border-left: 4px solid #dc3545; }}
        .issue-high {{ border-left: 4px solid #fd7e14; }}
        .issue-medium {{ border-left: 4px solid #ffc107; }}
        .issue-low {{ border-left: 4px solid #28a745; }}
        .code-block {{ background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; }}
        .file-path {{ color: #6c757d; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 C言語コードレビュー結果</h1>
        <p><strong>コミット:</strong> <code>{review_result.commit_hash}</code></p>
        <p><strong>実行時刻:</strong> {timestamp}</p>
        <p><strong>対象ファイル:</strong> {len(review_result.reviewed_files)}ファイル、{review_result.total_lines_reviewed}行</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <h3>総合品質</h3>
            <h2>{review_result.overall_quality_score:.1f}/100</h2>
        </div>
        <div class="metric-card">
            <h3>問題総数</h3>
            <h2>{len(review_result.issues)}</h2>
        </div>
        <div class="metric-card">
            <h3>Critical問題</h3>
            <h2 style="color: #dc3545;">{sum(1 for i in review_result.issues if i.severity == 'critical')}</h2>
        </div>
    </div>
"""
        
        # 問題の詳細をHTML形式で追加
        for issue in review_result.issues:
            css_class = f"issue-{issue.severity}"
            html_content += f"""
    <div class="issue {css_class}" style="margin: 20px 0; padding: 15px; border-radius: 8px; background: #fff;">
        <h3>{issue.review_point}</h3>
        <p class="file-path">{issue.file_path}:{issue.line_number}</p>
        <p><strong>問題:</strong> {issue.message}</p>
        <p><strong>改善提案:</strong> {issue.suggestion}</p>
        <div class="code-block">{issue.code_snippet}</div>
    </div>
"""
        
        html_content += """
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)
    
    def _generate_summary_report(self, review_result: CReviewResult, timestamp: str, commit_short: str) -> str:
        """コンソール表示用サマリー"""
        filename = f"c_review_summary_{commit_short}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        summary = f"""
====================================
C言語コードレビュー結果サマリー
====================================

コミット: {review_result.commit_hash}
実行時刻: {timestamp}
対象ファイル: {len(review_result.reviewed_files)}ファイル
総レビュー行数: {review_result.total_lines_reviewed}行

品質スコア: {review_result.overall_quality_score:.1f}/100

問題件数:
  🔴 Critical: {sum(1 for i in review_result.issues if i.severity == 'critical')}件
  🟠 High:     {sum(1 for i in review_result.issues if i.severity == 'high')}件
  🟡 Medium:   {sum(1 for i in review_result.issues if i.severity == 'medium')}件
  🟢 Low:      {sum(1 for i in review_result.issues if i.severity == 'low')}件

緊急対応が必要な問題:
"""
        
        critical_issues = [i for i in review_result.issues if i.severity == 'critical']
        if critical_issues:
            for issue in critical_issues:
                summary += f"  - {issue.file_path}:{issue.line_number} - {issue.review_point}\n"
        else:
            summary += "  なし\n"
        
        summary += f"\n詳細レポート:\n"
        summary += f"  - JSON: {self.output_dir}/c_review_{commit_short}_{timestamp}.json\n"
        summary += f"  - Markdown: {self.output_dir}/c_review_{commit_short}_{timestamp}.md\n"
        summary += f"  - HTML: {self.output_dir}/c_review_{commit_short}_{timestamp}.html\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return str(filepath)
```

## 使用例（完全ローカル）

### 基本的な使用方法
```bash
# ローカルコミットのレビュー
python c_agent_reviewer.py review abc123

# 現在のワーキングディレクトリの変更をレビュー
python c_agent_reviewer.py review HEAD

# 複数のレポート形式で出力
python c_agent_reviewer.py review abc123 --output all

# 特定のディレクトリにレポート出力
python c_agent_reviewer.py review abc123 --output-dir ./my_reviews
```

### レポート閲覧
```bash
# 生成されたレポートを表示
python c_agent_reviewer.py show-report ./review_reports/c_review_abc12345_20250701_103000.json

# HTMLレポートをブラウザで開く
python c_agent_reviewer.py open-report ./review_reports/c_review_abc12345_20250701_103000.html

# サマリーをコンソールに表示
python c_agent_reviewer.py summary abc123
```

### バッチ処理
```bash
# 複数のコミットを一括レビュー
python c_agent_reviewer.py batch-review abc123 def456 ghi789

# 指定期間のコミットをレビュー
python c_agent_reviewer.py review-period --since "2025-07-01" --until "2025-07-07"

# ブランチ全体のレビュー
python c_agent_reviewer.py review-branch feature/new-protocol
```## レビュー観点ファイルの例

### PDF形式のレビュー観点例
```
C言語コードレビュー観点

■ セキュリティ
- バッファオーバーフロー対策が適切に実装されているか
- 入力値検証が十分に行われているか
- 危険な関数（strcpy, strcat, sprintf, gets）の使用を避けているか
- メモリアクセス前の境界チェックが実装されているか

■ メモリ管理
- malloc/callocで確保したメモリが適切にfreeされているか
- ダブルフリーが発生する可能性はないか
- ポインタの初期化が適切に行われているか
- NULLポインタアクセスの可能性はないか

■ パフォーマンス
- ループ内での不要な処理は避けられているか
- 関数呼び出しの回数を最小化しているか
- メモリアロケーションが効率的に行われているか

■ コード品質
- 関数の責任が単一になっているか
- マジックナンバーが避けられているか
- 適切なコメントが記述されているか
```

### Markdown形式のレビュー観点例
```markdown
# C言語コードレビュー観点

## セキュリティ

- [ ] バッファオーバーフローの脆弱性がないか
- [ ] 入力値の検証が適切に行われているか
- [ ] 危険な関数の使用を避けているか
  - strcpy → strncpy
  - sprintf → snprintf
  - gets → fgets

## メモリ管理

- [ ] メモリリークが発生しないか
- [ ] ダブルフリーの可能性はないか
- [ ] 未初期化ポインタの使用はないか

## エラーハンドリング

- [ ] 戻り値のチェックが適切に行われているか
- [ ] エラー時の適切なクリーンアップが実装されているか
```

### TXT形式のレビュー観点例
```
セキュリティ観点：
・バッファオーバーフローの防止
・入力値検証の実装
・危険な関数の回避

メモリ管理観点：
・メモリリークの防止
・適切なポインタ管理
・リソースの確実な解放

パフォーマンス観点：
・ループ効率の最適化
・関数呼び出しコストの考慮
・メモリアクセスパターンの最適化
```

## エージェントの対話例

### セットアップ時の対話例
```
Agent: C言語プロジェクトのレビュー設定を開始します...

Agent: レビュー観点ファイルを指定してください:
       対応形式: PDF, Markdown(.md), テキスト(.txt)

User: ./review_guidelines.pdf

Agent: ✓ PDFファイルを解析中...
Agent: ✓ 以下のレビュー観点を検出しました:
       - セキュリティ: 15項目
       - メモリ管理: 12項目  
       - パフォーマンス: 8項目
       - コード品質: 20項目

Agent: 追加のレビュー観点ファイルはありますか？ [y/N]

User: y

User: ./company_standards.md

Agent: ✓ Markdownファイルを解析中...
Agent: ✓ 企業固有の観点を追加しました:
       - コーディング規約: 10項目
       - 組み込み固有: 7項目

Agent: 🎉 セットアップ完了！
       レビュー観点を .code_review_agent/c_review_points.yaml に保存しました
       
       今後は以下のコマンドでC言語レビューを実行できます:
       python c_agent_reviewer.py review <commit_hash>
```

### 自動レビュー実行例
```
Agent: コミット abc123 のC言語レビューを開始します...

[File Detection]
Agent: ✓ C言語ファイルを検出しました:
       - src/network/tcp_handler.c (新規, 234行)
       - include/security.h (変更, 45行)
       - src/memory/allocator.c (変更, 156行)

[Static Analysis]
Agent: ✓ cppcheck による静的解析を実行中...
Agent: ✓ カスタム解析ルールを適用中...

[Review Execution]
Agent: tcp_handler.c のレビューを開始...
Agent: ⚠️ セキュリティ問題を検出:
       ファイル: src/network/tcp_handler.c
       箇所: 行 67-72, 関数 handle_connection()
       観点: バッファオーバーフロー対策
       問題: strcpy関数の使用でバッファオーバーフローの可能性

Agent: ⚠️ メモリ管理問題を検出:
       ファイル: src/network/tcp_handler.c  
       箇所: 行 145, 関数 cleanup_connection()
       観点: メモリリークの防止
       問題: malloc で確保したメモリが一部の条件でfreeされない

Agent: allocator.c のレビューを開始...
Agent: ✓ メモリ管理が適切に実装されています
Agent: ⚠️ パフォーマンス改善の余地:
       ファイル: src/memory/allocator.c
       箇所: 行 89-95, 関数 find_free_block()
       観点: ループ効率の最適化
       問題: 線形探索が非効率、ハッシュテーブルの検討を推奨

[Validation Phase]
Agent: ✓ 全ファイル・全関数のレビューが完了しました
Agent: ✓ 設定されたレビュー観点が全て適用されました

[Report Generation]
Agent: 📊 C言語レビュー結果サマリー:
       - レビュー対象: 3ファイル, 435行
       - 重要度 CRITICAL: 1件
       - 重要度 HIGH: 2件  
       - 重要度 MEDIUM: 3件
       
       📝 詳細レポートを生成: ./review_reports/c_review_abc123.json
       📄 開発者向けレポート: ./review_reports/c_review_abc123.md
```

## 出力レポートの例

### JSON形式の詳細レポート
```json
{
  "commit_hash": "abc123",
  "timestamp": "2025-07-01T10:30:00Z",
  "reviewed_files": [
    "src/network/tcp_handler.c",
    "include/security.h", 
    "src/memory/allocator.c"
  ],
  "total_lines_reviewed": 435,
  "issues": [
    {
      "file_path": "src/network/tcp_handler.c",
      "line_number": 67,
      "column_number": 12,
      "function_name": "handle_connection",
      "review_point": "バッファオーバーフロー対策",
      "category": "security",
      "severity": "critical",
      "message": "strcpy関数の使用により、バッファオーバーフローが発生する可能性があります",
      "suggestion": "strncpy関数を使用し、適切なバッファサイズ制限を実装してください",
      "code_snippet": "char buffer[256];\nstrcpy(buffer, user_input);",
      "fixed_code_example": "char buffer[256];\nstrncpy(buffer, user_input, sizeof(buffer) - 1);\nbuffer[sizeof(buffer) - 1] = '\\0';"
    },
    {
      "file_path": "src/network/tcp_handler.c", 
      "line_number": 145,
      "function_name": "cleanup_connection",
      "review_point": "メモリリークの防止",
      "category": "memory_management",
      "severity": "high",
      "message": "エラー処理パスでメモリが解放されない可能性があります",
      "suggestion": "goto文を使用した共通エラーハンドリングの実装を推奨",
      "code_snippet": "if (error) {\n    return -1; // メモリリーク発生\n}\nfree(connection_data);",
      "fixed_code_example": "if (error) {\n    goto cleanup;\n}\n\ncleanup:\n    if (connection_data) {\n        free(connection_data);\n    }\n    return result;"
    }
  ],
  "security_issues": 1,
  "performance_issues": 1,
  "memory_issues": 1,
  "code_quality_issues": 0,
  "overall_quality_score": 78.5,
  "complexity_score": 65.2,
  "maintainability_score": 82.1,
  "critical_recommendations": [
    "tcp_handler.c の strcpy 使用箇所を即座に修正",
    "メモリリーク防止のためエラーハンドリング見直し"
  ],
  "general_recommendations": [
    "パフォーマンス向上のため線形探索をハッシュテーブルに変更",
    "静的解析ツールの定期実行を推奨"
  ],
  "applied_review_points": [
    "バッファオーバーフロー対策",
    "メモリリークの防止", 
    "ループ効率の最適化",
    "適切なエラーハンドリング"
  ]
}
```

### Markdown形式の開発者向けレポート
```markdown
# C言語コードレビュー結果

**コミット**: abc123  
**レビュー日時**: 2025-07-01 10:30:00  
**レビュー対象**: 3ファイル、435行

## 📊 サマリー

| 項目 | 件数 |
|------|------|
| 🔴 Critical | 1 |
| 🟠 High | 2 |  
| 🟡 Medium | 3 |
| 🟢 Low | 0 |

**総合品質スコア**: 78.5/100

## 🚨 緊急対応が必要な問題

### 1. バッファオーバーフロー脆弱性

**ファイル**: `src/network/tcp_handler.c`  
**箇所**: 67行目、`handle_connection()` 関数  
**レビュー観点**: バッファオーバーフロー対策

**問題**:
```c
char buffer[256];
strcpy(buffer, user_input);  // ❌ 危険
```

**修正例**:
```c
char buffer[256];
strncpy(buffer, user_input, sizeof(buffer) - 1);
buffer[sizeof(buffer) - 1] = '\0';  // ✅ 安全
```

## ⚠️ 重要な問題

### 2. メモリリーク

**ファイル**: `src/network/tcp_handler.c`  
**箇所**: 145行目、`cleanup_connection()` 関数  
**レビュー観点**: メモリリークの防止

**問題**: エラー時にメモリが解放されない

**修正例**:
```c
// goto文による統一エラーハンドリング
if (error) {
    goto cleanup;
}

cleanup:
    if (connection_data) {
        free(connection_data);
    }
    return result;
```

## 📈 改善提案

### 3. パフォーマンス最適化

**ファイル**: `src/memory/allocator.c`  
**箇所**: 89-95行目、`find_free_block()` 関数  
**レビュー観点**: ループ効率の最適化

線形探索をハッシュテーブルに変更することで、O(n) → O(1) の改善が期待できます。

## ✅ 適用されたレビュー観点

- ✅ バッファオーバーフロー対策
- ✅ メモリリークの防止
- ✅ ループ効率の最適化
- ✅ 適切なエラーハンドリング
- ✅ 危険な関数の回避チェック
- ✅ ポインタ管理の検証

## 📝 次回への改善提案

1. **静的解析ツールの活用**: cppcheck, clang-static-analyzer の定期実行
2. **コードレビューの自動化**: Git hooks による自動レビュー実行
3. **セキュリティガイドラインの強化**: MISRA-C 準拠の検討
```

## 使用例

### セットアップ（一度のみ）
```bash
# 必要なライブラリのインストール
pip install langchain langchain-community PyPDF2 markdown beautifulsoup4 GitPython PyYAML

# C言語プロジェクト初期化（ローカル）
cd /path/to/c/project
python c_agent_reviewer.py init

# レビュー観点ファイルでセットアップ
python c_agent_reviewer.py setup --review-files ./guidelines.pdf ./standards.md

# 出力ディレクトリの設定
python c_agent_reviewer.py config --set output.directory "./my_review_reports"
```

### 自動レビュー（ローカル完結）
```bash
# 基本的なC言語レビュー
python c_agent_reviewer.py review abc123

# 複数形式でレポート生成
python c_agent_reviewer.py review abc123 --output all

# HTMLレポートを生成してブラウザで開く
python c_agent_reviewer.py review abc123 --output html --open

# サマリーをコンソールに表示
python c_agent_reviewer.py review abc123 --show-summary

# 過去のレビュー結果と比較
python c_agent_reviewer.py review abc123 --compare-with def456
```

### レポート管理
```bash
# 生成されたレポートの一覧表示
python c_agent_reviewer.py list-reports

# 特定のレポートを表示
python c_agent_reviewer.py show-report ./review_reports/c_review_abc12345_20250701.json

# レポートの統計情報
python c_agent_reviewer.py report-stats --period "last-week"
```

### 高度な機能
```bash
# バッチ処理（複数コミット）
python c_agent_reviewer.py batch-review abc123 def456 ghi789

# 期間指定レビュー
python c_agent_reviewer.py review-period --since "2025-07-01" --until "2025-07-07"

# ブランチ全体のレビュー
python c_agent_reviewer.py review-branch feature/network-protocol

# 差分レビュー（2つのコミット間）
python c_agent_reviewer.py review-diff abc123..def456

# ファイル指定レビュー
python c_agent_reviewer.py review HEAD --files "src/security/*.c"

# Git hooks としてインストール（ローカル）
python c_agent_reviewer.py install-local-hooks
# 以降、git commit 時に自動でローカルレビュー実行
```

## エージェントの詳細実行例

### 完全なレビュー実行ログ
```
$ python c_agent_reviewer.py review abc123 --verbose

🤖 C言語コードレビューエージェントを起動中...

[初期化フェーズ]
✓ .code_review_agent/c_review_points.yaml からレビュー観点を読み込み
✓ Ollama LLM (codellama) に接続成功
✓ レビューツールを初期化: 7個のツールが利用可能

[Git解析フェーズ]
Agent: コミット abc123 の変更内容を解析します...
Tool: local_git_analyzer("get_commit_changes", "abc123")

✓ 変更検出:
  - 新規: src/network/tcp_server.c (186行)
  - 変更: src/security/auth.c (+45行, -12行)
  - 変更: include/protocol.h (+8行, -3行)

[レビュー計画フェーズ]
Agent: ファイルの重要度とレビュー戦略を決定中...
  
  tcp_server.c: HIGH priority (新規ファイル + ネットワーク処理)
    適用ルール: セキュリティ, バッファオーバーフロー対策, ネットワークセキュリティ
    
  auth.c: CRITICAL priority (認証関連)
    適用ルール: セキュリティ, 入力値検証, メモリ管理
    
  protocol.h: MEDIUM priority (ヘッダーファイル)
    適用ルール: コード品質, インターフェース設計

[静的解析フェーズ]
Tool: c_static_analyzer("tcp_server.c")
✓ cppcheck実行完了: 2件の警告を検出
✓ カスタム解析完了: メモリ管理に1件の問題を検出

[詳細レビューフェーズ]
Agent: tcp_server.c の詳細レビューを開始...

Tool: c_code_parser("src/network/tcp_server.c")
✓ 関数解析: 8個の関数を検出
✓ 複雑度計算: 平均複雑度 4.2 (良好)

Agent: handle_client_connection() 関数をレビュー中...
Tool: rule_evaluator(セキュリティルール, コード断片)

⚠️  問題検出:
    ファイル: src/network/tcp_server.c
    行: 67-72
    関数: handle_client_connection()
    観点: バッファオーバーフロー対策
    重要度: CRITICAL

Agent: recv_data() 関数をレビュー中...
✓ 適切なバッファ管理が実装されています

Agent: cleanup_connection() 関数をレビュー中...
⚠️  問題検出:
    メモリリークの可能性を検出

[品質検証フェーズ]
Agent: レビューの完全性をチェック中...
✓ 全関数がレビュー済み: 8/8
✓ 全レビュー観点が適用済み: 15/15
✓ 重要度の高いファイルが優先処理済み

[学習フェーズ]
Agent: 新しいパターンを学習中...
✓ ネットワーク処理の新しいパターンを記録
✓ このプロジェクトの傾向を更新

[レポート生成フェーズ]
Tool: report_generator("comprehensive", 結果データ)

✓ JSONレポート生成: ./review_reports/c_review_abc12345_20250701_143022.json
✓ Markdownレポート生成: ./review_reports/c_review_abc12345_20250701_143022.md  
✓ HTMLレポート生成: ./review_reports/c_review_abc12345_20250701_143022.html
✓ サマリーレポート生成: ./review_reports/c_review_summary_abc12345_20250701_143022.txt

[最終結果]
====================================
🎯 レビュー完了サマリー
====================================

品質スコア: 73.5/100 (改善の余地あり)
検出問題: 4件
  🔴 Critical: 1件 (バッファオーバーフロー)
  🟠 High: 1件 (メモリリーク)  
  🟡 Medium: 2件
  🟢 Low: 0件

緊急対応推奨:
  ❗ tcp_server.c:67 strcpy使用の修正が必要

詳細レポートパス:
  📄 ./review_reports/c_review_abc12345_20250701_143022.md

レビュー実行時間: 2分34秒
処理ファイル: 3ファイル、239行
使用LLM: codellama (47回のAPI呼び出し)
```

### HTMLレポートのプレビュー機能
```python
class LocalReportViewer:
    """ローカルレポートの表示・管理"""
    
    def open_html_report(self, report_path: str):
        """HTMLレポートをブラウザで開く"""
        import webbrowser
        import os
        
        full_path = os.path.abspath(report_path)
        webbrowser.open(f"file://{full_path}")
        print(f"ブラウザでレポートを開きました: {report_path}")
    
    def generate_reports_index(self, reports_dir: str = "./review_reports"):
        """すべてのレポートのインデックスページを生成"""
        reports_path = Path(reports_dir)
        reports = list(reports_path.glob("c_review_*.json"))
        
        index_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>C Code Review Reports Index</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .report-card { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .score-high { color: #28a745; }
        .score-medium { color: #ffc107; }
        .score-low { color: #dc3545; }
    </style>
</head>
<body>
    <h1>📊 C言語コードレビュー履歴</h1>
    <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        for report_file in sorted(reports, reverse=True):
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            score = report_data['overall_quality_score']
            score_class = "score-high" if score >= 80 else "score-medium" if score >= 60 else "score-low"
            
            # 対応するHTMLファイルのパス
            html_file = report_file.with_suffix('.html')
            
            index_html += f"""
    <div class="report-card">
        <h3>コミット: {report_data['commit_hash'][:8]}</h3>
        <p>日時: {report_data['timestamp']}</p>
        <p>品質スコア: <span class="{score_class}">{score:.1f}/100</span></p>
        <p>問題件数: {len(report_data['issues'])}件</p>
        <p>対象ファイル: {', '.join(report_data['reviewed_files'])}</p>
        <a href="{html_file.name}">詳細レポートを見る</a> | 
        <a href="{report_file.name}">JSON形式で見る</a>
    </div>
"""
        
        index_html += """
</body>
</html>"""
        
        index_path = reports_path / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        return str(index_path)
```

## 期待される効果

このローカル完結型C言語エージェントにより：

1. **完全ローカル実行** - 外部API不要、セキュアな環境での実行
2. **GitLab完全対応** - GitLabのコミットハッシュで問題なく動作
3. **多様な出力形式** - JSON、Markdown、HTML、テキストでの詳細レポート
4. **オフライン動作** - インターネット接続不要で動作
5. **履歴管理機能** - 過去のレビュー結果の蓄積・比較・統計
6. **自動化対応** - Git hooksによるローカル自動実行
7. **カスタマイズ可能** - プロジェクトに応じたレポート形式
8. **高速実行** - ローカル処理によるレスポンス向上

これにより、セキュリティ要件の厳しい企業環境や、オフライン開発環境でも、高品質なC言語コードレビューが確実に実現されます。ェクト初期化
cd /path/to/c/project
python c_agent_reviewer.py init

# レビュー観点ファイルでセットアップ
python c_agent_reviewer.py setup --review-files ./guidelines.pdf ./standards.md

# 複数ファイルからの一括セットアップ
python c_agent_reviewer.py setup --review-files ./security.pdf ./memory.md ./performance.txt
```

### 自動レビュー（継続使用）
```bash
# 基本的なC言語レビュー
python c_agent_reviewer.py review abc123

# 特定のファイルのみレビュー
python c_agent_reviewer.py review abc123 --files "*.c"

# 詳細ログ付きレビュー
python c_agent_reviewer.py review abc123 --verbose

# JSON形式での結果出力
python c_agent_reviewer.py review abc123 --output json

# Git hooksとの統合（完全自動化）
python c_agent_reviewer.py install-hooks
# 以降、git commit時に自動でC言語レビュー実行
```

### レビュー観点の管理
```bash
# 設定されたレビュー観点の確認
python c_agent_reviewer.py config --show-points

# レビュー観点の追加
python c_agent_reviewer.py config --add-points ./new_guidelines.pdf

# レビュー観点の更新
python c_agent_reviewer.py config --update-points ./updated_standards.md
```

## 期待される効果

このC言語特化エージェントにより：

1. **ファイル入力による柔軟な設定** - PDF/MD/TXTから自動でレビュー観点を抽出
2. **C言語特有の問題検出** - メモリリーク、バッファオーバーフロー等の専門的検出
3. **詳細な指摘情報** - ファイル、行番号、関数名、観点が明確に特定
4. **構造化された出力** - JSON/Markdownでの開発者フレンドリーなレポート
5. **静的解析ツール統合** - cppcheck等の既存ツールとの連携
6. **完全自動化** - セットアップ後はコミットハッシュのみでレビュー完了

これにより、C言語開発チームの品質向上と作業効率化が実現されます。## C言語特化のエージェント設計

### コアアーキテクチャ

```python
class CCodeReviewAgent:
    """C言語専用LangChainベースのコードレビューエージェント"""
    
    def __init__(self, config_path: str = None):
        self.config_manager = CConfigManager(config_path)
        self.llm = self._setup_ollama_llm()
        self.tools = self._setup_c_specific_tools()
        self.memory = self._setup_memory()
        self.agent = self._create_agent()
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=50
        )
    
    def _setup_c_specific_tools(self) -> List[BaseTool]:
        """C言語専用ツールを設定"""
        return [
            CGitAnalysisTool(),
            CCodeParserTool(), 
            CRuleEvaluatorTool(),
            CFileAnalyzerTool(),
            CStaticAnalysisTool(),
            ReviewPointLoaderTool(),
            CReportGeneratorTool()
        ]
    
    def setup_from_files(self, review_point_files: List[str]) -> bool:
        """レビュー観点ファイルからセットアップ"""
        review_points = {}
        
        for file_path in review_point_files:
            points = self._load_review_points_from_file(file_path)
            review_points.update(points)
        
        self.config_manager.save_review_points(review_points)
        return True
    
    def _load_review_points_from_file(self, file_path: str) -> Dict:
        """各種ファイル形式からレビュー観点を読み込み"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return self._parse_pdf_review_points(file_path)
        elif file_extension == '.md':
            return self._parse_markdown_review_points(file_path)
        elif file_extension == '.txt':
            return self._parse_text_review_points(file_path)
        else:
            raise ValueError(f"未対応のファイル形式: {file_extension}")
```

## レビュー観点ファイル処理システム

### PDF解析ツール
```python
class ReviewPointLoaderTool(BaseTool):
    name = "review_point_loader"
    description = "PDF/MD/TXTファイルからレビュー観点を読み込み"
    
    def _run(self, file_path: str) -> str:
        """レビュー観点ファイルを解析して構造化データに変換"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                content = self._extract_from_pdf(file_path)
            elif file_ext == '.md':
                content = self._extract_from_markdown(file_path)
            elif file_ext == '.txt':
                content = self._extract_from_text(file_path)
            else:
                return f"未対応のファイル形式: {file_ext}"
            
            # 構造化されたレビュー観点に変換
            structured_points = self._parse_review_content(content)
            return json.dumps(structured_points, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"ファイル読み込みエラー: {str(e)}"
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """PDFからテキストを抽出"""
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        return "\n".join([page.page_content for page in pages])
    
    def _extract_from_markdown(self, file_path: str) -> str:
        """Markdownファイルを読み込み"""
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # MarkdownをHTMLに変換してから解析
        html = markdown.markdown(md_content)
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()
    
    def _extract_from_text(self, file_path: str) -> str:
        """テキストファイルを読み込み"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _parse_review_content(self, content: str) -> Dict:
        """レビュー観点テキストを構造化"""
        review_points = {
            "security": [],
            "performance": [],
            "code_quality": [],
            "memory_management": [],
            "custom": []
        }
        
        # セクション別に解析
        current_category = "custom"
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # カテゴリの検出
            if any(keyword in line.lower() for keyword in ['セキュリティ', 'security']):
                current_category = "security"
            elif any(keyword in line.lower() for keyword in ['パフォーマンス', 'performance']):
                current_category = "performance"
            elif any(keyword in line.lower() for keyword in ['品質', 'quality']):
                current_category = "code_quality"
            elif any(keyword in line.lower() for keyword in ['メモリ', 'memory']):
                current_category = "memory_management"
            elif line.startswith('-') or line.startswith('*') or line.startswith('•'):
                # リスト項目として認識
                point = line[1:].strip()
                if point:
                    review_points[current_category].append({
                        "description": point,
                        "priority": "medium",
                        "applicable_files": ["*.c", "*.h"]
                    })
        
        return review_points
```

### C言語専用解析ツール

#### 1. **C言語構文解析ツール**
```python
class CCodeParserTool(BaseTool):
    name = "c_code_parser"
    description = "C言語ファイルを解析して関数、構造体、マクロ等を抽出"
    
    def _run(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            "functions": self._extract_functions(content),
            "structs": self._extract_structs(content),
            "macros": self._extract_macros(content),
            "includes": self._extract_includes(content),
            "global_variables": self._extract_global_vars(content),
            "complexity_metrics": self._calculate_c_complexity(content),
            "potential_issues": self._detect_c_issues(content)
        }
        
        return json.dumps(analysis, ensure_ascii=False, indent=2)
    
    def _extract_functions(self, content: str) -> List[Dict]:
        """関数定義を抽出"""
        functions = []
        
        # 関数定義の正規表現パターン
        func_pattern = r'(\w+\s+)?(\w+)\s*\([^)]*\)\s*{'
        matches = re.finditer(func_pattern, content, re.MULTILINE)
        
        for match in matches:
            func_start = match.start()
            func_name = match.group(2)
            
            # 関数の終了位置を見つける
            func_end = self._find_function_end(content, func_start)
            func_body = content[func_start:func_end]
            
            functions.append({
                "name": func_name,
                "start_line": content[:func_start].count('\n') + 1,
                "end_line": content[:func_end].count('\n') + 1,
                "body": func_body,
                "complexity": self._calculate_function_complexity(func_body)
            })
        
        return functions
    
    def _extract_structs(self, content: str) -> List[Dict]:
        """構造体定義を抽出"""
        structs = []
        struct_pattern = r'typedef\s+struct\s*(\w+)?\s*{([^}]*)}\s*(\w+);?'
        
        for match in re.finditer(struct_pattern, content, re.DOTALL):
            struct_name = match.group(3) or match.group(1)
            struct_body = match.group(2)
            
            structs.append({
                "name": struct_name,
                "members": self._parse_struct_members(struct_body),
                "line_number": content[:match.start()].count('\n') + 1
            })
        
        return structs
    
    def _detect_c_issues(self, content: str) -> List[Dict]:
        """C言語特有の問題を検出"""
        issues = []
        
        # バッファオーバーフローの可能性
        dangerous_funcs = ['strcpy', 'strcat', 'sprintf', 'gets']
        for func in dangerous_funcs:
            if func in content:
                issues.append({
                    "type": "security",
                    "severity": "high",
                    "description": f"危険な関数 {func} の使用を検出"
                })
        
        # メモリリークの可能性
        malloc_count = content.count('malloc')
        free_count = content.count('free')
        if malloc_count > free_count:
            issues.append({
                "type": "memory_leak",
                "severity": "medium", 
                "description": f"malloc({malloc_count})とfree({free_count})の数が不一致"
            })
        
        return issues
```

#### 2. **C言語静的解析ツール**
```python
class CStaticAnalysisTool(BaseTool):
    name = "c_static_analyzer"
    description = "cppcheck、clang-tidy等を使用したC言語静的解析"
    
    def _run(self, file_path: str) -> str:
        results = {
            "cppcheck_results": self._run_cppcheck(file_path),
            "splint_results": self._run_splint(file_path),
            "custom_analysis": self._run_custom_analysis(file_path)
        }
        
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run_cppcheck(self, file_path: str) -> List[Dict]:
        """cppcheckによる静的解析"""
        try:
            cmd = ['cppcheck', '--enable=all', '--xml', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # XML結果を解析（簡略化）
            issues = []
            if result.stderr:
                # 実際の実装では適切なXMLパーサーを使用
                lines = result.stderr.split('\n')
                for line in lines:
                    if 'error' in line or 'warning' in line:
                        issues.append({
                            "tool": "cppcheck",
                            "message": line.strip(),
                            "severity": "medium"
                        })
            
            return issues
        except FileNotFoundError:
            return [{"error": "cppcheck not found"}]
```

## 構造化出力システム

### レビュー結果の詳細構造
```python
class CReviewIssue(BaseModel):
    """C言語レビュー問題の詳細構造"""
    file_path: str = Field(description="指摘ファイルのパス")
    line_number: int = Field(description="指摘箇所の行番号")
    column_number: Optional[int] = Field(description="指摘箇所の列番号")
    function_name: Optional[str] = Field(description="指摘箇所の関数名")
    review_point: str = Field(description="適用されたレビュー観点")
    category: str = Field(description="問題カテゴリ（security/performance/quality等）")
    severity: str = Field(description="重要度（critical/high/medium/low）")
    message: str = Field(description="問題の詳細説明")
    suggestion: str = Field(description="具体的な改善提案")
    code_snippet: str = Field(description="問題のあるコード抜粋")
    fixed_code_example: Optional[str] = Field(description="修正例のコード")

class CReviewResult(BaseModel):
    """C言語レビュー結果の完全な構造"""
    commit_hash: str
    timestamp: str
    reviewed_files: List[str] = Field(description="レビュー対象のCファイル一覧")
    total_lines_reviewed: int
    issues: List[CReviewIssue]
    
    # カテゴリ別サマリー
    security_issues: int = Field(description="セキュリティ問題数")
    performance_issues: int = Field(description="パフォーマンス問題数")
    memory_issues: int = Field(description="メモリ管理問題数")
    code_quality_issues: int = Field(description="コード品質問題数")
    
    # メトリクス
    overall_quality_score: float = Field(description="総合品質スコア (0-100)")
    complexity_score: float = Field(description="複雑度スコア")
    maintainability_score: float = Field(description="保守性スコア")
    
    # 推奨事項
    critical_recommendations: List[str] = Field(description="緊急対応推奨事項")
    general_recommendations: List[str] = Field(description="一般的な改善推奨")
    
    # 適用されたレビュー観点
    applied_review_points: List[str] = Field(description="適用されたレビュー観点一覧")
```

### プロンプトテンプレート

#### システムプロンプト
```python
def _get_system_prompt(self) -> str:
    return """
あなたは高度なコードレビューエージェントです。以下の能力を持っています：

## 基本方針
1. **完全性の保証**: 全ファイル・全セクションを確実にレビュー
2. **自律的判断**: 設定に基づいて適切なルールを自動選択・適用
3. **継続的改善**: レビュー結果から学習し、精度を向上
4. **コンテキスト認識**: ファイルの種類・重要度に応じた適切な深度でレビュー

## 利用可能なツール
- git_analyzer: コミットの変更内容を解析
- code_parser: コードの構造を解析（AST、関数、クラス等）
- rule_evaluator: 設定されたルールに基づいてコードを評価
- file_analyzer: ファイルの読み込み・分析
- config_manager: プロジェクト設定の管理
- learning_tool: 新しいパターンの学習・記録

## レビュープロセス
1. **計画立案**: 変更内容を分析し、レビュー計画を策定
2. **ルール選択**: ファイル種別・パス・内容に基づいて適用ルールを決定
3. **段階的レビュー**: ファイルごと、セクションごとに詳細レビュー
4. **品質検証**: レビューの完全性・一貫性をチェック
5. **学習・改善**: 新しいパターンを学習し、設定を最適化

## 出力形式
- 構造化された問題報告
- 具体的な改善提案
- 重要度別の問題分類
- コード例を含む説明

必ず全てのファイルとセクションを完全にレビューしてください。
"""
```

### エージェント実行例

```python
class CodeReviewWorkflow:
    """LangChainベースのレビューワークフロー"""
    
    def __init__(self, agent: CodeReviewAgent):
        self.agent = agent
    
    async def review_commit(self, commit_hash: str) -> ReviewResult:
        """コミットの完全レビューを実行"""
        
        # エージェントへの指示
        review_instruction = f"""
        コミット {commit_hash} の完全なコードレビューを実行してください。
        
        手順:
        1. git_analyzer でコミットの変更内容を解析
        2. 各変更ファイルに対して適切なルールを選択
        3. code_parser で詳細な構造解析
        4. rule_evaluator で各ルールを評価
        5. 全ファイルの完全性を検証
        6. 結果を構造化して報告
        7. learning_tool で新しいパターンを学習
        
        プロジェクト設定: {self.agent.config_manager.get_project_config()}
        """
        
        # エージェント実行
        result = await self.agent.executor.arun(review_instruction)
        
        return self._parse_review_result(result)
```

### 出力パーサー

```python
class ReviewResultParser(PydanticOutputParser):
    """レビュー結果の構造化パーサー"""
    
    class ReviewIssue(BaseModel):
        file_path: str = Field(description="問題のあるファイルパス")
        line_number: int = Field(description="問題のある行番号")
        category: str = Field(description="問題カテゴリ")
        severity: str = Field(description="重要度")
        message: str = Field(description="問題の説明")
        suggestion: str = Field(description="改善提案")
        code_example: Optional[str] = Field(description="修正例のコード")
    
    class ReviewResult(BaseModel):
        commit_hash: str
        timestamp: str
        total_files_reviewed: int
        issues: List[ReviewIssue]
        summary: str
        overall_quality_score: float
        recommendations: List[str]
    
    def get_format_instructions(self) -> str:
        return f"""
        レビュー結果は以下のJSON形式で出力してください：
        {super().get_format_instructions()}
        """
```

### 設定管理（LangChain統合）

```python
class ConfigManager:
    """LangChain統合の設定管理"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or ".code_review_agent"
        self.config = self._load_config()
        
    @lru_cache(maxsize=128)
    def get_review_rules_for_file(self, file_path: str) -> List[str]:
        """ファイルに適用すべきルールをキャッシュ付きで取得"""
        rules = []
        
        # 言語ベースルール
        language = self._detect_language(file_path)
        rules.extend(self.config.get(f"rules.{language}", []))
        
        # パスベースルール
        for pattern, rule_set in self.config.get("rules.path_patterns", {}).items():
            if pattern in file_path:
                rules.extend(rule_set)
        
        # プロジェクト種別ルール
        project_type = self.config.get("project.type")
        rules.extend(self.config.get(f"rules.{project_type}", []))
        
        return list(set(rules))  # 重複除去
```

**LangChainを使用する主な利点：**

1. **エージェント管理の簡素化** - AgentExecutorが複雑な状態管理を自動処理
2. **ツールの標準化** - BaseToolを継承して統一的なツール開発
3. **メモリ管理** - ConversationBufferWindowMemoryで文脈保持
4. **エラーハンドリング** - handle_parsing_errorsで堅牢性向上
5. **非同期処理** - arunによる高速な並列処理
6. **構造化出力** - PydanticOutputParserで一貫した結果フォーマット
7. **プロンプト管理** - ChatPromptTemplateで保守性向上

この設計により、複雑なエージェントロジックをLangChainに委譲し、ビジネスロジック（コードレビューの品質）に集中できるようになります。# C言語専用AIエージェント型コードレビューツール作成プロンプト

## 概要
C言語ファイルに特化したコードレビューを確実に完了させる自律的なAIエージェントを作成してください。**レビュー観点はファイル入力（PDF/MD/TXT）で設定**し、以降はコミットハッシュのみでレビューを実行します。エージェントは計画立案、実行、検証のサイクルを繰り返し、完全なレビューを保証します。

## エージェントアーキテクチャ

### コアコンポーネント

```python
class CodeReviewAgent:
    """メインエージェントクラス"""
    def __init__(self, config_path: str = None):
        self.config_manager = ConfigManager(config_path)  # 設定管理
        self.rule_engine = ReviewRuleEngine()             # ルールエンジン
        self.planner = ReviewPlanner()                    # 計画立案
        self.executor = ReviewExecutor()                  # レビュー実行  
        self.validator = ReviewValidator()                # 検証・品質保証
        self.memory = AgentMemory()                       # 状態管理
        self.tools = ReviewTools()                        # ツール群
    
    def review_commit(self, commit_hash: str) -> ReviewResult:
        """設定に基づいて完全なレビューを実行（追加入力不要）"""
        pass
    
    def setup_project(self, project_path: str, interactive: bool = True):
        """プロジェクト初期セットアップ（一度のみ実行）"""
        pass
```

### エージェントの思考プロセス

#### 1. **計画フェーズ (Planning)**
```python
class ReviewPlanner:
    def create_review_plan(self, files: List[str]) -> ReviewPlan:
        """
        - ファイルの依存関係を分析
        - レビュー優先度を決定
        - 処理順序を最適化
        - チャンク分割戦略を決定
        """
```

#### 2. **実行フェーズ (Execution)**
```python
class ReviewExecutor:
    def execute_review_step(self, step: ReviewStep) -> StepResult:
        """
        - 各ファイルを段階的にレビュー
        - 進捗状況を記録
        - エラー時の回復処理
        """
```

#### 3. **検証フェーズ (Validation)**
```python
class ReviewValidator:
    def validate_completeness(self, review_result: ReviewResult) -> ValidationResult:
        """
        - レビューの完全性をチェック
        - 見逃しがないか確認
        - 品質基準を満たしているか検証
        """
```

## 設定管理システム

### 初回セットアップフロー

#### 1. **プロジェクト分析**
```python
class ProjectAnalyzer:
    def analyze_project_structure(self, project_path: str) -> ProjectProfile:
        """
        プロジェクトを自動分析して適切な設定を推奨
        - 言語/フレームワークの検出
        - アーキテクチャパターンの識別
        - 既存のリンター/フォーマッター設定の読み込み
        - コーディング規約の推定
        """
        
    def detect_review_needs(self, git_history: List[Commit]) -> ReviewNeeds:
        """
        過去のコミット履歴から頻出問題を分析
        - よく発生するバグパターン
        - 修正が多い領域
        - パフォーマンス問題の傾向
        """
```

#### 2. **対話的セットアップ**
```python
class SetupWizard:
    def interactive_setup(self) -> ReviewConfiguration:
        """
        ユーザーとの1回限りの対話でプロジェクト設定を構築
        """
        project_type = self.detect_project_type()
        
        # プロジェクト特有の質問
        if project_type == "web_api":
            security_focus = self.ask_security_requirements()
            performance_sla = self.ask_performance_requirements()
        elif project_type == "data_pipeline":
            data_quality_rules = self.ask_data_quality_requirements()
            
        # 共通設定
        team_standards = self.ask_team_coding_standards()
        custom_rules = self.ask_custom_business_rules()
        
        return self.build_configuration(...)
```

### 設定システムの構造

#### プロジェクト設定ファイル
```yaml
# .code_review_agent/project_config.yaml
project:
  name: "MyWebApp"
  type: "web_api"  # web_api, mobile_app, data_pipeline, library, etc.
  language_primary: "python"
  languages_secondary: ["javascript", "sql"]
  frameworks: ["fastapi", "react", "postgresql"]
  
architecture:
  pattern: "microservices"  # monolith, microservices, serverless
  layers: ["api", "business", "data"]
  
team:
  coding_standards: "pep8_strict"
  review_strictness: "high"  # low, medium, high, critical
  domain_expertise: ["fintech", "api_security"]

# 自動検出された設定
auto_detected:
  existing_linters: ["flake8", "mypy", "black"]
  test_framework: "pytest"
  ci_cd: "github_actions"
  dependency_manager: "poetry"
```

#### レビュールール設定
```yaml
# .code_review_agent/review_rules.yaml
rules:
  # プロジェクト種別別のルール
  web_api:
    security:
      priority: "critical"
      checks:
        - "sql_injection_prevention"
        - "input_validation_comprehensive"
        - "authentication_authorization"
        - "sensitive_data_exposure"
    performance:
      priority: "high"
      checks:
        - "database_query_optimization"
        - "caching_strategy"
        - "async_await_usage"
        
  # 言語固有のルール  
  python:
    code_quality:
      priority: "high"
      checks:
        - "pep8_compliance"
        - "type_hints_usage"
        - "exception_handling"
        - "docstring_completeness"
        
  # ビジネスロジック固有のルール
  business_domain:
    fintech:
      - "decimal_precision_for_money"
      - "audit_trail_requirements"
      - "regulatory_compliance_checks"
      
# 条件付きルール
conditional_rules:
  - condition: "file_path.contains('payment')"
    rules: ["extra_security_checks", "transaction_integrity"]
  - condition: "commit_message.contains('hotfix')"
    rules: ["emergency_deployment_checks"]
```

#### 学習済み設定
```yaml
# .code_review_agent/learned_patterns.yaml
learned_patterns:
  frequent_issues:
    - pattern: "missing_error_handling_in_api_endpoints"
      frequency: 0.8
      severity: "high"
      auto_detect: true
      
  team_preferences:
    - pattern: "prefer_explicit_typing"
      confidence: 0.9
      
  custom_business_rules:
    - name: "user_data_access_logging"
      description: "全てのユーザーデータアクセスはログに記録"
      pattern_regex: "User\\.query|user_repository\\."
      check_function: "verify_audit_logging"
```

## 自動化されたレビューエンジン

### ルールエンジン
```python
class ReviewRuleEngine:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.rules = self._load_all_rules()
        
    def get_applicable_rules(self, file_context: FileContext) -> List[ReviewRule]:
        """
        ファイルの種類、パス、内容に基づいて適用すべきルールを自動選択
        """
        rules = []
        
        # 言語固有ルール
        rules.extend(self.get_language_rules(file_context.language))
        
        # パスベースルール
        rules.extend(self.get_path_based_rules(file_context.path))
        
        # 内容ベースルール
        rules.extend(self.get_content_based_rules(file_context.ast))
        
        # プロジェクト種別ルール
        rules.extend(self.get_project_type_rules())
        
        # 学習済みカスタムルール
        rules.extend(self.get_learned_rules(file_context))
        
        return self.prioritize_rules(rules)
        
    def execute_rule(self, rule: ReviewRule, code_segment: CodeSegment) -> RuleResult:
        """個別ルールの実行"""
        pass
```

### コンテキスト認識
```python
class FileContext:
    def __init__(self, file_path: str, content: str):
        self.path = file_path
        self.content = content
        self.language = self._detect_language()
        self.ast = self._parse_ast()
        self.imports = self._extract_imports()
        self.functions = self._extract_functions()
        self.classes = self._extract_classes()
        self.complexity_metrics = self._calculate_complexity()
        
    def get_review_priority(self) -> ReviewPriority:
        """ファイルの重要度を判定"""
        if "auth" in self.path or "security" in self.path:
            return ReviewPriority.CRITICAL
        elif "test" in self.path:
            return ReviewPriority.MEDIUM
        elif self.complexity_metrics.cyclomatic > 15:
            return ReviewPriority.HIGH
        else:
            return ReviewPriority.NORMAL
```

## 完全自動化のワークフロー

### セットアップフェーズ（一度のみ）
```bash
# 初回セットアップ
cd /path/to/project
python agent_reviewer.py setup --interactive

# 質問例:
# Q: このプロジェクトの種類は？ [web_api/mobile_app/data_pipeline/library]
# A: web_api
# 
# Q: セキュリティの重要度は？ [low/medium/high/critical]  
# A: high
#
# Q: 特別に注意すべきビジネスルールはありますか？
# A: 金融取引の処理では小数点精度が重要、全ての個人情報アクセスはログ記録が必要
#
# ✓ 設定完了！ .code_review_agent/ ディレクトリに設定を保存しました
```

### 自動レビューフェーズ（継続実行）
```bash
# 以降は簡単なコマンドのみ
python agent_reviewer.py review abc123

# またはGit hooksに組み込んで完全自動化
git commit -m "fix user authentication"
# → 自動的にレビューエージェントが起動
```

### エージェントの自律判断プロセス
```
1. コミットハッシュを受信
2. 変更されたファイルを分析
3. 各ファイルに適用すべきルールを自動選択
4. ファイルの重要度に応じてレビューの深度を調整
5. 過去の学習データから頻出問題を優先チェック
6. レビューを実行・検証
7. 結果を構造化して出力
8. 新しいパターンを学習データに追加
```

### 基本的な思考ループ
```
1. 現在の状況を分析 (Observe)
2. 次に何をすべきか計画 (Plan)  
3. 計画を実行 (Act)
4. 結果を評価 (Reflect)
5. 必要に応じて計画を修正して継続
```

### 具体的な行動例

#### シナリオ1: 大きなファイルの処理
```
観察: main.py は 500行のファイル
計画: 関数単位で分割してレビュー
実行: 各関数を順次レビュー
検証: 全関数がレビュー済みか確認
```

#### シナリオ2: 依存関係の発見
```
観察: utils.py で未知の関数を発見
計画: 関連ファイルを特定してレビュー対象に追加
実行: helper.py を追加でレビュー
検証: 依存関係が完全に解決されたか確認
```

## エージェントの記憶システム

### 短期記憶 (Working Memory)
```python
class WorkingMemory:
    current_file: str
    current_section: str
    pending_issues: List[Issue]
    completed_sections: Set[str]
    context_buffer: str
```

### 長期記憶 (Long-term Memory)
```python
class LongTermMemory:
    file_relationships: Dict[str, List[str]]
    common_patterns: List[Pattern]
    review_history: List[ReviewSession]
    learned_rules: List[Rule]
```

## 自己修正メカニズム

### 品質チェックポイント
1. **セクション完了チェック**
   - 各関数/クラスがレビュー済みか
   - 重要な部分が見逃されていないか

2. **一貫性チェック**
   - レビュー観点が一貫して適用されているか
   - 評価基準がブレていないか

3. **完全性チェック**
   - 全ファイルが処理されたか
   - 依存関係が全て解決されたか

### 再実行トリガー
```python
def should_retry_review(self, section_result: SectionResult) -> bool:
    """
    再レビューが必要かを判断
    - レビューが不完全
    - 品質基準を満たさない
    - 新しい依存関係を発見
    """
```

## 実装仕様

### 必要なライブラリ
```python
# LangChain エージェント基盤
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import BaseTool, tool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import AsyncCallbackHandler
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.runnable import RunnablePassthrough

# ドキュメント処理
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2
import markdown
from bs4 import BeautifulSoup

# C言語解析専用
import subprocess
import re
from typing import List, Dict, Set, Optional, Union
from pathlib import Path

# 構造化データ
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum

# Git操作
from git import Repo

# 設定管理
import yaml
import json
from functools import lru_cache
```

### 設定ファイル例
```yaml
# .code_review_agent/agent_config.yaml
agent_behavior:
  max_iterations: 100
  timeout_per_file: 300  # seconds
  chunk_size: 50         # lines per chunk
  quality_threshold: 0.8
  auto_learning: true    # 新しいパターンを自動学習
  
ollama_config:
  model: "codellama"
  base_url: "http://localhost:11434"
  context_window: 4096
  
automation:
  # 自動化レベル設定
  require_human_approval: false  # 完全自動化
  auto_apply_suggestions: false  # 提案のみ
  git_integration: true          # Git hooksと連携
  
output:
  format: "markdown"             # json, markdown, html
  include_suggestions: true
  include_code_examples: true
  verbosity: "detailed"          # minimal, standard, detailed
  
notifications:
  slack_webhook: "https://hooks.slack.com/..."
  email_recipients: ["team@company.com"]
  critical_issues_only: false
```

## エージェントの対話例

### セットアップ時の対話例
```
Agent: プロジェクトの分析を開始します...

Agent: ✓ Python FastAPI プロジェクトを検出しました
Agent: ✓ PostgreSQL データベースを使用していることを確認
Agent: ✓ 既存の設定ファイル (.flake8, mypy.ini) を発見

Agent: プロジェクトの種類を確認させてください:
       検出結果: Web API (FastAPI)
       この判定で正しいですか？ [Y/n]

User: Y

Agent: セキュリティの重要度を教えてください:
       [1] Low - 内部ツール
       [2] Medium - 一般的なWebアプリ  
       [3] High - 機密データを扱う
       [4] Critical - 金融・医療等

User: 4

Agent: ✓ 金融系アプリケーション向けの厳格なセキュリティルールを適用します

Agent: 特別に注意すべきビジネスルールはありますか？
       例: 「決済処理では必ず監査ログ」「個人情報は暗号化必須」

User: 全ての金額計算はDecimal型を使用、個人情報アクセスは全てログ記録

Agent: ✓ カスタムルールを作成しました:
       - 金額計算でのDecimal型チェック
       - 個人情報アクセス時のログ記録チェック

Agent: 🎉 セットアップ完了！
       設定ファイルを .code_review_agent/ に保存しました
       
       今後は以下のコマンドでレビューを実行できます:
       python agent_reviewer.py review <commit_hash>
```

### 自動レビュー実行例
```
Agent: コミット abc123 のレビューを開始します...

[Auto-Configuration Loading]
Agent: ✓ プロジェクト設定を読み込みました
Agent: ✓ Web API + 金融系の厳格ルールを適用します

[Planning Phase]
Agent: 変更されたファイルを分析中...
- src/payment/processor.py (新規作成, 156行)
- src/auth/middleware.py (変更, 89行)
- tests/test_payment.py (新規作成, 78行)

Agent: ファイル重要度を判定中...
- payment/processor.py: CRITICAL (決済処理 + 金融ルール)
- auth/middleware.py: HIGH (認証・認可)
- test_payment.py: MEDIUM (テストファイル)

[Execution Phase]
Agent: payment/processor.py の厳格レビューを開始...
Agent: ✓ Decimal型の使用を確認
Agent: ⚠️ 監査ログが不足している箇所を検出 (行 45-52)
Agent: ✓ 例外処理が適切に実装されています
Agent: ⚠️ 入力値検証にセキュリティ脆弱性の可能性 (行 78)

Agent: auth/middleware.py のセキュリティレビューを開始...
Agent: ✓ JWTトークンの検証ロジックが適切です
Agent: ✓ レート制限の実装を確認

[Validation Phase]
Agent: レビューの完全性をチェック中...
Agent: ✓ 全ファイル・全関数がレビュー済みです
Agent: ✓ 金融系カスタムルールが全て適用されました

[Learning Phase]
Agent: 新しいパターンを学習中...
Agent: ✓ 決済処理の新しいパターンを学習しました

[Final Report]
Agent: 📊 レビュー結果サマリー:
       - 重要度: CRITICAL
       - 検出された問題: 2件
       - セキュリティ問題: 1件
       - ビジネスルール違反: 1件
       - 推奨改善: 3件
       
       📝 詳細レポートを生成しました: ./review_reports/abc123_review.md
       🔔 Slack通知を送信しました
```

## 高度な機能

### 学習機能
```python
class LearningModule:
    def learn_from_feedback(self, feedback: ReviewFeedback):
        """人間のフィードバックから学習"""
        
    def update_patterns(self, new_pattern: CodePattern):
        """新しいパターンを学習"""
        
    def refine_criteria(self, review_session: ReviewSession):
        """レビュー基準を改善"""
```

### 並列処理
```python
class ParallelReviewEngine:
    async def review_multiple_files(self, files: List[str]) -> List[ReviewResult]:
        """独立したファイルを並列レビュー"""
        
    async def chunk_parallel_review(self, large_file: str) -> ReviewResult:
        """大きなファイルをチャンク並列処理"""
```

### 品質メトリクス
```python
class QualityMetrics:
    coverage_percentage: float
    review_depth_score: float
    consistency_score: float
    completeness_score: float
    
    def overall_quality(self) -> float:
        """総合品質スコア"""
```

## 使用例

### セットアップ（一度のみ）
```bash
# 必要なライブラリのインストール
pip install langchain langchain-community langchain-experimental pydantic GitPython PyYAML

# プロジェクト初期化
cd /path/to/your/project
python agent_reviewer.py init

# 対話的セットアップ（LangChainエージェントが質問を管理）
python agent_reviewer.py setup --interactive

# 既存設定からの自動セットアップ
python agent_reviewer.py setup --auto-detect

# 設定の確認・編集
python agent_reviewer.py config --edit
```

### 自動レビュー（継続使用）
```bash
# 基本的な使用方法（LangChainエージェントが自律実行）
python agent_reviewer.py review abc123

# 詳細ログ付きで実行
python agent_reviewer.py review abc123 --verbose

# バックグラウンド実行（非同期処理）
python agent_reviewer.py review abc123 --async

# Git hooksとの統合（完全自動化）
python agent_reviewer.py install-hooks
# 以降、git commit時にLangChainエージェントが自動起動
```

### LangChain統合機能
```bash
# エージェントの思考プロセスを表示
python agent_reviewer.py review abc123 --show-reasoning

# 使用したツールチェーンを表示
python agent_reviewer.py review abc123 --show-tools

# メモリ（学習内容）の表示
python agent_reviewer.py memory --show

# カスタムツールの追加
python agent_reviewer.py tools --add CustomSecurityTool
```

## 期待される出力

エージェントは以下を保証します：

1. **完全性**: 全ファイル・全セクションの確実なレビュー
2. **品質**: 一貫した基準による高品質なレビュー  
3. **追跡可能性**: 詳細な処理ログと進捗記録
4. **回復力**: エラーや中断からの自動回復
5. **学習能力**: 継続的な改善と最適化

このエージェント設計により、人間の介入なしに完全で信頼性の高いコードレビューが実現されます。
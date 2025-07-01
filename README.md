# C言語専用AIエージェント型コードレビューツール

LangChainベースの自律的なC言語コードレビューエージェントです。PDF、Markdown、テキストファイルからコーディング規約を読み込み、完全自動でC言語コードのレビューを実行します。

## 特徴

- 🤖 **LangChain統合**: 自律的なエージェントによる完全自動レビュー
- 📄 **ファイルベース設定**: PDF/MD/TXT形式のコーディング規約ファイルに対応
- 🔍 **C言語特化**: メモリ管理、セキュリティ、パフォーマンスに重点
- 📊 **多様な出力**: JSON、Markdown、HTML形式でのレポート生成
- 🔧 **ローカル完結**: 外部API不要、完全ローカル実行
- ⚡ **高速処理**: 静的解析ツール統合による効率的な解析

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd ai-coding-agent

# 依存関係をインストール
pip install -r requirements.txt

# Ollamaをインストール（LLMエンジン）
# https://ollama.ai/download からインストールし、以下を実行：
ollama pull codellama
```

## 必要なツール

- **Python 3.8+**
- **Ollama** (codellama モデル)
- **cppcheck** (オプション - 静的解析用)
- **Git** (コミット解析用)

## クイックスタート

### 1. セットアップ

初回実行時、またはコーディング規約ファイルを変更・追加する場合に実行します。

```bash
# コーディング規約ファイルでセットアップ（初回または変更時）
python c_agent_reviewer.py setup --standards-files "./docs/coding_standards.pdf,./docs/team_guidelines.md" --project-name "MyProject"

# プロジェクト情報のみ更新する場合（規約ファイルは既存のものを使用）
python c_agent_reviewer.py setup --project-name "MyNewProject"
```

### 2. コードレビュー実行

一度セットアップが完了すれば、コミットハッシュを指定するだけでレビューを実行できます。

```bash
# 特定のコミットをレビュー
python c_agent_reviewer.py review abc123

# 全形式でレポート生成
python c_agent_reviewer.py review abc123 --output all

# サマリーをコンソール表示
python c_agent_reviewer.py review abc123 --show-summary
```

## コマンドリファレンス

### セットアップコマンド

初回実行時、またはコーディング規約ファイルを変更・追加する場合に利用します。`--standards-files`は初回セットアップ時、または新しい規約ファイルを追加する場合に指定します。一度設定すれば、以降のレビュー実行時には不要です。

```bash
# 初回セットアップまたは規約ファイルの追加
python c_agent_reviewer.py setup --standards-files "file1.pdf,file2.md,file3.txt"

# プロジェクト情報のみ更新（規約ファイルは既存のものを使用）
python c_agent_reviewer.py setup --project-name "EmbeddedSystem" --project-type "embedded_system"
```

### レビューコマンド

```bash
# 基本レビュー
python c_agent_reviewer.py review <commit_hash>

# 出力形式指定
python c_agent_reviewer.py review <commit_hash> --output json
python c_agent_reviewer.py review <commit_hash> --output markdown
python c_agent_reviewer.py review <commit_hash> --output html

# 出力ディレクトリ指定
python c_agent_reviewer.py review <commit_hash> --output-dir ./my_reviews
```

### 管理コマンド

```bash
# 設定確認
python c_agent_reviewer.py config

# レポート一覧
python c_agent_reviewer.py list-reports

# HTMLレポートをブラウザで開く
python c_agent_reviewer.py open-report ./review_reports/c_review_abc12345_20250701.html

# 統計情報
python c_agent_reviewer.py stats

# バージョン確認
python c_agent_reviewer.py version
```

## コーディング規約ファイルの形式

### PDF形式
```
C言語コーディング規約

■ セキュリティ
- バッファオーバーフロー対策を実装すること
- 入力値検証を適切に行うこと
- 危険な関数（strcpy, sprintf等）を避けること

■ メモリ管理
- malloc/callocで確保したメモリは必ずfreeすること
- NULLポインタアクセスを防ぐこと
```

### Markdown形式
```markdown
# C言語レビュー観点

## セキュリティ

- [ ] バッファオーバーフローの防止
- [ ] 入力値検証の実装
- [ ] 危険な関数の回避

## メモリ管理

- [ ] メモリリークの防止
- [ ] NULLポインタチェック
```

### テキスト形式
```
セキュリティ観点：
・バッファオーバーフローの防止
・入力値検証の実装

メモリ管理観点：
・メモリリークの防止
・適切なポインタ管理
```

## 出力例

### Markdownレポート
```markdown
# C言語コードレビュー結果

**コミット**: `abc123`
**実行時刻**: 2025-07-01 10:30:00
**対象ファイル**: 3ファイル

## 🔴 Critical Issues

### 1. バッファオーバーフロー脆弱性
**ファイル**: `src/network.c:67`
**問題**: strcpy使用によるバッファオーバーフロー
**修正例**:
```c
strncpy(buffer, input, sizeof(buffer) - 1);
buffer[sizeof(buffer) - 1] = '\0';
```

## アーキテクチャ

```
src/
├── agents/              # エージェント本体
│   └── code_review_agent.py
├── tools/               # レビューツール群
│   ├── coding_standards_loader.py
│   ├── c_code_parser.py
│   ├── c_static_analyzer.py
│   ├── local_git_analyzer.py
│   ├── review_rule_engine.py
│   └── report_generator.py
├── config/              # 設定管理
│   └── config_manager.py
└── reports/             # レポート構造
    └── review_result.py
```

## 高度な使用法

### Git Hooksとの統合

```bash
# pre-commit hookとして設定
echo '#!/bin/bash
python c_agent_reviewer.py review HEAD --show-summary
' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### カスタム設定

```bash
# 詳細ログ出力
python c_agent_reviewer.py --verbose review abc123

# 特定の出力ディレクトリ
python c_agent_reviewer.py review abc123 --output-dir ./reviews/$(date +%Y%m%d)
```

## トラブルシューティング

### よくある問題

1. **Ollamaに接続できない**
   ```bash
   # Ollamaが起動しているか確認
   ollama list
   
   # codelamaモデルをダウンロード
   ollama pull codellama
   ```

2. **cppcheckが見つからない**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install cppcheck
   
   # macOS
   brew install cppcheck
   ```

3. **PDFファイルが読み込めない**
   ```bash
   # PyPDF2の依存関係を確認
   pip install PyPDF2 --upgrade
   ```

## ライセンス

MIT License

## 貢献

プルリクエストやIssueを歓迎します。

## サポート

- [GitHub Issues](https://github.com/your-repo/issues)
- [ドキュメント](./docs/)
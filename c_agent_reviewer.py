#!/usr/bin/env python3
"""
C言語専用AIエージェント型コードレビューツール CLI
"""

import sys
import time
import click
import logging
from pathlib import Path
from typing import List, Optional

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.code_review_agent import CCodeReviewAgent
from src.config.config_manager import ConfigManager
from src.tools.coding_standards_loader import CodingStandardsLoader


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--config-path', default='.code_review_agent', help='設定ディレクトリのパス')
@click.option('--verbose', '-v', is_flag=True, help='詳細ログを表示')
@click.pass_context
def cli(ctx, config_path: str, verbose: bool):
    """C言語専用AIエージェント型コードレビューツール"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config_path
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--standards-files', help='コーディング規約ファイル（カンマ区切りで複数指定可能）')
@click.option('--project-name', help='プロジェクト名')
@click.option('--project-type', default='embedded_system', help='プロジェクトタイプ')
@click.pass_context
def setup(ctx, standards_files: str, project_name: Optional[str], project_type: str):
    """プロジェクトの初期セットアップ"""
    click.echo("🤖 C言語コードレビューエージェントのセットアップを開始します...")
    
    config_path = ctx.obj['config_path']
    config_manager = ConfigManager(config_path)
    
    # プロジェクト情報を更新
    if project_name:
        config_manager.update_project_info(
            project_name=project_name,
            project_type=project_type
        )
        click.echo(f"✓ プロジェクト設定: {project_name} ({project_type})")
    
    click.echo(f"📄 コーディング規約ファイルを処理中...")
    
    try:
        agent = CCodeReviewAgent(config_path)
        
        if standards_files:
            standards_file_list = [f.strip() for f in standards_files.split(',')]
            # 新しいファイルを保存
            for file_path in standards_file_list:
                if not Path(file_path).exists():
                    click.echo(f"❌ ファイルが見つかりません: {file_path}")
                    return
                config_manager.add_coding_standards_file(file_path)
                click.echo(f"  - {file_path} (追加)")
        
        # 設定済みのコーディング規約ファイルを取得
        current_standards_files = config_manager.get_coding_standards_files()
        
        if not current_standards_files:
            click.echo("⚠️ コーディング規約ファイルが設定されていません。`--standards-files`オプションで指定してください。")
            return
        
        click.echo("📄 以下のコーディング規約ファイルを使用します:")
        for file_path in current_standards_files:
            click.echo(f"  - {file_path}")
        
        # セットアップ実行
        success = agent.setup_from_files(current_standards_files)
        
        if success:
            click.echo("🎉 セットアップが完了しました！")
            click.echo(f"設定ディレクトリ: {config_path}")
            click.echo("\n今後は以下のコマンドでレビューを実行できます:")
            click.echo("  python c_agent_reviewer.py review <commit_hash>")
        else:
            click.echo("❌ セットアップに失敗しました")
            
    except Exception as e:
        click.echo(f"❌ エラー: {e}")
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()


@cli.command()
@click.argument('commit_hash')
@click.option('--output', default='all', help='出力形式 (json/markdown/html/all)')
@click.option('--output-dir', help='出力ディレクトリ')
@click.option('--show-summary', is_flag=True, help='サマリーをコンソールに表示')
@click.pass_context
def review(ctx, commit_hash: str, output: str, output_dir: Optional[str], show_summary: bool):
    """指定されたコミットのC言語レビューを実行"""
    click.echo(f"🔍 コミット {commit_hash[:8]} のC言語レビューを開始します...")
    
    config_path = ctx.obj['config_path']
    
    try:
        # エージェントを初期化
        agent = CCodeReviewAgent(config_path)
        
        # 出力ディレクトリを設定
        if output_dir:
            agent.tools[-1].output_dir = Path(output_dir)  # ReportGeneratorToolの出力ディレクトリを変更
        
        start_time = time.time()
        
        # レビュー実行
        with click.progressbar(length=100, label='レビュー実行中') as bar:
            # プログレスバーの更新（実際のエージェント処理では適切な進捗管理が必要）
            for i in range(0, 100, 10):
                time.sleep(0.1)  # 実際の処理時間をシミュレート
                bar.update(10)
        
        result = agent.review_commit(commit_hash, output)
        
        execution_time = time.time() - start_time
        
        if "error" in result:
            click.echo(f"❌ レビューに失敗しました: {result['error']}")
            return
        
        click.echo(f"✓ レビューが完了しました（実行時間: {execution_time:.2f}秒）")
        
        # サマリー表示
        if show_summary:
            click.echo("\n📊 レビュー結果サマリー:")
            click.echo(f"  コミット: {commit_hash}")
            click.echo(f"  ステータス: {result.get('status', 'unknown')}")
        
        # 生成されたファイルの表示
        if 'generated_files' in result:
            click.echo("\n📝 生成されたレポート:")
            for format_type, file_path in result['generated_files'].items():
                click.echo(f"  {format_type.upper()}: {file_path}")
        
    except Exception as e:
        click.echo(f"❌ エラー: {e}")
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()


@cli.command()
@click.pass_context
def config(ctx):
    """現在の設定を表示"""
    config_path = ctx.obj['config_path']
    config_manager = ConfigManager(config_path)
    
    try:
        current_config = config_manager.get_current_config()
        
        click.echo("⚙️ 現在の設定:")
        click.echo(f"設定ディレクトリ: {config_path}")
        
        # プロジェクト設定
        project = current_config.get('project', {}).get('project', {})
        click.echo(f"\nプロジェクト:")
        click.echo(f"  名前: {project.get('name', 'Unknown')}")
        click.echo(f"  タイプ: {project.get('type', 'Unknown')}")
        click.echo(f"  言語: {project.get('language_primary', 'Unknown')}")
        
        # チーム設定
        team = current_config.get('project', {}).get('team', {})
        click.echo(f"\nチーム設定:")
        click.echo(f"  レビュー厳格度: {team.get('review_strictness', 'medium')}")
        standards_files = team.get('coding_standards_files', [])
        if standards_files:
            click.echo(f"  コーディング規約ファイル:")
            for file_path in standards_files:
                click.echo(f"    - {file_path}")
        
        # レビュー観点
        standards = current_config.get('review_standards', {})
        click.echo(f"\nレビュー観点:")
        for category, rules in standards.items():
            click.echo(f"  {category}: {len(rules)}件")
        
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option('--period', default='all', help='期間指定 (all/last-week/last-month)')
@click.pass_context
def list_reports(ctx, period: str):
    """生成されたレポートの一覧を表示"""
    config_path = ctx.obj['config_path']
    
    try:
        from src.tools.report_generator import ReportGeneratorTool
        
        report_generator = ReportGeneratorTool()
        reports = json.loads(report_generator._run("list_reports"))
        
        if not reports:
            click.echo("📄 レポートが見つかりません")
            return
        
        click.echo(f"📄 レビューレポート一覧 ({len(reports)}件)")
        click.echo("-" * 80)
        
        for report in reports[:10]:  # 最新10件を表示
            click.echo(f"📄 {report['filename']}")
            click.echo(f"   コミット: {report['commit_hash']}")
            click.echo(f"   作成日時: {report['created']}")
            click.echo(f"   サイズ: {report['size']:,} bytes")
            click.echo()
        
        if len(reports) > 10:
            click.echo(f"... 他 {len(reports) - 10}件")
        
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.argument('report_path')
@click.pass_context
def open_report(ctx, report_path: str):
    """HTMLレポートをブラウザで開く"""
    import webbrowser
    import os
    
    report_file = Path(report_path)
    
    if not report_file.exists():
        click.echo(f"❌ レポートファイルが見つかりません: {report_path}")
        return
    
    if report_file.suffix.lower() != '.html':
        click.echo(f"❌ HTMLファイルではありません: {report_path}")
        return
    
    try:
        full_path = os.path.abspath(report_path)
        webbrowser.open(f"file://{full_path}")
        click.echo(f"🌐 ブラウザでレポートを開きました: {report_path}")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option('--output-file', help='統計結果の出力ファイル')
@click.pass_context
def stats(ctx, output_file: Optional[str]):
    """レビュー統計情報を表示"""
    try:
        from src.tools.report_generator import ReportGeneratorTool
        import json
        
        report_generator = ReportGeneratorTool()
        stats_result = json.loads(report_generator._run("get_report_stats"))
        
        click.echo("📊 レビュー統計情報:")
        click.echo(f"  総レポート数: {stats_result['total_reports']}件")
        click.echo(f"  総サイズ: {stats_result['total_size_mb']:.2f} MB")
        click.echo(f"  出力ディレクトリ: {stats_result['output_directory']}")
        
        if stats_result['latest_report']:
            latest = stats_result['latest_report']
            click.echo(f"  最新レポート: {latest['filename']} ({latest['created']})")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(stats_result, f, ensure_ascii=False, indent=2)
            click.echo(f"✓ 統計結果を保存しました: {output_file}")
        
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.pass_context
def version(ctx):
    """バージョン情報を表示"""
    click.echo("C言語専用AIエージェント型コードレビューツール")
    click.echo("バージョン: 1.0.0")
    click.echo("LangChain統合版")
    click.echo("\n対応ファイル形式:")
    click.echo("  - コーディング規約: PDF, Markdown (.md), テキスト (.txt)")
    click.echo("  - レビュー対象: C言語 (.c, .h)")
    click.echo("  - 出力形式: JSON, Markdown, HTML")


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n👋 レビューを中断しました")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ 予期しないエラー: {e}")
        sys.exit(1)
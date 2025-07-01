"""
C言語専用AIエージェント型コードレビューツール
LangChainベースの自律的なコードレビューエージェント
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama

from ..tools.coding_standards_loader import CodingStandardsLoader
from ..tools.c_code_parser import CCodeParserTool
from ..tools.c_static_analyzer import CStaticAnalysisTool
from ..tools.review_rule_engine import ReviewRuleEngineTool
from ..tools.local_git_analyzer import LocalGitTool
from ..tools.report_generator import ReportGeneratorTool
from ..config.config_manager import ConfigManager
from ..reports.review_result import CReviewResult


class CCodeReviewAgent:
    """C言語専用LangChainベースのコードレビューエージェント"""
    
    def __init__(self, config_path: str = None, llm_model: str = "codellama"):
        self.config_manager = ConfigManager(config_path)
        self.llm = self._setup_llm(llm_model)
        self.memory = self._setup_memory()
        self.tools = self._setup_tools()
        self.agent = self._create_agent()
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=50,
            early_stopping_method="generate"
        )
        
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _setup_llm(self, model: str) -> ChatOllama:
        """Ollama LLMをセットアップ"""
        return ChatOllama(
            model=model,
            base_url="http://localhost:11434",
            temperature=0.1,
            num_ctx=4096
        )
    
    def _setup_memory(self) -> ConversationBufferWindowMemory:
        """エージェントのメモリをセットアップ"""
        return ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
    
    def _setup_tools(self) -> List[Any]:
        """C言語レビュー専用ツールをセットアップ"""
        return [
            LocalGitTool(),
            CCodeParserTool(), 
            CStaticAnalysisTool(),
            ReviewRuleEngineTool(self.config_manager),
            ReportGeneratorTool()
        ]
    
    def _create_agent(self):
        """構造化チャットエージェントを作成"""
        system_prompt = """
        あなたは経験豊富なC言語コードレビューエージェントです。
        以下の能力を持っています:

        ## 基本方針
        1. **完全性の保証**: 全ファイル・全セクションを確実にレビュー
        2. **自律的判断**: 設定に基づいて適切なルールを自動選択・適用
        3. **C言語特化**: メモリ管理、セキュリティ、パフォーマンスに重点
        4. **コンテキスト認識**: ファイルの種類・重要度に応じた適切な深度でレビュー

        ## 利用可能なツール
        - local_git_analyzer: ローカルGitリポジトリの解析
        - c_code_parser: C言語コードの構造解析
        - c_static_analyzer: 静的解析ツール(cppcheck等)の実行
        - review_rule_engine: レビュールールの評価・適用
        - report_generator: 構造化されたレポートの生成

        ## レビュープロセス
        1. **Git解析**: 変更内容を分析し、C言語ファイルを特定
        2. **計画立案**: ファイルの重要度とレビュー戦略を決定
        3. **静的解析**: cppcheckやカスタム解析を実行
        4. **詳細レビュー**: 各ファイルを段階的に詳細レビュー
        5. **品質検証**: レビューの完全性・一貫性をチェック
        6. **レポート生成**: 構造化された結果を出力

        ## C言語特有の観点
        - バッファオーバーフロー対策
        - メモリリークの防止
        - NULLポインタアクセスのチェック
        - 危険な関数の使用回避
        - 適切なエラーハンドリング

        必ず全てのC言語ファイルとセクションを完全にレビューしてください。
        問題を発見した場合は、具体的なコード例と修正提案を含めて報告してください。
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return create_structured_chat_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    def setup_from_files(self, review_standards_files: List[str]) -> bool:
        """レビュー観点ファイルからセットアップ"""
        try:
            loader = CodingStandardsLoader()
            
            # 各ファイルから観点を読み込み
            all_standards = {}
            for file_path in review_standards_files:
                self.logger.info(f"Loading standards from: {file_path}")
                standards = loader.load_standards_from_file(file_path)
                all_standards.update(standards)
            
            # 設定に保存
            self.config_manager.save_review_standards(all_standards)
            self.logger.info("Setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False
    
    def review_commit(self, commit_hash: str, output_format: str = "all") -> Dict[str, str]:
        """指定されたコミットの完全なC言語レビューを実行"""
        try:
            self.logger.info(f"Starting C code review for commit: {commit_hash}")
            
            # エージェントへの指示
            review_instruction = f"""
            コミット {commit_hash} の完全なC言語コードレビューを実行してください。

            手順:
            1. local_git_analyzer でコミットの変更内容を解析し、C言語ファイル(.c, .h)を特定
            2. 各C言語ファイルの重要度とレビュー戦略を決定
            3. c_static_analyzer で静的解析を実行
            4. c_code_parser で詳細な構造解析
            5. review_rule_engine で設定されたルールを評価
            6. 全ファイルの完全性を検証
            7. report_generator で構造化された結果を生成

            重点項目:
            - セキュリティ: バッファオーバーフロー、入力値検証
            - メモリ管理: メモリリーク、ダブルフリー、NULL pointer
            - パフォーマンス: ループ効率、関数呼び出しコスト
            - コード品質: 可読性、保守性、エラーハンドリング

            出力形式: {output_format}
            """
            
            # エージェント実行
            result = self.executor.run(review_instruction)
            
            # 結果の解析と整理
            return self._parse_agent_result(result, commit_hash, output_format)
            
        except Exception as e:
            self.logger.error(f"Review failed: {e}")
            return {"error": str(e)}
    
    def _parse_agent_result(self, result: str, commit_hash: str, output_format: str) -> Dict[str, str]:
        """エージェントの結果を解析して適切な形式で返す"""
        try:
            # 結果をJSONとして解析を試行
            if isinstance(result, str):
                # テキスト結果の場合は構造化する
                return {
                    "commit_hash": commit_hash,
                    "status": "completed",
                    "summary": result,
                    "format": output_format
                }
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"Failed to parse agent result: {e}")
            return {
                "commit_hash": commit_hash,
                "status": "error", 
                "error": str(e),
                "raw_result": str(result)
            }
    
    def show_config(self) -> Dict[str, Any]:
        """現在の設定を表示"""
        return self.config_manager.get_current_config()
    
    def get_memory_summary(self) -> str:
        """エージェントのメモリ（学習内容）の要約を取得"""
        chat_history = self.memory.chat_memory.messages
        if not chat_history:
            return "No memory data available"
        
        return f"Memory contains {len(chat_history)} messages from recent interactions"
    
    def clear_memory(self):
        """エージェントのメモリをクリア"""
        self.memory.clear()
        self.logger.info("Agent memory cleared")
"""
設定管理システム
プロジェクト設定とレビュー観点の管理
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path(".code_review_agent")
        self.config_path.mkdir(exist_ok=True)
        
        self.project_config_file = self.config_path / "project_config.yaml"
        self.review_standards_file = self.config_path / "review_standards.json"
        self.agent_config_file = self.config_path / "agent_config.yaml"
        
        self.logger = logging.getLogger(__name__)
        
        # デフォルト設定を初期化
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """デフォルト設定を初期化"""
        # プロジェクト設定のデフォルト
        if not self.project_config_file.exists():
            default_project_config = {
                "project": {
                    "name": "C Project",
                    "type": "embedded_system",
                    "language_primary": "c",
                    "languages_secondary": ["h"],
                    "description": "C language project"
                },
                "team": {
                    "coding_standards_files": [],
                    "review_strictness": "medium",
                    "domain_expertise": ["embedded", "systems_programming"]
                },
                "auto_detected": {
                    "existing_linters": [],
                    "build_system": "make",
                    "test_framework": "unknown"
                }
            }
            self.save_project_config(default_project_config)
        
        # エージェント設定のデフォルト
        if not self.agent_config_file.exists():
            default_agent_config = {
                "agent_behavior": {
                    "max_iterations": 50,
                    "timeout_per_file": 300,
                    "chunk_size": 50,
                    "quality_threshold": 0.8,
                    "auto_learning": True
                },
                "llm_config": {
                    "model": "codellama",
                    "base_url": "http://localhost:11434",
                    "temperature": 0.1,
                    "context_window": 4096
                },
                "output": {
                    "format": "all",
                    "include_suggestions": True,
                    "include_code_examples": True,
                    "verbosity": "detailed"
                },
                "tools": {
                    "enable_cppcheck": True,
                    "enable_custom_analysis": True,
                    "enable_git_analysis": True
                }
            }
            self.save_agent_config(default_agent_config)
    
    def save_project_config(self, config: Dict[str, Any]):
        """プロジェクト設定を保存"""
        try:
            with open(self.project_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info("Project config saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save project config: {e}")
            raise
    
    def load_project_config(self) -> Dict[str, Any]:
        """プロジェクト設定を読み込み"""
        try:
            if not self.project_config_file.exists():
                return {}
            
            with open(self.project_config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to load project config: {e}")
            return {}
    
    def save_agent_config(self, config: Dict[str, Any]):
        """エージェント設定を保存"""
        try:
            with open(self.agent_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info("Agent config saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save agent config: {e}")
            raise
    
    def load_agent_config(self) -> Dict[str, Any]:
        """エージェント設定を読み込み"""
        try:
            if not self.agent_config_file.exists():
                return {}
            
            with open(self.agent_config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to load agent config: {e}")
            return {}
    
    def save_review_standards(self, standards: Dict[str, List[Dict]]):
        """レビュー観点を保存"""
        try:
            with open(self.review_standards_file, 'w', encoding='utf-8') as f:
                json.dump(standards, f, ensure_ascii=False, indent=2)
            self.logger.info("Review standards saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save review standards: {e}")
            raise
    
    def get_review_standards(self) -> Dict[str, List[Dict]]:
        """レビュー観点を取得"""
        try:
            if not self.review_standards_file.exists():
                return self._get_default_review_standards()
            
            with open(self.review_standards_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load review standards: {e}")
            return self._get_default_review_standards()
    
    def _get_default_review_standards(self) -> Dict[str, List[Dict]]:
        """デフォルトのレビュー観点を取得"""
        return {
            "security": [
                {
                    "description": "バッファオーバーフローの防止",
                    "priority": "high",
                    "applicable_files": ["*.c", "*.h"],
                    "category": "security"
                },
                {
                    "description": "入力値検証の実装",
                    "priority": "high", 
                    "applicable_files": ["*.c"],
                    "category": "security"
                },
                {
                    "description": "危険な関数の回避",
                    "priority": "high",
                    "applicable_files": ["*.c"],
                    "category": "security"
                }
            ],
            "memory_management": [
                {
                    "description": "メモリリークの防止",
                    "priority": "high",
                    "applicable_files": ["*.c"],
                    "category": "memory_management"
                },
                {
                    "description": "NULLポインタアクセスの防止",
                    "priority": "high",
                    "applicable_files": ["*.c"],
                    "category": "memory_management"
                },
                {
                    "description": "適切なポインタ管理",
                    "priority": "medium",
                    "applicable_files": ["*.c", "*.h"],
                    "category": "memory_management"
                }
            ],
            "performance": [
                {
                    "description": "ループ効率の最適化",
                    "priority": "medium",
                    "applicable_files": ["*.c"],
                    "category": "performance"
                },
                {
                    "description": "関数呼び出しコストの考慮",
                    "priority": "medium",
                    "applicable_files": ["*.c"],
                    "category": "performance"
                }
            ],
            "code_quality": [
                {
                    "description": "適切なコメントの記述",
                    "priority": "low",
                    "applicable_files": ["*.c", "*.h"],
                    "category": "code_quality"
                },
                {
                    "description": "マジックナンバーの回避",
                    "priority": "medium",
                    "applicable_files": ["*.c"],
                    "category": "code_quality"
                }
            ]
        }
    
    @lru_cache(maxsize=128)
    def get_rules_for_file(self, file_path: str) -> List[Dict]:
        """ファイルに適用すべきルールをキャッシュ付きで取得"""
        import fnmatch
        
        standards = self.get_review_standards()
        applicable_rules = []
        
        for category, rules in standards.items():
            for rule in rules:
                applicable_files = rule.get("applicable_files", ["*"])
                
                # ファイルパターンマッチング
                for pattern in applicable_files:
                    if fnmatch.fnmatch(file_path, pattern):
                        applicable_rules.append(rule)
                        break
        
        return applicable_rules
    
    def get_current_config(self) -> Dict[str, Any]:
        """現在の全設定を取得"""
        return {
            "project": self.load_project_config(),
            "agent": self.load_agent_config(),
            "review_standards": self.get_review_standards(),
            "config_path": str(self.config_path)
        }
    
    def update_project_info(self, project_name: str = None, project_type: str = None, **kwargs):
        """プロジェクト情報を更新"""
        config = self.load_project_config()
        
        if project_name:
            config.setdefault("project", {})["name"] = project_name
        
        if project_type:
            config.setdefault("project", {})["type"] = project_type
        
        # その他の設定項目を更新
        for key, value in kwargs.items():
            if "." in key:
                # ネストしたキー（例：team.review_strictness）
                parts = key.split(".")
                current = config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            else:
                config[key] = value
        
        self.save_project_config(config)
    
    def add_coding_standards_file(self, file_path: str):
        """コーディング規約ファイルを追加"""
        config = self.load_project_config()
        files = config.setdefault("team", {}).setdefault("coding_standards_files", [])
        
        if file_path not in files:
            files.append(file_path)
            self.save_project_config(config)
            self.logger.info(f"Added coding standards file: {file_path}")
    
    def get_coding_standards_files(self) -> List[str]:
        """コーディング規約ファイル一覧を取得"""
        config = self.load_project_config()
        return config.get("team", {}).get("coding_standards_files", [])
    
    def update_agent_setting(self, setting_path: str, value: Any):
        """エージェント設定を更新"""
        config = self.load_agent_config()
        
        # ネストしたキーを処理
        parts = setting_path.split(".")
        current = config
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        
        self.save_agent_config(config)
        self.logger.info(f"Updated agent setting: {setting_path} = {value}")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """LLM設定を取得"""
        agent_config = self.load_agent_config()
        return agent_config.get("llm_config", {
            "model": "codellama",
            "base_url": "http://localhost:11434",
            "temperature": 0.1
        })
    
    def get_output_config(self) -> Dict[str, Any]:
        """出力設定を取得"""
        agent_config = self.load_agent_config()
        return agent_config.get("output", {
            "format": "all",
            "include_suggestions": True,
            "include_code_examples": True
        })
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """ツールが有効かチェック"""
        agent_config = self.load_agent_config()
        tools_config = agent_config.get("tools", {})
        return tools_config.get(f"enable_{tool_name}", True)
    
    def export_config(self, export_path: str):
        """設定をエクスポート"""
        export_data = self.get_current_config()
        
        export_file = Path(export_path)
        with open(export_file, 'w', encoding='utf-8') as f:
            if export_file.suffix.lower() == '.json':
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"Configuration exported to: {export_path}")
    
    def import_config(self, import_path: str):
        """設定をインポート"""
        import_file = Path(import_path)
        
        if not import_file.exists():
            raise FileNotFoundError(f"Config file not found: {import_path}")
        
        with open(import_file, 'r', encoding='utf-8') as f:
            if import_file.suffix.lower() == '.json':
                import_data = json.load(f)
            else:
                import_data = yaml.safe_load(f)
        
        # 各設定を更新
        if "project" in import_data:
            self.save_project_config(import_data["project"])
        
        if "agent" in import_data:
            self.save_agent_config(import_data["agent"])
        
        if "review_standards" in import_data:
            self.save_review_standards(import_data["review_standards"])
        
        self.logger.info(f"Configuration imported from: {import_path}")
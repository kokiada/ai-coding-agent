"""
ローカルGit解析ツール
コミットの変更内容を解析してC言語ファイルを特定
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from git import Repo, GitCommandError
from langchain.tools import BaseTool


class LocalGitTool(BaseTool):
    """ローカルGitリポジトリの解析ツール"""
    
    name = "local_git_analyzer"
    description = "ローカルGitリポジトリの解析（外部通信なし）"
    
    def __init__(self, repo_path: str = "."):
        super().__init__()
        self.repo_path = repo_path
        self.logger = logging.getLogger(__name__)
        
        try:
            self.repo = Repo(repo_path)
        except Exception as e:
            self.logger.error(f"Failed to initialize Git repository: {e}")
            self.repo = None
    
    def _run(self, action: str, commit_hash: str = None, file_path: str = None) -> str:
        """Git操作を実行"""
        if not self.repo:
            return json.dumps({"error": "Git repository not initialized"})
        
        try:
            if action == "get_commit_changes":
                if not commit_hash:
                    return json.dumps({"error": "commit_hash required for get_commit_changes"})
                changes = self._get_commit_changes(commit_hash)
                return json.dumps(changes, ensure_ascii=False, indent=2)
            
            elif action == "get_file_content":
                if not file_path:
                    return json.dumps({"error": "file_path required for get_file_content"})
                content = self._get_file_content(file_path, commit_hash)
                return content
            
            elif action == "list_c_files":
                c_files = self._list_c_files()
                return json.dumps(c_files, ensure_ascii=False, indent=2)
            
            elif action == "get_recent_commits":
                commits = self._get_recent_commits()
                return json.dumps(commits, ensure_ascii=False, indent=2)
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
                
        except Exception as e:
            self.logger.error(f"Git operation failed: {e}")
            return json.dumps({"error": str(e)})
    
    def _get_commit_changes(self, commit_hash: str) -> Dict:
        """指定コミットの変更内容を取得"""
        try:
            commit = self.repo.commit(commit_hash)
            
            changes = {
                "commit_info": {
                    "hash": commit_hash,
                    "short_hash": commit_hash[:8],
                    "author": str(commit.author),
                    "author_email": commit.author.email,
                    "committer": str(commit.committer),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                    "parents": [p.hexsha for p in commit.parents]
                },
                "c_files": {
                    "modified": [],
                    "added": [],
                    "deleted": [],
                    "renamed": []
                },
                "file_changes": {},
                "stats": {
                    "total_files": 0,
                    "c_files_count": 0,
                    "total_additions": 0,
                    "total_deletions": 0
                }
            }
            
            # 親コミットとの差分を取得
            parent = commit.parents[0] if commit.parents else None
            diff = commit.diff(parent)
            
            for item in diff:
                file_path = item.a_path or item.b_path
                
                # C言語ファイルのみを対象
                if not self._is_c_file(file_path):
                    continue
                
                changes["stats"]["total_files"] += 1
                changes["stats"]["c_files_count"] += 1
                
                # 変更タイプ別の分類
                if item.change_type == 'M':  # Modified
                    changes["c_files"]["modified"].append(file_path)
                elif item.change_type == 'A':  # Added
                    changes["c_files"]["added"].append(file_path)
                elif item.change_type == 'D':  # Deleted
                    changes["c_files"]["deleted"].append(file_path)
                elif item.change_type == 'R':  # Renamed
                    changes["c_files"]["renamed"].append({
                        "old_path": item.a_path,
                        "new_path": item.b_path
                    })
                
                # ファイルごとの詳細な変更情報
                file_change_info = {
                    "change_type": item.change_type,
                    "old_path": item.a_path,
                    "new_path": item.b_path,
                    "added_lines": 0,
                    "removed_lines": 0,
                    "diff_hunks": []
                }
                
                # 差分の詳細情報を取得
                try:
                    if item.diff:
                        diff_text = item.diff.decode('utf-8')
                        file_change_info["diff_text"] = diff_text
                        
                        # 追加・削除行数をカウント
                        for line in diff_text.split('\n'):
                            if line.startswith('+') and not line.startswith('+++'):
                                file_change_info["added_lines"] += 1
                                changes["stats"]["total_additions"] += 1
                            elif line.startswith('-') and not line.startswith('---'):
                                file_change_info["removed_lines"] += 1
                                changes["stats"]["total_deletions"] += 1
                        
                        # ハンク情報を抽出
                        file_change_info["diff_hunks"] = self._extract_diff_hunks(diff_text)
                
                except UnicodeDecodeError:
                    file_change_info["diff_text"] = "[Binary file or encoding error]"
                
                changes["file_changes"][file_path] = file_change_info
            
            return changes
            
        except GitCommandError as e:
            raise ValueError(f"Invalid commit hash: {commit_hash}")
        except Exception as e:
            raise ValueError(f"Failed to get commit changes: {str(e)}")
    
    def _get_file_content(self, file_path: str, commit_hash: str = None) -> str:
        """指定ファイルの内容を取得"""
        try:
            if commit_hash:
                # 特定のコミットでのファイル内容
                commit = self.repo.commit(commit_hash)
                try:
                    blob = commit.tree[file_path]
                    return blob.data_stream.read().decode('utf-8')
                except KeyError:
                    raise ValueError(f"File {file_path} not found in commit {commit_hash}")
            else:
                # 現在のワーキングディレクトリのファイル内容
                full_path = Path(self.repo_path) / file_path
                if not full_path.exists():
                    raise ValueError(f"File {file_path} not found in working directory")
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
        except UnicodeDecodeError:
            raise ValueError(f"File {file_path} is binary or has encoding issues")
    
    def _list_c_files(self) -> List[Dict]:
        """リポジトリ内のC言語ファイル一覧を取得"""
        c_files = []
        
        try:
            # Git管理下のファイルのみを対象
            for item in self.repo.index.entries:
                file_path = item[0]
                if self._is_c_file(file_path):
                    full_path = Path(self.repo_path) / file_path
                    
                    file_info = {
                        "path": file_path,
                        "size": full_path.stat().st_size if full_path.exists() else 0,
                        "modified_time": datetime.fromtimestamp(
                            full_path.stat().st_mtime
                        ).isoformat() if full_path.exists() else None
                    }
                    c_files.append(file_info)
            
        except Exception as e:
            self.logger.warning(f"Failed to list files from index: {e}")
            # フォールバック: ファイルシステムから検索
            repo_path = Path(self.repo_path)
            for pattern in ["**/*.c", "**/*.h"]:
                for file_path in repo_path.glob(pattern):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(repo_path)
                        c_files.append({
                            "path": str(relative_path),
                            "size": file_path.stat().st_size,
                            "modified_time": datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat()
                        })
        
        return c_files
    
    def _get_recent_commits(self, limit: int = 10) -> List[Dict]:
        """最近のコミット一覧を取得"""
        commits = []
        
        try:
            for commit in self.repo.iter_commits(max_count=limit):
                commit_info = {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                    "c_files_changed": self._count_c_files_in_commit(commit)
                }
                commits.append(commit_info)
        
        except Exception as e:
            self.logger.error(f"Failed to get recent commits: {e}")
        
        return commits
    
    def _is_c_file(self, file_path: str) -> bool:
        """C言語ファイルかどうかを判定"""
        if not file_path:
            return False
        
        c_extensions = ['.c', '.h', '.cc', '.cpp', '.cxx', '.hpp']
        return any(file_path.lower().endswith(ext) for ext in c_extensions)
    
    def _count_c_files_in_commit(self, commit) -> int:
        """コミット内のC言語ファイル数を数える"""
        try:
            parent = commit.parents[0] if commit.parents else None
            diff = commit.diff(parent)
            
            c_file_count = 0
            for item in diff:
                file_path = item.a_path or item.b_path
                if self._is_c_file(file_path):
                    c_file_count += 1
            
            return c_file_count
        except Exception:
            return 0
    
    def _extract_diff_hunks(self, diff_text: str) -> List[Dict]:
        """差分からハンク情報を抽出"""
        hunks = []
        current_hunk = None
        
        for line in diff_text.split('\n'):
            if line.startswith('@@'):
                # 新しいハンクの開始
                if current_hunk:
                    hunks.append(current_hunk)
                
                # ハンク情報を解析
                import re
                hunk_match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if hunk_match:
                    current_hunk = {
                        "old_start": int(hunk_match.group(1)),
                        "old_count": int(hunk_match.group(2)) if hunk_match.group(2) else 1,
                        "new_start": int(hunk_match.group(3)),
                        "new_count": int(hunk_match.group(4)) if hunk_match.group(4) else 1,
                        "context": line,
                        "changes": []
                    }
            elif current_hunk and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                # 変更内容を記録
                change_type = 'context' if line.startswith(' ') else ('addition' if line.startswith('+') else 'deletion')
                current_hunk["changes"].append({
                    "type": change_type,
                    "content": line[1:]  # 先頭の+/-/ を除去
                })
        
        # 最後のハンクを追加
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
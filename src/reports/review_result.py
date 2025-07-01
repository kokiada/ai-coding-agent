"""
レビュー結果のデータ構造定義
C言語レビュー結果の完全な構造
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CReviewIssue(BaseModel):
    """C言語レビュー問題の詳細構造"""
    file_path: str = Field(description="指摘ファイルのパス")
    line_number: Optional[int] = Field(description="指摘箇所の行番号")
    column_number: Optional[int] = Field(description="指摘箇所の列番号")
    function_name: Optional[str] = Field(description="指摘箇所の関数名")
    rule_description: Optional[str] = Field(description="適用されたレビュー観点")
    category: str = Field(description="問題カテゴリ（security/performance/quality等）")
    severity: str = Field(description="重要度（critical/high/medium/low）")
    message: str = Field(description="問題の詳細説明")
    suggestion: Optional[str] = Field(description="具体的な改善提案")
    code_snippet: Optional[str] = Field(description="問題のあるコード抜粋")
    fixed_code_example: Optional[str] = Field(description="修正例のコード")
    tool_source: Optional[str] = Field(description="問題を検出したツール名")
    confidence: Optional[float] = Field(description="検出の信頼度（0.0-1.0）")


class CFileAnalysis(BaseModel):
    """ファイル別解析結果"""
    file_path: str
    language: str = "c"
    line_count: int = 0
    function_count: int = 0
    complexity_score: float = 0.0
    issues: List[CReviewIssue] = []
    analysis_time_ms: float = 0.0


class CReviewMetrics(BaseModel):
    """レビューメトリクス"""
    overall_quality_score: float = Field(description="総合品質スコア (0-100)")
    complexity_score: float = Field(description="複雑度スコア")
    maintainability_score: float = Field(description="保守性スコア")
    security_score: float = Field(description="セキュリティスコア")
    performance_score: float = Field(description="パフォーマンススコア")


class CReviewSummary(BaseModel):
    """レビューサマリー"""
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_issues: int = 0
    issues_by_severity: Dict[str, int] = Field(default_factory=dict)
    issues_by_category: Dict[str, int] = Field(default_factory=dict)
    files_with_issues: int = 0
    clean_files: int = 0


class CReviewResult(BaseModel):
    """C言語レビュー結果の完全な構造"""
    
    # 基本情報
    commit_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tool_version: str = "1.0.0"
    
    # レビュー対象
    reviewed_files: List[str] = Field(description="レビュー対象のCファイル一覧")
    total_lines_reviewed: int = 0
    
    # 問題リスト
    issues: List[CReviewIssue] = []
    
    # ファイル別解析結果
    file_analyses: List[CFileAnalysis] = []
    
    # メトリクス
    metrics: CReviewMetrics = Field(default_factory=CReviewMetrics)
    
    # サマリー
    summary: CReviewSummary = Field(default_factory=CReviewSummary)
    
    # 推奨事項
    critical_recommendations: List[str] = Field(description="緊急対応推奨事項")
    general_recommendations: List[str] = Field(description="一般的な改善推奨")
    
    # 適用されたレビュー観点
    applied_review_points: List[str] = Field(description="適用されたレビュー観点一覧")
    
    # 実行情報
    execution_time_ms: float = 0.0
    tools_used: List[str] = []
    
    # エラー情報
    errors: List[str] = []
    warnings: List[str] = []
    
    def calculate_summary(self):
        """サマリー情報を計算"""
        self.summary.total_files = len(self.reviewed_files)
        self.summary.total_lines = self.total_lines_reviewed
        self.summary.total_issues = len(self.issues)
        
        # 重要度別集計
        severity_counts = {}
        category_counts = {}
        
        for issue in self.issues:
            # 重要度別
            severity = issue.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # カテゴリ別
            category = issue.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        self.summary.issues_by_severity = severity_counts
        self.summary.issues_by_category = category_counts
        
        # 問題のあるファイル数を計算
        files_with_issues = set()
        for issue in self.issues:
            files_with_issues.add(issue.file_path)
        
        self.summary.files_with_issues = len(files_with_issues)
        self.summary.clean_files = self.summary.total_files - self.summary.files_with_issues
    
    def calculate_metrics(self):
        """メトリクスを計算"""
        if not self.issues:
            self.metrics.overall_quality_score = 100.0
            self.metrics.security_score = 100.0
            return
        
        # 重要度に基づく重み付きスコア計算
        severity_weights = {
            'critical': 10,
            'high': 5,
            'medium': 2,
            'low': 1
        }
        
        total_weight = 0
        for issue in self.issues:
            weight = severity_weights.get(issue.severity, 1)
            total_weight += weight
        
        # 基本スコア計算（問題数に基づく）
        base_score = max(0, 100 - (total_weight * 2))  # 重み付き問題数から減点
        
        self.metrics.overall_quality_score = base_score
        
        # カテゴリ別スコア計算
        security_issues = len([i for i in self.issues if i.category == 'security'])
        performance_issues = len([i for i in self.issues if i.category == 'performance'])
        
        self.metrics.security_score = max(0, 100 - (security_issues * 15))
        self.metrics.performance_score = max(0, 100 - (performance_issues * 10))
        
        # 複雑度スコア（ファイル解析結果から）
        if self.file_analyses:
            avg_complexity = sum(f.complexity_score for f in self.file_analyses) / len(self.file_analyses)
            self.metrics.complexity_score = max(0, 100 - avg_complexity)
        else:
            self.metrics.complexity_score = 100.0
        
        # 保守性スコア（問題数と複雑度から）
        maintainability_penalty = len(self.issues) * 3 + (100 - self.metrics.complexity_score) * 0.5
        self.metrics.maintainability_score = max(0, 100 - maintainability_penalty)
    
    def add_issue(self, issue: CReviewIssue):
        """問題を追加"""
        self.issues.append(issue)
    
    def add_file_analysis(self, analysis: CFileAnalysis):
        """ファイル解析結果を追加"""
        self.file_analyses.append(analysis)
        if analysis.file_path not in self.reviewed_files:
            self.reviewed_files.append(analysis.file_path)
        self.total_lines_reviewed += analysis.line_count
    
    def add_recommendation(self, recommendation: str, is_critical: bool = False):
        """推奨事項を追加"""
        if is_critical:
            self.critical_recommendations.append(recommendation)
        else:
            self.general_recommendations.append(recommendation)
    
    def add_applied_review_point(self, point: str):
        """適用されたレビュー観点を追加"""
        if point not in self.applied_review_points:
            self.applied_review_points.append(point)
    
    def add_error(self, error: str):
        """エラーを追加"""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """警告を追加"""
        self.warnings.append(warning)
    
    def finalize(self):
        """レビュー結果を最終化（サマリーとメトリクスを計算）"""
        self.calculate_summary()
        self.calculate_metrics()
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """シンプルな辞書形式に変換（JSON出力用）"""
        return {
            "commit_hash": self.commit_hash,
            "timestamp": self.timestamp,
            "reviewed_files": self.reviewed_files,
            "total_lines_reviewed": self.total_lines_reviewed,
            "issues": [
                {
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "function_name": issue.function_name,
                    "category": issue.category,
                    "severity": issue.severity,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "code_snippet": issue.code_snippet,
                    "fixed_code_example": issue.fixed_code_example
                }
                for issue in self.issues
            ],
            "summary": self.summary.dict(),
            "metrics": self.metrics.dict(),
            "critical_recommendations": self.critical_recommendations,
            "general_recommendations": self.general_recommendations,
            "applied_review_points": self.applied_review_points,
            "errors": self.errors,
            "warnings": self.warnings
        }
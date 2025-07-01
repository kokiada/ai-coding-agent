"""
コーディング規約ファイルの読み込みと処理
PDF, Markdown, テキストファイルからレビュー観点を抽出
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

import PyPDF2
import markdown
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


class CodingStandardsLoader:
    """コーディング規約ファイルの読み込みと解析"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.txt', '.md']
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", ".", " "]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_standards_from_file(self, file_path: str) -> Dict[str, List[Dict]]:
        """ファイルからコーディング規約を読み込み"""
        if not self._is_supported_format(file_path):
            raise ValueError(f"Unsupported file format: {file_path}")
        
        self.logger.info(f"Loading standards from: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            content = self._extract_from_pdf(file_path)
        elif file_ext == '.md':
            content = self._extract_from_markdown(file_path)
        elif file_ext == '.txt':
            content = self._extract_from_text(file_path)
        
        # コンテンツを解析して構造化
        structured_standards = self._parse_standards_content(content)
        
        return structured_standards
    
    def _is_supported_format(self, file_path: str) -> bool:
        """対応ファイル形式かチェック"""
        return any(file_path.lower().endswith(fmt) for fmt in self.supported_formats)
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """PDFからテキストを抽出"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            self.logger.error(f"Failed to read PDF {file_path}: {e}")
            raise
    
    def _extract_from_markdown(self, file_path: str) -> str:
        """Markdownファイルからテキストを抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            
            # MarkdownをHTMLに変換してからテキスト抽出
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()
        except Exception as e:
            self.logger.error(f"Failed to read Markdown {file_path}: {e}")
            raise
    
    def _extract_from_text(self, file_path: str) -> str:
        """テキストファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Failed to read text file {file_path}: {e}")
            raise
    
    def _parse_standards_content(self, content: str) -> Dict[str, List[Dict]]:
        """コンテンツを解析してレビュー観点を構造化"""
        standards = {
            "security": [],
            "memory_management": [],
            "performance": [],
            "code_quality": [],
            "error_handling": [],
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
            category = self._detect_category(line)
            if category:
                current_category = category
                continue
            
            # レビュー観点として認識できる行の処理
            if self._is_review_point(line):
                point = self._clean_review_point(line)
                if point:
                    standards[current_category].append({
                        "description": point,
                        "priority": self._determine_priority(point),
                        "applicable_files": ["*.c", "*.h"],
                        "category": current_category
                    })
        
        # 空のカテゴリを削除
        return {k: v for k, v in standards.items() if v}
    
    def _detect_category(self, line: str) -> str:
        """行からカテゴリを検出"""
        line_lower = line.lower()
        
        if any(keyword in line_lower for keyword in [
            'セキュリティ', 'security', 'セキュリティー', '脆弱性'
        ]):
            return "security"
        elif any(keyword in line_lower for keyword in [
            'メモリ', 'memory', 'メモリー', 'malloc', 'free'
        ]):
            return "memory_management"
        elif any(keyword in line_lower for keyword in [
            'パフォーマンス', 'performance', '性能', '最適化', 'optimization'
        ]):
            return "performance"
        elif any(keyword in line_lower for keyword in [
            '品質', 'quality', 'コード品質', 'code quality'
        ]):
            return "code_quality"
        elif any(keyword in line_lower for keyword in [
            'エラー', 'error', 'エラーハンドリング', 'error handling', '例外'
        ]):
            return "error_handling"
        
        return None
    
    def _is_review_point(self, line: str) -> bool:
        """レビュー観点として認識すべき行かチェック"""
        # リスト項目のマーカー
        list_markers = ['-', '*', '•', '・', '○', '●']
        
        # 行の最初がリストマーカーで始まるかチェック
        if any(line.startswith(marker + ' ') for marker in list_markers):
            return True
        
        # 番号付きリスト
        if re.match(r'^\d+[.\)]\s', line):
            return True
        
        # チェックボックス形式
        if re.match(r'^- \[[ x]\]', line):
            return True
        
        # 「〜すること」「〜べき」「〜する」などの指示形式
        directive_patterns = [
            r'.*すること$', r'.*べき$', r'.*する$', r'.*してください$',
            r'.*を確認', r'.*をチェック', r'.*を検証'
        ]
        if any(re.search(pattern, line) for pattern in directive_patterns):
            return True
        
        return False
    
    def _clean_review_point(self, line: str) -> str:
        """レビュー観点のテキストをクリーンアップ"""
        # リストマーカーを除去
        line = re.sub(r'^[-*•・○●]\s*', '', line)
        line = re.sub(r'^\d+[.\)]\s*', '', line)
        line = re.sub(r'^- \[[ x]\]\s*', '', line)
        
        return line.strip()
    
    def _determine_priority(self, point: str) -> str:
        """レビュー観点の優先度を判定"""
        point_lower = point.lower()
        
        # 高優先度キーワード
        high_priority_keywords = [
            'バッファオーバーフロー', 'buffer overflow', 'セキュリティ', 'security',
            'メモリリーク', 'memory leak', 'null pointer', 'ヌルポインタ',
            '危険', 'danger', 'critical', 'クリティカル'
        ]
        
        # 中優先度キーワード
        medium_priority_keywords = [
            'パフォーマンス', 'performance', '最適化', 'optimization',
            'エラーハンドリング', 'error handling', '例外処理'
        ]
        
        if any(keyword in point_lower for keyword in high_priority_keywords):
            return "high"
        elif any(keyword in point_lower for keyword in medium_priority_keywords):
            return "medium"
        else:
            return "low"
    
    def create_vectorstore(self, standards: Dict[str, List[Dict]]) -> FAISS:
        """レビュー観点からベクトルストアを作成"""
        try:
            # 全ての観点をテキストとして結合
            documents = []
            for category, points in standards.items():
                for point in points:
                    doc_text = f"カテゴリ: {category}\n説明: {point['description']}\n優先度: {point['priority']}"
                    documents.append(doc_text)
            
            if not documents:
                raise ValueError("No standards documents to process")
            
            # テキストを分割
            splits = self.text_splitter.create_documents(documents)
            
            # ベクトルストアを作成
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            vectorstore = FAISS.from_documents(splits, embeddings)
            
            return vectorstore
            
        except Exception as e:
            self.logger.error(f"Failed to create vectorstore: {e}")
            raise
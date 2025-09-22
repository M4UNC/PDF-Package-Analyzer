#!/usr/bin/env python3
"""
Data models for PDF analysis results.
"""

import os
from datetime import datetime
from typing import Dict, List, Any


class PDFTestResult:
    """Container for PDF test results."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.timestamp = datetime.now().isoformat()
        
        # Test results for each library
        self.pypdf_result = {}
        self.pymupdf_result = {}
        self.pdfplumber_result = {}
        
        # Overall assessment
        self.overall_score = 0.0
        self.issues = []
        self.recommendations = []

# -----------------------------------------------------------------------------
# Copyright (C) 2025 Jeff Luster, mailto:jeff.luster96@gmail.com
# License: GNU AFFERO GPL 3.0, https://www.gnu.org/licenses/agpl-3.0.html
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# Full license text can be found in the file "COPYING.txt".
# Full copyright text can be found in the file "main.py".
# -----------------------------------------------------------------------------

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
        self.overall_score = 0
        self.issues = []
        self.recommendations = []
        self.recommended_package = None

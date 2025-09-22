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
PDF Analyzer modules package.
"""

from .analyzer import PDFAnalyzer
from .models import PDFTestResult

__all__ = ['PDFAnalyzer', 'PDFTestResult']

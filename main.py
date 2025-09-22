# -----------------------------------------------------------------------------

# Part of "pdf-package-analyzer", a tool to analyze PDF files for quality 
# and compatibility with various pdf packages.
# Copyright (C) 2025 Jeff Luster, mailto:jeff.luster96@gmail.com

# License: GNU AFFERO GPL 3.0, https://www.gnu.org/licenses/agpl-3.0.html
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program in the file "COPYING.txt". If not, see 
# <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

#!/usr/bin/env python3
"""
Main CLI interface for PDF analyzer.
"""

import argparse
import sys
import traceback
import logging

from modules.analyzer import PDFAnalyzer


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze PDF files for quality and compatibility")
    parser.add_argument("--docs_dir", default="files/docs", help="Directory containing PDF files")
    parser.add_argument("--info_dir", help="Directory to store analysis results and logs (default: {docs_dir}-info)")
    parser.add_argument("--report_output", default="pdf_analysis_report.json", help="Output report file")
    parser.add_argument("--summary_output", help="Output summary file")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each PDF library test (default: 30)")
    parser.add_argument("--limit", type=int, help="Limit the number of PDF files to process (default: process all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", nargs='?', const="all", choices=["progress", "logs", "all"], default=None, help="Quiet mode: 'progress' hides progress bar, 'logs' hides console logs, 'all' hides both (default: all when --quiet is used)")
    parser.add_argument("--recommendation_only", action="store_true", help="Show only the recommended package and percentage of files it is recommended for")
    
    args = parser.parse_args()
    
    try:
        # Create analyzer (logging is set up in the constructor)
        analyzer = PDFAnalyzer(args.docs_dir, info_dir=args.info_dir, timeout_seconds=args.timeout, verbose=args.verbose, limit=args.limit, quiet=args.quiet)
        logger = analyzer.logger
        
        # Analyze all PDFs
        logger.info(f"Starting PDF analysis with {args.timeout}s timeout per library...")
        results = analyzer.analyze_all_pdfs()
        
        if not results:
            logger.warning("No PDF files found to analyze")
            return
        
        # Generate report
        report = analyzer.generate_report(args.report_output)
        
        # Print summary
        analyzer.print_summary(args.summary_output, recommendation_only=args.recommendation_only)
        
        logger.info("PDF analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

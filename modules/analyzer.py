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
Main PDF analyzer class.
"""

import os
import logging
import json
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from tqdm import tqdm

from .models import PDFTestResult
from .pdf_libraries import (
    PYPDF_AVAILABLE, PYMUPDF_AVAILABLE, PDFPLUMBER_AVAILABLE,
    test_pypdf_internal, test_pymupdf_internal, test_pdfplumber_internal
)
from .utils import run_with_timeout


class PDFAnalyzer:
    """Main PDF analysis class."""
    
    def __init__(self, docs_dir: str = "files/docs", info_dir: str = None, timeout_seconds: int = 30, verbose: bool = False, limit: int = None, quiet: str = None):
        self.docs_dir = Path(docs_dir)
        self.results = []
        self.timeout_seconds = timeout_seconds
        self.limit = limit
        self.quiet = quiet
        
        # Check if docs directory exists
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"docs directory '{docs_dir}' not found")
        
        # Set info directory - use provided path or default to one level above docs directory
        if info_dir is not None:
            self.info_dir = Path(info_dir)
        else:
            self.info_dir = self.docs_dir.parent / f"{self.docs_dir.name}-info"
        self.info_dir.mkdir(exist_ok=True)
        
        # Setup logging with output in info directory
        log_level = logging.DEBUG if verbose else logging.INFO
        self.logger = self._setup_logging(log_level)
    
    def _setup_logging(self, log_level=logging.INFO):
        """Setup logging configuration with output in info directory."""
        # Create logger
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler - output to info directory (always enabled)
        log_file = self.info_dir / 'pdf_test_results.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler - conditionally enabled based on quiet flag
        if self.quiet not in ["logs", "all"]:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def test_pypdf(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with pypdf library with timeout."""
        if not PYPDF_AVAILABLE:
            return {"error": "pypdf not available", "success": False}
        
        return run_with_timeout(test_pypdf_internal, self.timeout_seconds, file_path)
    
    def test_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with PyMuPDF (fitz) library with timeout."""
        if not PYMUPDF_AVAILABLE:
            return {"error": "PyMuPDF not available", "success": False}
        
        return run_with_timeout(test_pymupdf_internal, self.timeout_seconds, file_path)
    
    def test_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with pdfplumber library with timeout."""
        if not PDFPLUMBER_AVAILABLE:
            return {"error": "pdfplumber not available", "success": False}
        
        return run_with_timeout(test_pdfplumber_internal, self.timeout_seconds, file_path)
    
    def analyze_pdf(self, file_path: str, show_progress: bool = False) -> PDFTestResult:
        """Analyze a single PDF file with all available libraries."""
        # Log to file only (not console) for detailed tracking
        # Create a file-only logger for this specific message
        file_logger = logging.getLogger(f"{__name__}.file_only")
        file_logger.setLevel(logging.INFO)
        file_logger.handlers.clear()
        file_logger.propagate = False  # Prevent propagation to parent logger
        
        # Add only file handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = self.info_dir / 'pdf_test_results.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_logger.addHandler(file_handler)
        
        file_logger.info(f"Analyzing: {os.path.basename(file_path)}")
        
        result = PDFTestResult(file_path)
        
        # Test with each available library
        if PYPDF_AVAILABLE:
            result.pypdf_result = self.test_pypdf(file_path)
        
        if PYMUPDF_AVAILABLE:
            result.pymupdf_result = self.test_pymupdf(file_path)
        
        if PDFPLUMBER_AVAILABLE:
            result.pdfplumber_result = self.test_pdfplumber(file_path)
        
        # Calculate overall score and generate recommendations
        self._evaluate_pdf(result)
        
        return result
    
    def _evaluate_library_result(self, lib_result: Dict[str, Any], lib_name: str) -> Tuple[float, List[str], int]:
        """Evaluate a single library result and return (score, issues, timeout_count)."""
        issues = []
        timeout_count = 0
        
        if lib_result.get("success"):
            score = 1.0
            if lib_result.get("warnings"):
                issues.append(f"{lib_name}: {len(lib_result['warnings'])} warnings")
            if lib_result.get("errors"):
                issues.append(f"{lib_name}: {len(lib_result['errors'])} errors")
        else:
            score = 0.0
            if lib_result.get("timeout"):
                issues.append(f"{lib_name}: Timed out after {self.timeout_seconds} seconds")
                timeout_count = 1
            else:
                issues.append(f"{lib_name}: Failed - {lib_result.get('error', 'Unknown error')}")
        
        return score, issues, timeout_count

    def _evaluate_pdf(self, result: PDFTestResult):
        """Evaluate PDF quality and generate recommendations."""
        issues = []
        timeout_count = 0
        total_errors = 0
        package_errors = {}
        
        # Evaluate each library and count errors
        for lib_name, lib_result in [("pypdf", result.pypdf_result), ("PyMuPDF", result.pymupdf_result), ("pdfplumber", result.pdfplumber_result)]:
            if lib_result:
                # Count errors for this package
                error_count = 0
                if lib_result.get("success"):
                    # Count warnings and errors
                    error_count += len(lib_result.get("warnings", []))
                    error_count += len(lib_result.get("errors", []))
                else:
                    # Failed libraries count as 5 errors each
                    error_count = 5
                    if lib_result.get("timeout"):
                        issues.append(f"{lib_name}: Timed out after {self.timeout_seconds} seconds")
                        timeout_count += 1
                    else:
                        issues.append(f"{lib_name}: Failed - {lib_result.get('error', 'Unknown error')}")
                
                package_errors[lib_name] = error_count
                total_errors += error_count
                
                # Add detailed issues for successful libraries
                if lib_result.get("success"):
                    if lib_result.get("warnings"):
                        issues.append(f"{lib_name}: {len(lib_result['warnings'])} warnings")
                    if lib_result.get("errors"):
                        issues.append(f"{lib_name}: {len(lib_result['errors'])} errors")
        
        result.issues = issues
        
        # Calculate overall score based on error count
        if total_errors == 0:
            result.overall_score = 1.0  # Excellent
        elif total_errors <= 3:
            result.overall_score = 0.8  # Good
        elif total_errors <= 8:
            result.overall_score = 0.5  # Problematic
        else:
            result.overall_score = 0.0  # Failed
        
        # Determine recommended package
        if total_errors == 0:
            # No errors - default to pypdf
            result.recommended_package = "pypdf"
        else:
            # Find package with least errors
            min_errors = min(package_errors.values())
            best_packages = [pkg for pkg, errors in package_errors.items() if errors == min_errors]
            
            if min_errors == 5:  # All packages failed
                result.recommended_package = "Other"
            else:
                # Prefer pypdf if it's among the best, otherwise use the first best
                if "pypdf" in best_packages:
                    result.recommended_package = "pypdf"
                else:
                    result.recommended_package = best_packages[0]
        
        # Generate recommendations
        recommendations = []
        
        if timeout_count > 0:
            recommendations.append(f"PDF processing timed out for {timeout_count} library(ies) - consider increasing timeout or file may be corrupted")
        
        if result.overall_score == 0.0:
            recommendations.append("PDF appears to be corrupted or unreadable" + (" (timeouts suggest processing issues)" if timeout_count > 0 else ""))
        elif result.overall_score == 0.5:
            recommendations.append("PDF has significant issues - consider replacing")
        elif result.overall_score == 0.8:
            recommendations.append("PDF has minor issues but should work")
        else:
            recommendations.append("PDF appears to be in good condition")
        
        # Add package-specific recommendations
        if result.recommended_package != "Other":
            recommendations.append(f"Recommended package: {result.recommended_package}")
        else:
            recommendations.append("All packages failed - consider using alternative PDF processing tools")
        
        if result.file_size > 50 * 1024 * 1024:  # 50MB
            recommendations.append("Large file size may impact processing speed")
        
        result.recommendations = recommendations
    
    def analyze_all_pdfs(self) -> List[PDFTestResult]:
        """Analyze all PDF files in the docs directory."""
        pdf_files = list(self.docs_dir.glob("*.pdf"))
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {self.docs_dir}")
            return []
        
        # Apply limit if specified
        if self.limit is not None:
            pdf_files = pdf_files[:self.limit]
            self.logger.info(f"Found {len(list(self.docs_dir.glob('*.pdf')))} PDF files total, processing first {len(pdf_files)} files")
        else:
            self.logger.info(f"Found {len(pdf_files)} PDF files to analyze")
        
        # Use tqdm for progress bar with filename display (conditionally based on quiet flag)
        if self.quiet not in ["progress", "all"]:
            # Show progress bar
            with tqdm(total=len(pdf_files), desc="Analyzing PDFs", unit="file", 
                     bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}',
                     leave=True, dynamic_ncols=True) as pbar:
                for pdf_file in pdf_files:
                    try:
                        result = self.analyze_pdf(str(pdf_file))
                        self.results.append(result)
                        
                        # Update progress
                        pbar.update(1)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to analyze {pdf_file}: {e}")
                        traceback.print_exc()
                        # Still update progress even if file failed
                        pbar.update(1)
        else:
            # No progress bar - just process files
            for pdf_file in pdf_files:
                try:
                    result = self.analyze_pdf(str(pdf_file))
                    self.results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to analyze {pdf_file}: {e}")
                    traceback.print_exc()
        
        return self.results
    
    def generate_report(self, output_file: str = None):
        """Generate a detailed analysis report."""
        # Default output file in info directory if not specified
        if output_file is None:
            output_file = self.info_dir / "pdf_analysis_report.json"
        else:
            # If relative path, make it relative to info directory
            if not os.path.isabs(output_file):
                output_file = self.info_dir / output_file
        
        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "docs_directory": str(self.docs_dir),
            "total_files": len(self.results),
            "libraries_available": {
                "pypdf": PYPDF_AVAILABLE,
                "pymupdf": PYMUPDF_AVAILABLE,
                "pdfplumber": PDFPLUMBER_AVAILABLE
            },
            "summary": {
                "excellent_pdfs": len([r for r in self.results if r.overall_score == 1.0]),
                "good_pdfs": len([r for r in self.results if r.overall_score == 0.8]),
                "problematic_pdfs": len([r for r in self.results if r.overall_score == 0.5]),
                "failed_pdfs": len([r for r in self.results if r.overall_score == 0.0])
            },
            "detailed_results": []
        }
        
        # Add detailed results
        for result in self.results:
            report["detailed_results"].append({
                "filename": result.filename,
                "file_path": result.file_path,
                "file_size": result.file_size,
                "overall_score": result.overall_score,
                "issues": result.issues,
                "recommendations": result.recommendations,
                "recommended_package": result.recommended_package,
                "pypdf_result": result.pypdf_result,
                "pymupdf_result": result.pymupdf_result,
                "pdfplumber_result": result.pdfplumber_result
            })
        
        # Save report with custom JSON encoder to handle non-serializable objects
        def json_serializer(obj):
            """Custom JSON serializer to handle non-serializable objects."""
            if hasattr(obj, '__dict__'):
                return str(obj)
            return str(obj)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        self.logger.info(f"Analysis report saved to {output_file}")
        return report
    
    def _get_summary_stats(self) -> Dict[str, int]:
        """Get summary statistics for the analysis results."""
        return {
            "total": len(self.results),
            "excellent": len([r for r in self.results if r.overall_score == 1.0]),
            "good": len([r for r in self.results if r.overall_score == 0.8]),
            "problematic": len([r for r in self.results if r.overall_score == 0.5]),
            "failed": len([r for r in self.results if r.overall_score == 0.0])
        }
    
    def _get_package_recommendation_stats(self) -> Dict[str, int]:
        """Get package recommendation statistics."""
        stats = {"pypdf": 0, "PyMuPDF": 0, "pdfplumber": 0, "Other": 0}
        for result in self.results:
            if result.recommended_package:
                stats[result.recommended_package] = stats.get(result.recommended_package, 0) + 1
        return stats
    
    def _get_package_recommendation_stats_with_percentages(self) -> Dict[str, Tuple[int, float]]:
        """Get package recommendation statistics with percentages."""
        stats = self._get_package_recommendation_stats()
        total = len(self.results)
        
        if total == 0:
            return {pkg: (count, 0.0) for pkg, count in stats.items()}
        
        return {pkg: (count, (count / total) * 100) for pkg, count in stats.items()}

    def _format_problematic_file_details(self, result: PDFTestResult) -> List[str]:
        """Format detailed information for a problematic file."""
        lines = [
            f"\nFile: {result.filename}",
            f"Score: {result.overall_score:.1%}",
            f"Size: {result.file_size:,} bytes",
            "Issues:"
        ]
        
        for issue in result.issues:
            lines.append(f"  - {issue}")
        
        # Show detailed errors for each library
        for lib_name, lib_result in [("pypdf", result.pypdf_result), ("PyMuPDF", result.pymupdf_result), ("pdfplumber", result.pdfplumber_result)]:
            if lib_result.get("errors"):
                lines.append(f"\n{lib_name} detailed errors:")
                for error in lib_result["errors"][:10]:  # Show first 10 errors
                    lines.append(f"  - {error}")
                if len(lib_result["errors"]) > 10:
                    lines.append(f"  ... and {len(lib_result['errors']) - 10} more errors")
        
        lines.append("Recommendations:")
        for rec in result.recommendations:
            lines.append(f"  - {rec}")
        
        return lines

    def print_summary(self, output_file: str = None, recommendation_only: bool = False):
        """Print a summary of the analysis results and optionally save to file."""
        # Default output file in info directory if not specified
        if output_file is None:
            output_file = self.info_dir / "pdf_analysis_summary.txt"
        else:
            # If relative path, make it relative to info directory
            if not os.path.isabs(output_file):
                output_file = self.info_dir / output_file
        
        if not self.results:
            message = "No PDF files analyzed."
            print(message)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(message)
            return
        
        # Always build full summary content for the file
        full_summary_lines = [
            "\n" + "="*60,
            "PDF ANALYSIS SUMMARY",
            "="*60
        ]
        
        stats = self._get_summary_stats()
        package_stats = self._get_package_recommendation_stats_with_percentages()
        full_summary_lines.extend([
            f"Total PDF files analyzed: {stats['total']}",
            f"Excellent (0 errors): {stats['excellent']}",
            f"Good (1-3 errors): {stats['good']}",
            f"Problematic (4-8 errors): {stats['problematic']}",
            f"Failed (9+ errors): {stats['failed']}",
            f"\nPackage recommendations:",
            f"  pypdf: {package_stats['pypdf'][0]} files ({package_stats['pypdf'][1]:.1f}%)",
            f"  PyMuPDF: {package_stats['PyMuPDF'][0]} files ({package_stats['PyMuPDF'][1]:.1f}%)",
            f"  pdfplumber: {package_stats['pdfplumber'][0]} files ({package_stats['pdfplumber'][1]:.1f}%)",
            f"  Other: {package_stats['Other'][0]} files ({package_stats['Other'][1]:.1f}%)",
            f"\nLibraries available:",
            f"  pypdf: {'✓' if PYPDF_AVAILABLE else '✗'}",
            f"  PyMuPDF: {'✓' if PYMUPDF_AVAILABLE else '✗'}",
            f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}"
        ])
        
        problematic_files = [r for r in self.results if r.overall_score < 0.7]
        if problematic_files:
            full_summary_lines.extend([
                f"Total problematic files: {len(problematic_files)}",
                f"\nDetailed analysis of problematic files:",
                "-" * 50
            ])
            for result in problematic_files:
                full_summary_lines.extend(self._format_problematic_file_details(result))
        
        # Determine what to print to console
        if recommendation_only:
            # Show only recommended package and percentage
            best_package = max(package_stats.items(), key=lambda x: x[1][0])
            package_name, (count, percentage) = best_package
            
            console_lines = [
                f"{package_name}: {count} files ({percentage:.1f}%)"
            ]
        else:
            # Show full summary
            console_lines = full_summary_lines
        
        # Print to console
        for line in console_lines:
            print(line)
        
        # Always write full summary to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(full_summary_lines))
        
        self.logger.info(f"Summary saved to {output_file}")

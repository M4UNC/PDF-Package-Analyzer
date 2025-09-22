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

from models import PDFTestResult
from pdf_libraries import (
    PYPDF_AVAILABLE, PYMUPDF_AVAILABLE, PDFPLUMBER_AVAILABLE,
    test_pypdf_internal, test_pymupdf_internal, test_pdfplumber_internal
)
from utils import run_with_timeout


class PDFAnalyzer:
    """Main PDF analysis class."""
    
    def __init__(self, books_dir: str = "library/books", info_dir: str = None, timeout_seconds: int = 30, verbose: bool = False, limit: int = None):
        self.books_dir = Path(books_dir)
        self.results = []
        self.timeout_seconds = timeout_seconds
        self.limit = limit
        
        # Check if books directory exists
        if not self.books_dir.exists():
            raise FileNotFoundError(f"Books directory '{books_dir}' not found")
        
        # Set info directory - use provided path or default to one level above books directory
        if info_dir is not None:
            self.info_dir = Path(info_dir)
        else:
            self.info_dir = self.books_dir.parent / f"{self.books_dir.name}-info"
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
        
        # File handler - output to info directory
        log_file = self.info_dir / 'pdf_test_results.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
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
        scores = []
        issues = []
        timeout_count = 0
        
        # Evaluate each library
        for lib_name, lib_result in [("pypdf", result.pypdf_result), ("PyMuPDF", result.pymupdf_result), ("pdfplumber", result.pdfplumber_result)]:
            score, lib_issues, lib_timeouts = self._evaluate_library_result(lib_result, lib_name)
            scores.append(score)
            issues.extend(lib_issues)
            timeout_count += lib_timeouts
        
        # Calculate overall score
        result.overall_score = sum(scores) / len(scores) if scores else 0.0
        result.issues = issues
        
        # Generate recommendations
        recommendations = []
        
        if timeout_count > 0:
            recommendations.append(f"PDF processing timed out for {timeout_count} library(ies) - consider increasing timeout or file may be corrupted")
        
        if result.overall_score == 0.0:
            recommendations.append("PDF appears to be corrupted or unreadable" + (" (timeouts suggest processing issues)" if timeout_count > 0 else ""))
        elif result.overall_score < 0.5:
            recommendations.append("PDF has significant issues - consider replacing")
        elif result.overall_score < 1.0:
            recommendations.append("PDF has minor issues but should work")
        else:
            recommendations.append("PDF appears to be in good condition")
        
        # Library-specific recommendations
        if result.pypdf_result.get("warnings") and len(result.pypdf_result["warnings"]) > 10:
            recommendations.append("Consider using PyMuPDF or pdfplumber instead of pypdf")
        
        if result.file_size > 50 * 1024 * 1024:  # 50MB
            recommendations.append("Large file size may impact processing speed")
        
        result.recommendations = recommendations
    
    def analyze_all_pdfs(self) -> List[PDFTestResult]:
        """Analyze all PDF files in the books directory."""
        pdf_files = list(self.books_dir.glob("*.pdf"))
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {self.books_dir}")
            return []
        
        # Apply limit if specified
        if self.limit is not None:
            pdf_files = pdf_files[:self.limit]
            self.logger.info(f"Found {len(list(self.books_dir.glob('*.pdf')))} PDF files total, processing first {len(pdf_files)} files")
        else:
            self.logger.info(f"Found {len(pdf_files)} PDF files to analyze")
        
        # Use tqdm for progress bar with filename display
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
            "books_directory": str(self.books_dir),
            "total_files": len(self.results),
            "libraries_available": {
                "pypdf": PYPDF_AVAILABLE,
                "pymupdf": PYMUPDF_AVAILABLE,
                "pdfplumber": PDFPLUMBER_AVAILABLE
            },
            "summary": {
                "excellent_pdfs": len([r for r in self.results if r.overall_score == 1.0]),
                "good_pdfs": len([r for r in self.results if 0.7 <= r.overall_score < 1.0]),
                "problematic_pdfs": len([r for r in self.results if 0.3 <= r.overall_score < 0.7]),
                "failed_pdfs": len([r for r in self.results if r.overall_score < 0.3])
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
            "good": len([r for r in self.results if 0.7 <= r.overall_score < 1.0]),
            "problematic": len([r for r in self.results if 0.3 <= r.overall_score < 0.7]),
            "failed": len([r for r in self.results if r.overall_score < 0.3])
        }

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

    def print_summary(self, output_file: str = None):
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
        
        # Build summary content
        summary_lines = [
            "\n" + "="*60,
            "PDF ANALYSIS SUMMARY",
            "="*60
        ]
        
        stats = self._get_summary_stats()
        summary_lines.extend([
            f"Total PDF files analyzed: {stats['total']}",
            f"Excellent (100%): {stats['excellent']}",
            f"Good (70-99%): {stats['good']}",
            f"Problematic (30-69%): {stats['problematic']}",
            f"Failed (<30%): {stats['failed']}",
            f"\nLibraries available:",
            f"  pypdf: {'✓' if PYPDF_AVAILABLE else '✗'}",
            f"  PyMuPDF: {'✓' if PYMUPDF_AVAILABLE else '✗'}",
            f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}"
        ])
        
        problematic_files = [r for r in self.results if r.overall_score < 0.7]
        if problematic_files:
            summary_lines.extend([
                f"Total problematic files: {len(problematic_files)}",
                f"\nDetailed analysis of problematic files:",
                "-" * 50
            ])
            for result in problematic_files:
                summary_lines.extend(self._format_problematic_file_details(result))
        
        # Print to console and write to file
        for line in summary_lines:
            print(line)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines))
        
        self.logger.info(f"Summary saved to {output_file}")

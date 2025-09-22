#!/usr/bin/env python3
"""
PDF Test Analyzer

A standalone script to test and analyze PDF documents for quality issues,
parsing problems, and compatibility with different PDF libraries.

This script helps identify problematic PDFs before they cause issues in the RAG workflow.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import json
import traceback
import multiprocessing
import signal
import time
import io
import contextlib
from tqdm import tqdm

# PDF processing libraries
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Configure logging
def setup_logging(log_level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pdf_test_results.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

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
    
    @contextlib.contextmanager
    def capture_stdout_stderr(self):
        """Context manager to capture stdout and stderr output."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            yield stdout_capture, stderr_capture
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
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
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create a base result dictionary with default values."""
        return {
            "success": False,
            "pages": 0,
            "warnings": [],
            "errors": [],
            "text_length": 0,
            "metadata": {},
            "stdout_output": "",
            "stderr_output": ""
        }
    
    def _extract_pypdf_metadata(self, metadata) -> Dict[str, str]:
        """Extract metadata from pypdf reader."""
        if not metadata:
            return {}
        return {
            "title": str(metadata.get("/Title", "")),
            "author": str(metadata.get("/Author", "")),
            "creator": str(metadata.get("/Creator", "")),
            "producer": str(metadata.get("/Producer", "")),
            "creation_date": str(metadata.get("/CreationDate", "")),
            "modification_date": str(metadata.get("/ModDate", ""))
        }
    
    def _extract_pymupdf_metadata(self, metadata) -> Dict[str, str]:
        """Extract metadata from PyMuPDF document."""
        if not metadata:
            return {}
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", "")
        }
    
    def _extract_pdfplumber_metadata(self, metadata) -> Dict[str, str]:
        """Extract metadata from pdfplumber PDF."""
        if not metadata:
            return {}
        return {
            "title": metadata.get("Title", ""),
            "author": metadata.get("Author", ""),
            "creator": metadata.get("Creator", ""),
            "producer": metadata.get("Producer", ""),
            "creation_date": str(metadata.get("CreationDate", "")),
            "modification_date": str(metadata.get("ModDate", ""))
        }
    
    def _extract_text_pages(self, pages, errors: List[str], library_name: str) -> int:
        """Extract text from pages and return total length."""
        text_content = ""
        for i, page in enumerate(pages):
            try:
                if library_name == "pypdf":
                    text_content += page.extract_text()
                elif library_name == "pymupdf":
                    text_content += page.get_text()
                elif library_name == "pdfplumber":
                    text_content += page.extract_text() or ""
            except Exception as e:
                errors.append(f"Page {i+1} text extraction failed: {str(e)}")
        return len(text_content)
    
    def _process_output_capture(self, result: Dict[str, Any], stdout_capture, stderr_capture):
        """Process captured stdout and stderr output."""
        result["stdout_output"] = stdout_capture.getvalue().strip()
        result["stderr_output"] = stderr_capture.getvalue().strip()
        
        # Add error-like content to errors list
        for output, prefix in [(result["stderr_output"], "stderr"), (result["stdout_output"], "stdout")]:
            if output:
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                        result["errors"].append(f"{prefix}: {line}")

    def _run_with_timeout(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Run a function with timeout using threading approach."""
        import threading
        import queue
        
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def worker():
            try:
                result = func(*args, **kwargs)
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)
        
        # Start the worker thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # Wait for completion or timeout
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            # Thread is still running, timeout occurred
            return {
                "success": False,
                "error": f"Operation timed out after {self.timeout_seconds} seconds",
                "timeout": True
            }
        else:
            # Thread completed, check for results
            if not result_queue.empty():
                return result_queue.get()
            elif not exception_queue.empty():
                exception = exception_queue.get()
                return {
                    "success": False,
                    "error": f"Operation failed: {str(exception)}",
                    "timeout": False
                }
            else:
                return {
                    "success": False,
                    "error": "Operation completed but no result returned",
                    "timeout": False
                }
    
    def _test_pypdf_internal(self, file_path: str) -> Dict[str, Any]:
        """Internal method to test PDF with pypdf library (without timeout)."""
        result = self._create_base_result()
        
        try:
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                    with open(file_path, 'rb') as file:
                        reader = pypdf.PdfReader(file)
                        result["pages"] = len(reader.pages)
                        result["metadata"] = self._extract_pypdf_metadata(reader.metadata)
                        result["text_length"] = self._extract_text_pages(reader.pages[:5], result["errors"], "pypdf")
                        
                        for warning in w:
                            result["warnings"].append(str(warning.message))
                        
                        result["success"] = True
                
                self._process_output_capture(result, stdout_capture, stderr_capture)
                    
        except Exception as e:
            result["errors"].append(f"pypdf processing failed: {str(e)}")
            result["success"] = False
        
        return result

    def test_pypdf(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with pypdf library with timeout."""
        if not PYPDF_AVAILABLE:
            return {"error": "pypdf not available", "success": False}
        
        return self._run_with_timeout(self._test_pypdf_internal, file_path)
    
    def _test_pymupdf_internal(self, file_path: str) -> Dict[str, Any]:
        """Internal method to test PDF with PyMuPDF (fitz) library (without timeout)."""
        result = self._create_base_result()
        
        try:
            with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                doc = fitz.open(file_path)
                result["pages"] = doc.page_count
                result["metadata"] = self._extract_pymupdf_metadata(doc.metadata)
                result["text_length"] = self._extract_text_pages([doc[i] for i in range(min(5, doc.page_count))], result["errors"], "pymupdf")
                result["success"] = True
                doc.close()
            
            self._process_output_capture(result, stdout_capture, stderr_capture)
            
        except Exception as e:
            result["errors"].append(f"PyMuPDF processing failed: {str(e)}")
            result["success"] = False
        
        return result

    def test_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with PyMuPDF (fitz) library with timeout."""
        if not PYMUPDF_AVAILABLE:
            return {"error": "PyMuPDF not available", "success": False}
        
        return self._run_with_timeout(self._test_pymupdf_internal, file_path)
    
    def _test_pdfplumber_internal(self, file_path: str) -> Dict[str, Any]:
        """Internal method to test PDF with pdfplumber library (without timeout)."""
        result = self._create_base_result()
        
        try:
            with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                with pdfplumber.open(file_path) as pdf:
                    result["pages"] = len(pdf.pages)
                    result["metadata"] = self._extract_pdfplumber_metadata(pdf.metadata)
                    result["text_length"] = self._extract_text_pages(pdf.pages[:5], result["errors"], "pdfplumber")
                    result["success"] = True
            
            self._process_output_capture(result, stdout_capture, stderr_capture)
                
        except Exception as e:
            result["errors"].append(f"pdfplumber processing failed: {str(e)}")
            result["success"] = False
        
        return result

    def test_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with pdfplumber library with timeout."""
        if not PDFPLUMBER_AVAILABLE:
            return {"error": "pdfplumber not available", "success": False}
        
        return self._run_with_timeout(self._test_pdfplumber_internal, file_path)
    
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

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze PDF documents for quality and compatibility")
    parser.add_argument("--books_dir", default="library/books", help="Directory containing PDF files")
    parser.add_argument("--info_dir", help="Directory to store analysis results and logs (default: {books_dir}-info)")
    parser.add_argument("--report_output", default="pdf_analysis_report.json", help="Output report file")
    parser.add_argument("--summary_output", help="Output summary file")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each PDF library test (default: 30)")
    parser.add_argument("--limit", type=int, help="Limit the number of PDF documents to process (default: process all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        # Create analyzer (logging is set up in the constructor)
        analyzer = PDFAnalyzer(args.books_dir, info_dir=args.info_dir, timeout_seconds=args.timeout, verbose=args.verbose, limit=args.limit)
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
        analyzer.print_summary(args.summary_output)
        
        logger.info("PDF analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

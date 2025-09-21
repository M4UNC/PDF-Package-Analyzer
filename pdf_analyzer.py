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
    
    def __init__(self, books_dir: str = "books", timeout_seconds: int = 30, verbose: bool = False):
        self.books_dir = Path(books_dir)
        self.results = []
        self.timeout_seconds = timeout_seconds
        
        # Check if books directory exists
        if not self.books_dir.exists():
            raise FileNotFoundError(f"Books directory '{books_dir}' not found")
        
        # Create info directory within books directory
        self.info_dir = self.books_dir / "info"
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
        result = {
            "success": False,
            "pages": 0,
            "warnings": [],
            "errors": [],
            "text_length": 0,
            "metadata": {},
            "stdout_output": "",
            "stderr_output": ""
        }
        
        try:
            # Capture warnings, stdout, and stderr
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                    with open(file_path, 'rb') as file:
                        reader = pypdf.PdfReader(file)
                        
                        # Basic info
                        result["pages"] = len(reader.pages)
                        
                        # Extract metadata
                        if reader.metadata:
                            result["metadata"] = {
                                "title": str(reader.metadata.get("/Title", "")),
                                "author": str(reader.metadata.get("/Author", "")),
                                "creator": str(reader.metadata.get("/Creator", "")),
                                "producer": str(reader.metadata.get("/Producer", "")),
                                "creation_date": str(reader.metadata.get("/CreationDate", "")),
                                "modification_date": str(reader.metadata.get("/ModDate", ""))
                            }
                        
                        # Extract text from first few pages to test
                        text_content = ""
                        for i, page in enumerate(reader.pages[:5]):  # Test first 5 pages
                            try:
                                text_content += page.extract_text()
                            except Exception as e:
                                result["errors"].append(f"Page {i+1} text extraction failed: {str(e)}")
                        
                        result["text_length"] = len(text_content)
                        
                        # Capture warnings
                        for warning in w:
                            result["warnings"].append(str(warning.message))
                        
                        result["success"] = True
                
                # Capture stdout and stderr output
                result["stdout_output"] = stdout_capture.getvalue().strip()
                result["stderr_output"] = stderr_capture.getvalue().strip()
                
                # Add stdout/stderr messages to errors if they contain error-like content
                if result["stderr_output"]:
                    stderr_lines = [line.strip() for line in result["stderr_output"].split('\n') if line.strip()]
                    for line in stderr_lines:
                        if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                            result["errors"].append(f"stderr: {line}")
                
                if result["stdout_output"]:
                    stdout_lines = [line.strip() for line in result["stdout_output"].split('\n') if line.strip()]
                    for line in stdout_lines:
                        if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                            result["errors"].append(f"stdout: {line}")
                    
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
        result = {
            "success": False,
            "pages": 0,
            "warnings": [],
            "errors": [],
            "text_length": 0,
            "metadata": {},
            "stdout_output": "",
            "stderr_output": ""
        }
        
        try:
            with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                doc = fitz.open(file_path)
                
                # Basic info
                result["pages"] = doc.page_count
                
                # Extract metadata
                metadata = doc.metadata
                if metadata:
                    result["metadata"] = {
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""),
                        "creator": metadata.get("creator", ""),
                        "producer": metadata.get("producer", ""),
                        "creation_date": metadata.get("creationDate", ""),
                        "modification_date": metadata.get("modDate", "")
                    }
                
                # Extract text from first few pages
                text_content = ""
                for i in range(min(5, doc.page_count)):  # Test first 5 pages
                    try:
                        page = doc[i]
                        text_content += page.get_text()
                    except Exception as e:
                        result["errors"].append(f"Page {i+1} text extraction failed: {str(e)}")
                
                result["text_length"] = len(text_content)
                result["success"] = True
                
                doc.close()
            
            # Capture stdout and stderr output
            result["stdout_output"] = stdout_capture.getvalue().strip()
            result["stderr_output"] = stderr_capture.getvalue().strip()
            
            # Add stdout/stderr messages to errors if they contain error-like content
            if result["stderr_output"]:
                stderr_lines = [line.strip() for line in result["stderr_output"].split('\n') if line.strip()]
                for line in stderr_lines:
                    if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                        result["errors"].append(f"stderr: {line}")
            
            if result["stdout_output"]:
                stdout_lines = [line.strip() for line in result["stdout_output"].split('\n') if line.strip()]
                for line in stdout_lines:
                    if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                        result["errors"].append(f"stdout: {line}")
            
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
        result = {
            "success": False,
            "pages": 0,
            "warnings": [],
            "errors": [],
            "text_length": 0,
            "metadata": {},
            "stdout_output": "",
            "stderr_output": ""
        }
        
        try:
            with self.capture_stdout_stderr() as (stdout_capture, stderr_capture):
                with pdfplumber.open(file_path) as pdf:
                    # Basic info
                    result["pages"] = len(pdf.pages)
                    
                    # Extract metadata
                    if pdf.metadata:
                        result["metadata"] = {
                            "title": pdf.metadata.get("Title", ""),
                            "author": pdf.metadata.get("Author", ""),
                            "creator": pdf.metadata.get("Creator", ""),
                            "producer": pdf.metadata.get("Producer", ""),
                            "creation_date": str(pdf.metadata.get("CreationDate", "")),
                            "modification_date": str(pdf.metadata.get("ModDate", ""))
                        }
                    
                    # Extract text from first few pages
                    text_content = ""
                    for i, page in enumerate(pdf.pages[:5]):  # Test first 5 pages
                        try:
                            text_content += page.extract_text() or ""
                        except Exception as e:
                            result["errors"].append(f"Page {i+1} text extraction failed: {str(e)}")
                    
                    result["text_length"] = len(text_content)
                    result["success"] = True
            
            # Capture stdout and stderr output
            result["stdout_output"] = stdout_capture.getvalue().strip()
            result["stderr_output"] = stderr_capture.getvalue().strip()
            
            # Add stdout/stderr messages to errors if they contain error-like content
            if result["stderr_output"]:
                stderr_lines = [line.strip() for line in result["stderr_output"].split('\n') if line.strip()]
                for line in stderr_lines:
                    if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                        result["errors"].append(f"stderr: {line}")
            
            if result["stdout_output"]:
                stdout_lines = [line.strip() for line in result["stdout_output"].split('\n') if line.strip()]
                for line in stdout_lines:
                    if any(keyword in line.lower() for keyword in ['error', 'invalid', 'failed', 'exception', 'traceback']):
                        result["errors"].append(f"stdout: {line}")
                
        except Exception as e:
            result["errors"].append(f"pdfplumber processing failed: {str(e)}")
            result["success"] = False
        
        return result

    def test_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Test PDF with pdfplumber library with timeout."""
        if not PDFPLUMBER_AVAILABLE:
            return {"error": "pdfplumber not available", "success": False}
        
        return self._run_with_timeout(self._test_pdfplumber_internal, file_path)
    
    def analyze_pdf(self, file_path: str) -> PDFTestResult:
        """Analyze a single PDF file with all available libraries."""
        self.logger.info(f"Analyzing: {os.path.basename(file_path)}")
        
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
    
    def _evaluate_pdf(self, result: PDFTestResult):
        """Evaluate PDF quality and generate recommendations."""
        scores = []
        issues = []
        timeout_count = 0
        
        # Evaluate pypdf results
        if result.pypdf_result.get("success"):
            scores.append(1.0)
            if result.pypdf_result.get("warnings"):
                issues.append(f"pypdf: {len(result.pypdf_result['warnings'])} warnings")
            if result.pypdf_result.get("errors"):
                issues.append(f"pypdf: {len(result.pypdf_result['errors'])} errors")
        else:
            scores.append(0.0)
            if result.pypdf_result.get("timeout"):
                issues.append(f"pypdf: Timed out after {self.timeout_seconds} seconds")
                timeout_count += 1
            else:
                issues.append(f"pypdf: Failed - {result.pypdf_result.get('error', 'Unknown error')}")
        
        # Evaluate PyMuPDF results
        if result.pymupdf_result.get("success"):
            scores.append(1.0)
            if result.pymupdf_result.get("warnings"):
                issues.append(f"PyMuPDF: {len(result.pymupdf_result['warnings'])} warnings")
            if result.pymupdf_result.get("errors"):
                issues.append(f"PyMuPDF: {len(result.pymupdf_result['errors'])} errors")
        else:
            scores.append(0.0)
            if result.pymupdf_result.get("timeout"):
                issues.append(f"PyMuPDF: Timed out after {self.timeout_seconds} seconds")
                timeout_count += 1
            else:
                issues.append(f"PyMuPDF: Failed - {result.pymupdf_result.get('error', 'Unknown error')}")
        
        # Evaluate pdfplumber results
        if result.pdfplumber_result.get("success"):
            scores.append(1.0)
            if result.pdfplumber_result.get("warnings"):
                issues.append(f"pdfplumber: {len(result.pdfplumber_result['warnings'])} warnings")
            if result.pdfplumber_result.get("errors"):
                issues.append(f"pdfplumber: {len(result.pdfplumber_result['errors'])} errors")
        else:
            scores.append(0.0)
            if result.pdfplumber_result.get("timeout"):
                issues.append(f"pdfplumber: Timed out after {self.timeout_seconds} seconds")
                timeout_count += 1
            else:
                issues.append(f"pdfplumber: Failed - {result.pdfplumber_result.get('error', 'Unknown error')}")
        
        # Calculate overall score
        result.overall_score = sum(scores) / len(scores) if scores else 0.0
        result.issues = issues
        
        # Generate recommendations
        recommendations = []
        
        if timeout_count > 0:
            recommendations.append(f"PDF processing timed out for {timeout_count} library(ies) - consider increasing timeout or file may be corrupted")
        
        if result.overall_score == 0.0:
            if timeout_count > 0:
                recommendations.append("PDF appears to be corrupted or unreadable (timeouts suggest processing issues)")
            else:
                recommendations.append("PDF appears to be corrupted or unreadable")
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
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to analyze")
        
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
    
    def print_summary(self):
        """Print a summary of the analysis results."""
        if not self.results:
            print("No PDF files analyzed.")
            return
        
        print("\n" + "="*60)
        print("PDF ANALYSIS SUMMARY")
        print("="*60)
        
        total_files = len(self.results)
        excellent = len([r for r in self.results if r.overall_score == 1.0])
        good = len([r for r in self.results if 0.7 <= r.overall_score < 1.0])
        problematic = len([r for r in self.results if 0.3 <= r.overall_score < 0.7])
        failed = len([r for r in self.results if r.overall_score < 0.3])
        
        print(f"Total PDF files analyzed: {total_files}")
        print(f"Excellent (100%): {excellent}")
        print(f"Good (70-99%): {good}")
        print(f"Problematic (30-69%): {problematic}")
        print(f"Failed (<30%): {failed}")
        
        print(f"\nLibraries available:")
        print(f"  pypdf: {'✓' if PYPDF_AVAILABLE else '✗'}")
        print(f"  PyMuPDF: {'✓' if PYMUPDF_AVAILABLE else '✗'}")
        print(f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
        
        problematic_files = [r for r in self.results if r.overall_score < 0.7]
        if problematic_files:
            print(f"Total problematic files: {len(problematic_files)}")
            print(f"\nDetailed analysis of problematic files:")
            print("-" * 50)
            for result in problematic_files:
                print(f"\nFile: {result.filename}")
                print(f"Score: {result.overall_score:.1%}")
                print(f"Size: {result.file_size:,} bytes")
                print("Issues:")
                for issue in result.issues:
                    print(f"  - {issue}")
                
                # Show detailed errors for each library
                for lib_name, lib_result in [("pypdf", result.pypdf_result), ("PyMuPDF", result.pymupdf_result), ("pdfplumber", result.pdfplumber_result)]:
                    if lib_result.get("errors"):
                        print(f"\n{lib_name} detailed errors:")
                        for error in lib_result["errors"][:10]:  # Show first 10 errors
                            print(f"  - {error}")
                        if len(lib_result["errors"]) > 10:
                            print(f"  ... and {len(lib_result['errors']) - 10} more errors")
                
                print("Recommendations:")
                for rec in result.recommendations:
                    print(f"  - {rec}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze PDF documents for quality and compatibility")
    parser.add_argument("--books-dir", default="books", help="Directory containing PDF files")
    parser.add_argument("--output", default="pdf_analysis_report.json", help="Output report file")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each PDF library test (default: 30)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        # Create analyzer (logging is set up in the constructor)
        analyzer = PDFAnalyzer(args.books_dir, timeout_seconds=args.timeout, verbose=args.verbose)
        logger = analyzer.logger
        
        # Analyze all PDFs
        logger.info(f"Starting PDF analysis with {args.timeout}s timeout per library...")
        results = analyzer.analyze_all_pdfs()
        
        if not results:
            logger.warning("No PDF files found to analyze")
            return
        
        # Generate report
        report = analyzer.generate_report(args.output)
        
        # Print summary
        analyzer.print_summary()
        
        logger.info("PDF analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

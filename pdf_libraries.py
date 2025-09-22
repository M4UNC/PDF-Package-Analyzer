#!/usr/bin/env python3
"""
PDF library testing modules for pypdf, PyMuPDF, and pdfplumber.
"""

import io
import sys
import warnings
from typing import Dict, List, Any, Tuple
from contextlib import contextmanager

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


@contextmanager
def capture_stdout_stderr():
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


def create_base_result() -> Dict[str, Any]:
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


def extract_pypdf_metadata(metadata) -> Dict[str, str]:
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


def extract_pymupdf_metadata(metadata) -> Dict[str, str]:
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


def extract_pdfplumber_metadata(metadata) -> Dict[str, str]:
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


def extract_text_pages(pages, errors: List[str], library_name: str) -> int:
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


def process_output_capture(result: Dict[str, Any], stdout_capture, stderr_capture):
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


def test_pypdf_internal(file_path: str) -> Dict[str, Any]:
    """Internal method to test PDF with pypdf library (without timeout)."""
    result = create_base_result()
    
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            with capture_stdout_stderr() as (stdout_capture, stderr_capture):
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    result["pages"] = len(reader.pages)
                    result["metadata"] = extract_pypdf_metadata(reader.metadata)
                    result["text_length"] = extract_text_pages(reader.pages[:5], result["errors"], "pypdf")
                    
                    for warning in w:
                        result["warnings"].append(str(warning.message))
                    
                    result["success"] = True
            
            process_output_capture(result, stdout_capture, stderr_capture)
                
    except Exception as e:
        result["errors"].append(f"pypdf processing failed: {str(e)}")
        result["success"] = False
    
    return result


def test_pymupdf_internal(file_path: str) -> Dict[str, Any]:
    """Internal method to test PDF with PyMuPDF (fitz) library (without timeout)."""
    result = create_base_result()
    
    try:
        with capture_stdout_stderr() as (stdout_capture, stderr_capture):
            doc = fitz.open(file_path)
            result["pages"] = doc.page_count
            result["metadata"] = extract_pymupdf_metadata(doc.metadata)
            result["text_length"] = extract_text_pages([doc[i] for i in range(min(5, doc.page_count))], result["errors"], "pymupdf")
            result["success"] = True
            doc.close()
        
        process_output_capture(result, stdout_capture, stderr_capture)
        
    except Exception as e:
        result["errors"].append(f"PyMuPDF processing failed: {str(e)}")
        result["success"] = False
    
    return result


def test_pdfplumber_internal(file_path: str) -> Dict[str, Any]:
    """Internal method to test PDF with pdfplumber library (without timeout)."""
    result = create_base_result()
    
    try:
        with capture_stdout_stderr() as (stdout_capture, stderr_capture):
            with pdfplumber.open(file_path) as pdf:
                result["pages"] = len(pdf.pages)
                result["metadata"] = extract_pdfplumber_metadata(pdf.metadata)
                result["text_length"] = extract_text_pages(pdf.pages[:5], result["errors"], "pdfplumber")
                result["success"] = True
        
        process_output_capture(result, stdout_capture, stderr_capture)
            
    except Exception as e:
        result["errors"].append(f"pdfplumber processing failed: {str(e)}")
        result["success"] = False
    
    return result

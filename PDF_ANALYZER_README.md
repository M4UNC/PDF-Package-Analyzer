# PDF Test Analyzer

A standalone Python script to test and analyze PDF documents for quality issues, parsing problems, and compatibility with different PDF libraries. This tool helps identify problematic PDFs before they cause issues in your RAG workflow.

## Features

- **Multi-library testing**: Tests PDFs with pypdf, PyMuPDF (fitz), and pdfplumber
- **Comprehensive analysis**: Checks for parsing errors, warnings, and text extraction issues
- **Detailed reporting**: Generates JSON reports with file-specific error details
- **Quality scoring**: Provides overall quality scores for each PDF
- **Recommendations**: Suggests which PDF library works best for each file
- **Progress tracking**: Shows real-time progress during analysis

## Installation

1. Install the required dependencies:
```bash
pip install -r pdf_analyzer_requirements.txt
```

2. Make sure you have PDF files in a `books` directory (or specify a different directory)

## Usage

### Basic Usage

```bash
# Analyze all PDFs in the default 'books' directory
python pdf_test_analyzer.py

# Analyze PDFs in a specific directory
python pdf_test_analyzer.py --books-dir /path/to/your/pdfs

# Enable verbose logging
python pdf_test_analyzer.py --verbose

# Specify custom output file
python pdf_test_analyzer.py --output my_analysis_report.json
```

### Using the Test Script

```bash
# Run the simple test interface
python test_pdf_analyzer.py
```

### Command Line Options

- `--books-dir`: Directory containing PDF files (default: "books")
- `--output`: Output report file (default: "pdf_analysis_report.json")
- `--verbose`, `-v`: Enable verbose logging

## Output Files

The analyzer generates several output files:

1. **`pdf_analysis_report.json`**: Detailed analysis report with all results
2. **`pdf_test_results.log`**: Log file with analysis progress and errors
3. **Console output**: Summary statistics and problematic file details

## Understanding the Results

### Quality Scores

- **1.0 (100%)**: Excellent - PDF works perfectly with all libraries
- **0.7-0.99 (70-99%)**: Good - PDF works well with minor issues
- **0.3-0.69 (30-69%)**: Problematic - PDF has significant issues but may work
- **0.0-0.29 (0-29%)**: Failed - PDF is corrupted or unreadable

### Common Issues

- **Object definition errors**: PDF structure problems
- **Page label issues**: Problems with page numbering
- **Text extraction failures**: Content cannot be extracted properly
- **Metadata corruption**: PDF metadata is damaged

### Recommendations

The analyzer provides specific recommendations for each PDF:

- **Library suggestions**: Which PDF library works best
- **File quality**: Whether the PDF should be replaced
- **Processing tips**: How to handle specific issues

## Integration with RAG Workflow

The enhanced RAG workflow now includes:

1. **Better error logging**: File-specific error tracking
2. **Warning capture**: Captures and logs PDF processing warnings
3. **Statistics tracking**: Shows success/warning/error counts
4. **Separate log files**: PDF warnings logged to `pdf_processing_warnings.log`

## Example Output

```
PDF ANALYSIS SUMMARY
============================================================
Total PDF files analyzed: 5
Excellent (100%): 2
Good (70-99%): 2
Problematic (30-69%): 1
Failed (<30%): 0

Libraries available:
  pypdf: ✓
  PyMuPDF: ✓
  pdfplumber: ✓

Problematic files:
  problematic_document.pdf (Score: 50.0%)
    - pypdf: 15 warnings
    - PyMuPDF: 2 warnings
```

## Troubleshooting

### Common Issues

1. **No PDF files found**: Make sure PDFs are in the correct directory
2. **Library import errors**: Install missing dependencies
3. **Permission errors**: Check file permissions for PDF files

### Getting Help

If you encounter issues:

1. Check the log files for detailed error messages
2. Run with `--verbose` flag for more detailed output
3. Verify that PDF files are not corrupted
4. Ensure all required libraries are installed

## Dependencies

- `pypdf`: Basic PDF processing
- `PyMuPDF`: Advanced PDF processing
- `pdfplumber`: Text extraction focused
- `tqdm`: Progress bars
- `pathlib`: Path handling (built-in)
- `json`: JSON handling (built-in)
- `logging`: Logging (built-in)

## License

This tool is part of the Book Summarizer project and follows the same license terms.

# PDF Package Analyzer

A comprehensive Python tool for analyzing PDF files and determining the best PDF processing library for each file. The analyzer tests PDFs against multiple libraries (pypdf, PyMuPDF, pdfplumber) and provides detailed compatibility reports and recommendations.

## 🚀 Features

- **Multi-library Testing**: Tests PDFs against pypdf, PyMuPDF, and pdfplumber
- **Comprehensive Analysis**: Evaluates text extraction, metadata access, and error handling
- **Detailed Reporting**: Generates JSON reports and text summaries
- **Timeout Protection**: Prevents hanging on problematic PDFs
- **Progress Tracking**: Visual progress bars and logging
- **Modular Architecture**: Clean, maintainable code structure
- **CLI Interface**: Easy-to-use command-line interface

## 📁 Project Structure

```
pdf-package-analyzer/
├── main.py              # CLI interface and main entry point
├── modules/             # Core analysis modules
│   ├── __init__.py     # Package initialization
│   ├── analyzer.py     # Main PDFAnalyzer class
│   ├── models.py       # Data classes and result containers
│   ├── pdf_libraries.py # PDF library testing logic
│   └── utils.py        # Utility functions (timeout handling, etc.)
├── files/
│   ├── docs/           # Directory containing PDF files to analyze
│   └── docs-info/      # Analysis results and logs
├── pyproject.toml      # Project configuration and dependencies
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd pdf-analyzer

# Install dependencies
uv sync

# Run the analyzer
uv run main.py
```

### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd pdf-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the analyzer
python main.py
```

## 📖 Usage

### Basic Usage

```bash
# Analyze all PDFs in the default directory (files/docs)
uv run main.py

# Analyze PDFs in a specific directory
uv run main.py --docs_dir /path/to/your/pdfs

# Limit the number of files to process
uv run main.py --limit 10

# Enable verbose logging
uv run main.py --verbose
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--docs_dir` | Directory containing PDF files | `files/docs` |
| `--info_dir` | Directory to store analysis results | `{docs_dir}-info` |
| `--report_output` | Output report file name | `pdf_analysis_report.json` |
| `--summary_output` | Output summary file name | Auto-generated |
| `--timeout` | Timeout in seconds for each library test | `30` |
| `--limit` | Limit number of PDF files to process | Process all |
| `--verbose`, `-v` | Enable verbose logging | `False` |
| `--quiet` | Quiet mode: `progress`, `logs`, or `all` | None |
| `--recommendation_only` | Show only recommended package and percentage | `False` |

### Examples

```bash
# Quick analysis with custom timeout
uv run main.py --timeout 60 --limit 5

# Silent analysis with custom output directory
uv run main.py --quiet all --info_dir results --docs_dir my_pdfs

# Verbose analysis with custom report name
uv run main.py --verbose --report_output my_analysis.json

# Show only recommendations
uv run main.py --recommendation_only
```

## 📊 Output

The analyzer generates several output files in the info directory:

### JSON Report (`pdf_analysis_report.json`)
Detailed analysis results including:
- Individual file test results
- Library performance metrics
- Error details and recommendations
- Overall statistics

### Summary Report (`pdf_analysis_summary.txt`)
Human-readable summary with:
- Overall statistics
- Library recommendations
- Common issues found
- Performance insights

### Log File (`pdf_test_results.log`)
Detailed execution log with:
- Processing steps
- Error messages
- Performance metrics
- Debug information (if verbose mode enabled)

## 🏗️ Architecture

The project follows a modular architecture for maintainability and testability:

### Core Modules

- **`main.py`**: CLI interface and argument parsing
- **`modules/analyzer.py`**: Main analysis orchestration and report generation
- **`modules/models.py`**: Data structures for test results
- **`modules/pdf_libraries.py`**: PDF library testing implementations
- **`modules/utils.py`**: Utility functions (timeout handling, threading)

### Key Classes

- **`PDFAnalyzer`**: Main analysis class that orchestrates the entire process
- **`PDFTestResult`**: Container for individual PDF test results

## 🔧 Development

### Adding New PDF Libraries

1. Add the library to `requirements.txt` and `pyproject.toml` (or use 'uv add [package]' and 'uv sync')
2. Implement test functions in `modules/pdf_libraries.py`
3. Update the analyzer to include the new library
4. Add corresponding result fields to `PDFTestResult`

### Adding New Features

- **New analysis features**: Modify `modules/analyzer.py`
- **New data models**: Add classes to `modules/models.py`
- **New utilities**: Add functions to `modules/utils.py`
- **New CLI options**: Modify `main.py`

### Testing

```bash
# Run with test files
uv run main.py --docs_dir test_files --verbose

# Test specific functionality
uv run main.py --limit 1 --timeout 10
```

## 📋 Dependencies

- **pypdf** (≥3.0.0): PDF manipulation library
- **PyMuPDF** (≥1.23.0): High-performance PDF processing
- **pdfplumber** (≥0.9.0): PDF text extraction and analysis
- **tqdm** (≥4.65.0): Progress bars and visual feedback

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

Copyright (C) 2025 Jeff Luster, mailto:jeff.luster96@gmail.com
License: GNU AFFERO GPL 3.0, https://www.gnu.org/licenses/agpl-3.0.html
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
Full license text can be found in the file "COPYING.txt".
Full copyright text can be found in the file "main.py".

## 🆘 Troubleshooting

### Common Issues

**"No PDF files found to analyze"**
- Ensure the `--docs_dir` contains PDF files
- Check file permissions
- Verify the directory path is correct

**Timeout errors**
- Increase the `--timeout` value for large or complex PDFs
- Check if PDFs are corrupted or password-protected

**Memory issues**
- Use `--limit` to process files in smaller batches
- Ensure sufficient system memory for large PDFs

### Getting Help

- Check the log file for detailed error information
- Use `--verbose` flag for additional debugging output
- Review the JSON report for specific file issues


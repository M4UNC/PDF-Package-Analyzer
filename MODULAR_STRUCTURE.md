# PDF Analyzer - Modular Structure

The original `pdf_analyzer.py` has been refactored into multiple, more manageable modules for better maintainability and organization.

## File Structure

```
pdf-analyzer/
├── main.py              # CLI interface and main entry point
├── analyzer.py          # Main PDFAnalyzer class
├── models.py            # Data classes and result containers
├── pdf_libraries.py     # PDF library testing logic (pypdf, PyMuPDF, pdfplumber)
├── utils.py             # Utility functions (timeout handling, etc.)
├── pdf_analyzer.py      # Original monolithic file (kept for reference)
└── requirements.txt     # Dependencies
```

## Module Descriptions

### `main.py`
- **Purpose**: CLI interface and entry point
- **Contains**: Argument parsing, main function, error handling
- **Dependencies**: `analyzer.py`

### `analyzer.py`
- **Purpose**: Core PDF analysis logic
- **Contains**: `PDFAnalyzer` class, analysis orchestration, report generation
- **Dependencies**: `models.py`, `pdf_libraries.py`, `utils.py`

### `models.py`
- **Purpose**: Data structures and result containers
- **Contains**: `PDFTestResult` class
- **Dependencies**: None (pure data classes)

### `pdf_libraries.py`
- **Purpose**: PDF library testing implementations
- **Contains**: Functions for testing with pypdf, PyMuPDF, and pdfplumber
- **Dependencies**: PDF libraries (pypdf, PyMuPDF, pdfplumber)

### `utils.py`
- **Purpose**: Utility functions
- **Contains**: Timeout handling, threading utilities
- **Dependencies**: Standard library only

## Usage

The modular version maintains the same CLI interface as the original:

```bash
# Run with default settings
uv run main.py

# Run with custom options
uv run main.py --books_dir library/books --limit 5 --verbose

# Get help
uv run main.py --help
```

## Benefits of Modular Structure

1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Individual modules can be tested in isolation
3. **Reusability**: Components can be imported and used independently
4. **Readability**: Smaller files are easier to understand and navigate
5. **Collaboration**: Multiple developers can work on different modules simultaneously

## Migration from Original

The original `pdf_analyzer.py` is preserved for reference. All functionality has been maintained in the modular version with identical behavior and CLI interface.

## Development

To add new features:
- **New PDF libraries**: Add functions to `pdf_libraries.py`
- **New data models**: Add classes to `models.py`
- **New utilities**: Add functions to `utils.py`
- **New analysis features**: Modify `analyzer.py`
- **New CLI options**: Modify `main.py`

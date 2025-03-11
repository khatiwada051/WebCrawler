# AI-Powered Web Scraping Agent

This project implements an intelligent web scraping agent capable of navigating websites, logging in when necessary, and extracting structured product data into JSON format.

## Features

- Modular, extensible architecture for web scraping
- Authentication support for accessing login-protected content
- AI-enhanced extraction for better data accuracy
- Configurable site-specific adapters
- Robust error handling and resilience
- Structured JSON output with schema validation

## Installation

### Prerequisites

- Python 3.9 or higher
- For browser automation: Chrome or Firefox browser
- For OCR capabilities: Tesseract OCR engine

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web-scraper-ai.git
cd web-scraper-ai
```

2. Create and activate a virtual environment:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install --no-deps -e .
pip install -r requirements.txt
```

4. Install browser drivers for Playwright:
```bash
playwright install --force
```

5. For NLP features, download the spaCy language model:
```bash
python -m spacy download en_core_web_sm
```

## Configuration

1. Copy the example configuration file:
```bash
cp config/config.example.json config/config.json
```

2. Edit `config/config.json` to customize the global settings.

3. Create site-specific configurations in the `config/sites/` directory.

## Usage

### Basic Usage

```bash
python -m scraper run --site example-store --output-dir ./data
```

### Login-required Sites

1. Set up secure credentials:
```bash
python -m scraper auth setup --site example-store
```

2. Run the scraper:
```bash
python -m scraper run --site example-store --with-login
```

### Advanced Usage

```bash
# Extract specific categories
python -m scraper run --site example-store --categories electronics,books

# Run with a specific proxy
python -m scraper run --site example-store --proxy http://user:pass@proxy.example.com:8080

# Schedule recurring jobs
python -m scraper schedule --site example-store --interval 12h
```

## Examples

The `examples/` directory contains complete examples for common websites:
- `examples/public_store/`: Simple example for a public e-commerce site
- `examples/auth_store/`: Example with login requirement
- `examples/dynamic_site/`: Example for JavaScript-heavy site

## Legal Considerations

Always ensure you have permission to scrape websites and comply with their Terms of Service. This tool should be used responsibly and ethically.

## License

MIT License - See LICENSE file for details
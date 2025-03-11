# Installation Guide

This guide provides detailed instructions for installing and setting up the AI-powered web scraping agent.

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- For browser automation: Chrome or Firefox browser
- For OCR capabilities: Tesseract OCR engine (optional)

## Basic Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/web-scraper-ai.git
cd web-scraper-ai
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to avoid conflicts with other Python packages.

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install the Package

#### Basic Installation
```bash
pip install -e .
```

#### With AI Features
```bash
pip install -e ".[ai]"
```

#### With Database Support
```bash
pip install -e ".[db]"
```

#### With Development Tools
```bash
pip install -e ".[dev]"
```

#### Full Installation (All Features)
```bash
pip install -e ".[ai,db,dev]"
```

### 4. Install Browser Drivers for Playwright

If you plan to use browser automation (required for login functionality and JavaScript-heavy sites):

```bash
playwright install
```

### 5. Download spaCy Language Model

If you plan to use AI-enhanced extraction:

```bash
python -m spacy download en_core_web_md
```

## Configuration

### 1. Create Configuration Files

Copy the example configuration files:

```bash
mkdir -p config/sites
cp config/config.example.json config/config.json
```

### 2. Edit Configuration

Edit `config/config.json` to customize global settings.

Create site-specific configuration files in the `config/sites/` directory. For example:

```bash
cp config/sites/example-store.json config/sites/your-site.json
```

Then edit `config/sites/your-site.json` to match the structure of the site you want to scrape.

## Testing the Installation

Run a simple example to verify that everything is working:

```bash
python examples/simple_example.py
```

## Troubleshooting

### Common Issues

#### Missing Dependencies

If you encounter errors about missing dependencies, try installing the full set of dependencies:

```bash
pip install -r requirements.txt
```

#### Browser Automation Issues

If you encounter issues with browser automation:

1. Make sure you have installed the browser drivers:
   ```bash
   playwright install
   ```

2. Try running with a visible browser (non-headless) for debugging:
   Edit `config/config.json` and set:
   ```json
   "browser_automation": {
     "enabled": true,
     "headless": false,
     ...
   }
   ```

#### Permission Issues

If you encounter permission issues when saving files:

1. Make sure the output directory specified in `config/config.json` exists and is writable.
2. On Linux/macOS, you might need to adjust permissions:
   ```bash
   mkdir -p data
   chmod 755 data
   ```

## Advanced Installation

### Installing Tesseract OCR (Optional)

For OCR capabilities (extracting text from images):

#### On Windows:
1. Download and install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Add the Tesseract installation directory to your PATH environment variable.

#### On macOS:
```bash
brew install tesseract
```

#### On Linux:
```bash
sudo apt-get install tesseract-ocr
```

### Using with Docker (Optional)

A Dockerfile is provided for containerized deployment:

```bash
docker build -t web-scraper-ai .
docker run -v $(pwd)/config:/app/config -v $(pwd)/data:/app/data web-scraper-ai scraper run --site example-store
``` 
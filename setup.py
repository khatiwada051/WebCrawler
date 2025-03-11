"""
Setup script for the AI-powered web scraping agent.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-web-scraper",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered web scraping agent with authentication capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/web-scraper-ai",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "aiohttp>=3.9.1",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.2",
        "lxml>=4.9.3",
        "pydantic>=2.5.2",
        "jsonschema>=4.20.0",
        "python-dateutil>=2.8.2",
        "spacy>=3.7.2",
        "cryptography>=41.0.5",
        "keyring>=24.2.0",
        "tqdm>=4.66.1",
        "python-dotenv>=1.0.0",
        "tenacity>=8.2.3",
    ],
    extras_require={
        "ai": [
            "transformers>=4.35.2",
            "pillow>=10.1.0",
            "pytesseract>=0.3.10",
        ],
        "db": [
            "pymongo>=4.6.0",
            "redis>=5.0.1",
        ],
        "dev": [
            "pytest>=7.4.3",
            "black>=23.11.0",
            "flake8>=6.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "scraper=scraper.__main__:main",
        ],
    },
) 
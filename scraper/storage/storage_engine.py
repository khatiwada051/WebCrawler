"""
Storage Engine - Component responsible for managing data persistence and file operations.
"""

import logging
import json
import os
import time
from typing import Dict, List, Any, Optional, Union
import gzip
from datetime import datetime

from scraper.utils.exceptions import StorageException

logger = logging.getLogger(__name__)

class StorageEngine:
    """Manages data storage operations for scraped data."""
    
    def __init__(
        self,
        output_dir: str,
        file_format: str = "json",
        compress: bool = False,
        append_mode: bool = False,
        max_items_per_file: int = 1000
    ):
        """
        Initialize the storage engine.
        
        Args:
            output_dir: Directory to store output files
            file_format: Format for output files ('json' or 'jsonl')
            compress: Whether to compress output files with gzip
            append_mode: Whether to append to existing files
            max_items_per_file: Maximum number of items per file (for batched output)
        """
        self.output_dir = output_dir
        self.file_format = file_format.lower()
        self.compress = compress
        self.append_mode = append_mode
        self.max_items_per_file = max_items_per_file
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # State tracking
        self.items_written = 0
        self.files_created = 0
    
    def save(self, data: Dict[str, Any], filename_prefix: str = None) -> str:
        """
        Save data to storage.
        
        Args:
            data: Data to save
            filename_prefix: Optional prefix for the output filename
            
        Returns:
            Path to the saved file
        """
        try:
            # Generate filename if not provided
            if not filename_prefix:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_prefix = f"scrape_{timestamp}"
            
            # Determine full path
            file_extension = ".json.gz" if self.compress else ".json"
            if self.file_format == "jsonl":
                file_extension = ".jsonl.gz" if self.compress else ".jsonl"
                
            filepath = os.path.join(self.output_dir, f"{filename_prefix}{file_extension}")
            
            # Save the data
            if self.file_format == "json":
                self._save_json(data, filepath)
            elif self.file_format == "jsonl":
                self._save_jsonl(data, filepath)
            else:
                raise StorageException(f"Unsupported file format: {self.file_format}")
            
            logger.info(f"Data saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            raise StorageException(f"Failed to save data: {str(e)}")
    
    def _save_json(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Save data in JSON format.
        
        Args:
            data: Data to save
            filepath: Path to the output file
        """
        mode = 'a' if self.append_mode and os.path.exists(filepath) else 'w'
        
        if self.compress:
            with gzip.open(filepath, mode + 't', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                self.items_written += 1
        else:
            with open(filepath, mode, encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                self.items_written += 1
        
        self.files_created += 1
    
    def _save_jsonl(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Save data in JSON Lines format (one JSON object per line).
        
        Args:
            data: Data to save
            filepath: Path to the output file
        """
        mode = 'a' if self.append_mode and os.path.exists(filepath) else 'w'
        
        # Handle both single items and lists of items
        items_to_write = []
        
        if 'products' in data:
            # Multiple products in the data
            for product in data['products']:
                # Create a complete record for each product
                record = {
                    "schema_version": data.get('schema_version', '1.0'),
                    "timestamp": data.get('timestamp', datetime.now().isoformat()),
                    "source": data.get('source', {}),
                    "product": product
                }
                items_to_write.append(record)
        else:
            # Single product or other data structure
            items_to_write.append(data)
        
        if self.compress:
            with gzip.open(filepath, mode + 't', encoding='utf-8') as f:
                for item in items_to_write:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    self.items_written += 1
        else:
            with open(filepath, mode, encoding='utf-8') as f:
                for item in items_to_write:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    self.items_written += 1
        
        self.files_created += 1
    
    def save_batch(
        self, 
        data_items: List[Dict[str, Any]], 
        filename_prefix: str = None,
        batch_size: int = None
    ) -> List[str]:
        """
        Save a batch of data items, potentially splitting into multiple files.
        
        Args:
            data_items: List of data items to save
            filename_prefix: Optional prefix for the output filenames
            batch_size: Optional override for max_items_per_file
            
        Returns:
            List of paths to the saved files
        """
        try:
            # Generate base filename if not provided
            if not filename_prefix:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_prefix = f"batch_{timestamp}"
            
            # Use instance batch size if not specified
            batch_size = batch_size or self.max_items_per_file
            
            # Split into batches
            batches = [data_items[i:i + batch_size] for i in range(0, len(data_items), batch_size)]
            
            # Save each batch
            saved_files = []
            for i, batch in enumerate(batches):
                batch_filename = f"{filename_prefix}_part{i+1}"
                
                # Create batch data structure
                batch_data = {
                    "schema_version": "1.0",
                    "timestamp": datetime.now().isoformat(),
                    "source": {
                        "batch_id": f"{filename_prefix}",
                        "batch_part": i+1,
                        "total_parts": len(batches)
                    },
                    "products": batch
                }
                
                # Save this batch
                filepath = self.save(batch_data, batch_filename)
                saved_files.append(filepath)
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save batch data: {str(e)}")
            raise StorageException(f"Failed to save batch data: {str(e)}")
    
    def save_incremental(
        self, 
        data: Dict[str, Any], 
        key_field: str,
        collection_name: str
    ) -> None:
        """
        Save data with incremental updates, avoiding duplicates.
        
        Args:
            data: Data to save
            key_field: Field to use as unique identifier
            collection_name: Name of the collection to save to
        """
        try:
            # Determine the collection file path
            collection_path = os.path.join(self.output_dir, f"{collection_name}.json")
            
            # Load existing data if file exists
            existing_data = {}
            if os.path.exists(collection_path):
                with open(collection_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse existing file {collection_path}, treating as empty")
                        existing_data = {}
            
            # Extract products to update
            products_to_update = []
            if 'product' in data:
                products_to_update = [data['product']]
            elif 'products' in data:
                products_to_update = data['products']
            else:
                logger.warning("No products found in data, nothing to update")
                return
            
            # Create or update the collection structure
            if not existing_data:
                # New collection
                collection = {
                    "schema_version": data.get('schema_version', '1.0'),
                    "last_updated": datetime.now().isoformat(),
                    "source": data.get('source', {}),
                    "products": {}
                }
            else:
                # Existing collection
                collection = existing_data
                collection['last_updated'] = datetime.now().isoformat()
            
            # Ensure products is a dictionary
            if 'products' not in collection or not isinstance(collection['products'], dict):
                collection['products'] = {}
            
            # Update products
            updated_count = 0
            for product in products_to_update:
                if key_field not in product:
                    logger.warning(f"Product missing key field '{key_field}', skipping")
                    continue
                    
                key = product[key_field]
                collection['products'][key] = product
                updated_count += 1
            
            # Save the updated collection
            with open(collection_path, 'w', encoding='utf-8') as f:
                json.dump(collection, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Updated {updated_count} products in collection {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to save incremental data: {str(e)}")
            raise StorageException(f"Failed to save incremental data: {str(e)}")
    
    def load(self, filepath: str) -> Dict[str, Any]:
        """
        Load data from storage.
        
        Args:
            filepath: Path to the file to load
            
        Returns:
            Loaded data
        """
        try:
            if not os.path.exists(filepath):
                raise StorageException(f"File not found: {filepath}")
            
            is_compressed = filepath.endswith('.gz')
            is_jsonl = filepath.endswith('.jsonl') or filepath.endswith('.jsonl.gz')
            
            if is_jsonl:
                # Load JSONL file (one JSON object per line)
                data = []
                if is_compressed:
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        for line in f:
                            data.append(json.loads(line))
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            data.append(json.loads(line))
                return data
            else:
                # Load standard JSON file
                if is_compressed:
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load data from {filepath}: {str(e)}")
            raise StorageException(f"Failed to load data from {filepath}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Create a storage engine
    storage = StorageEngine(
        output_dir="./data",
        file_format="json",
        compress=False
    )
    
    # Sample data
    sample_data = {
        "schema_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "source": {
            "site": "example-store",
            "url": "https://example.com/products/123",
            "scrape_id": "test-scrape-123"
        },
        "product": {
            "id": "PROD123",
            "name": "Example Product",
            "price": {"current": 99.99, "currency": "USD"},
            "availability": "in_stock",
            "description": "This is an example product"
        }
    }
    
    # Save the data
    filepath = storage.save(sample_data, "example_product")
    print(f"Data saved to {filepath}")
    
    # Load the data back
    loaded_data = storage.load(filepath)
    print("Loaded data:", json.dumps(loaded_data, indent=2)) 
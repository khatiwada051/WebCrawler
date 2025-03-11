"""
JSON Formatter - Component responsible for transforming extracted data into standardized JSON format.
"""

import logging
import json
from typing import Dict, List, Any, Union
import datetime
import uuid
import jsonschema
from dateutil import parser as date_parser

from scraper.utils.exceptions import FormattingException

logger = logging.getLogger(__name__)

class JSONFormatter:
    """Transforms extracted data into standardized JSON format with validation."""
    
    def __init__(self, schema_path: str = None):
        """
        Initialize the JSON formatter.
        
        Args:
            schema_path: Optional path to a JSON schema file for validation
        """
        self.schema = None
        
        if schema_path:
            try:
                with open(schema_path, 'r') as f:
                    self.schema = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load schema from {schema_path}: {str(e)}")
    
    def format(
        self, 
        data: Union[Dict[str, Any], List[Dict[str, Any]]], 
        site_id: str, 
        url: str
    ) -> Dict[str, Any]:
        """
        Format extracted data into a standardized JSON structure.
        
        Args:
            data: Raw extracted data
            site_id: ID of the site the data was extracted from
            url: URL the data was extracted from
            
        Returns:
            Formatted JSON data as a dictionary
        """
        try:
            # Handle single item or list of items
            if isinstance(data, list):
                formatted_products = [self._format_product(item, site_id, url) for item in data]
                result = {
                    "schema_version": "1.0",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": {
                        "site": site_id,
                        "url": url,
                        "scrape_id": str(uuid.uuid4())
                    },
                    "products": formatted_products
                }
            else:
                formatted_product = self._format_product(data, site_id, url)
                result = {
                    "schema_version": "1.0",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": {
                        "site": site_id,
                        "url": url,
                        "scrape_id": str(uuid.uuid4())
                    },
                    "product": formatted_product
                }
            
            # Validate against schema if available
            if self.schema:
                try:
                    jsonschema.validate(instance=result, schema=self.schema)
                except jsonschema.exceptions.ValidationError as e:
                    logger.warning(f"Data doesn't match schema: {str(e)}")
                    # Continue anyway but log the warning
            
            return result
            
        except Exception as e:
            logger.error(f"Formatting failed: {str(e)}")
            raise FormattingException(f"Failed to format data: {str(e)}")
    
    def _format_product(self, product: Dict[str, Any], site_id: str, url: str) -> Dict[str, Any]:
        """
        Format a single product entry.
        
        Args:
            product: Raw product data
            site_id: ID of the site the data was extracted from
            url: URL the data was extracted from
            
        Returns:
            Formatted product data
        """
        # Start with a copy of the original data
        formatted = {}
        
        # Handle standard fields
        self._copy_field(product, formatted, 'id')
        self._copy_field(product, formatted, 'name')
        self._copy_field(product, formatted, 'brand')
        self._copy_field(product, formatted, 'description')
        
        # Format price data
        if 'price' in product:
            formatted['price'] = self._format_price(product['price'])
        
        # Format availability
        if 'availability' in product:
            formatted['availability'] = self._normalize_availability(product['availability'])
        
        # Format categories
        if 'categories' in product:
            formatted['categories'] = product['categories'] if isinstance(product['categories'], list) else [product['categories']]
        
        # Format images
        if 'image_url' in product:
            # Single image URL format
            formatted['images'] = [
                {"url": product['image_url'], "type": "primary"}
            ]
        elif 'images' in product:
            # Already structured format
            formatted['images'] = product['images']
        
        # Format specifications
        if 'specifications' in product:
            formatted['specifications'] = product['specifications']
        
        # Copy any metadata
        if 'metadata' in product:
            formatted['metadata'] = product['metadata']
        
        # Add URL if not present
        if 'url' not in formatted and 'url' in product:
            formatted['url'] = product['url']
        
        # Include any other fields not explicitly handled
        for key, value in product.items():
            if key not in formatted and key not in ['image_url', 'timestamp']:
                formatted[key] = value
        
        return formatted
    
    def _copy_field(self, source: Dict[str, Any], dest: Dict[str, Any], field: str) -> None:
        """Copy a field from source to destination if it exists."""
        if field in source and source[field]:
            dest[field] = source[field]
    
    def _format_price(self, price_data: Any) -> Dict[str, Any]:
        """Format price data to a consistent structure."""
        if isinstance(price_data, dict):
            # Already in a structured format
            return price_data
        elif isinstance(price_data, (int, float)):
            # Simple numeric price
            return {"current": float(price_data)}
        elif isinstance(price_data, str):
            # Try to parse from string
            try:
                # Remove currency symbols and commas
                cleaned = price_data.replace('$', '').replace('€', '').replace('£', '').replace(',', '')
                return {"current": float(cleaned)}
            except ValueError:
                logger.warning(f"Could not parse price from string: {price_data}")
                return {"raw_price": price_data}
        else:
            # Unrecognized format
            logger.warning(f"Unrecognized price format: {type(price_data)}")
            return {"raw_price": str(price_data)}
    
    def _normalize_availability(self, availability: str) -> str:
        """Normalize availability status to standard values."""
        if not availability:
            return "unknown"
        
        availability = str(availability).lower()
        
        # Map common phrases to standard values
        if any(term in availability for term in ['in stock', 'instock', 'available', 'in_stock']):
            return "in_stock"
        elif any(term in availability for term in ['out of stock', 'outofstock', 'sold out', 'unavailable', 'out_of_stock']):
            return "out_of_stock"
        elif any(term in availability for term in ['preorder', 'pre-order', 'pre order']):
            return "preorder"
        elif any(term in availability for term in ['backorder', 'back order', 'back-order']):
            return "backorder"
        
        # Return as is if no match
        return availability
    
    def get_default_schema(self) -> Dict[str, Any]:
        """
        Get the default JSON schema for validation.
        
        Returns:
            Default schema as a dictionary
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["schema_version", "timestamp", "source"],
            "properties": {
                "schema_version": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "source": {
                    "type": "object",
                    "required": ["site", "url", "scrape_id"],
                    "properties": {
                        "site": {"type": "string"},
                        "url": {"type": "string", "format": "uri"},
                        "scrape_id": {"type": "string"}
                    }
                },
                "product": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "brand": {"type": "string"},
                        "price": {
                            "type": "object",
                            "properties": {
                                "current": {"type": "number"},
                                "currency": {"type": "string"},
                                "original": {"type": "number"},
                                "discount_percentage": {"type": "integer"}
                            }
                        },
                        "availability": {"type": "string"},
                        "description": {"type": "string"},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "images": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["url"],
                                "properties": {
                                    "url": {"type": "string"},
                                    "type": {"type": "string"}
                                }
                            }
                        },
                        "specifications": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        },
                        "variants": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "attributes": {"type": "object"},
                                    "price": {"type": "number"},
                                    "availability": {"type": "string"}
                                }
                            }
                        },
                        "metadata": {"type": "object"}
                    }
                },
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            # (Same as product properties above)
                        }
                    }
                }
            },
            "oneOf": [
                {"required": ["product"]},
                {"required": ["products"]}
            ]
        }
    
    def save_schema(self, path: str) -> None:
        """
        Save the default schema to a file.
        
        Args:
            path: Path to save the schema to
        """
        schema = self.get_default_schema()
        try:
            with open(path, 'w') as f:
                json.dump(schema, f, indent=2)
            logger.info(f"Schema saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save schema to {path}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Create a formatter
    formatter = JSONFormatter()
    
    # Sample extracted data
    sample_data = {
        "name": "Example Product",
        "price": "$99.99",
        "brand": "Example Brand",
        "description": "This is an example product description.",
        "image_url": "https://example.com/images/product.jpg",
        "specifications": {
            "Color": "Red",
            "Size": "Medium",
            "Weight": "2.5 kg"
        },
        "availability": "In Stock"
    }
    
    # Format the data
    formatted_data = formatter.format(sample_data, "example-store", "https://example.com/product/123")
    
    # Print the result
    print(json.dumps(formatted_data, indent=2)) 
"""
Product Search Tool using Pinecone Vector Database
This tool provides semantic search functionality for products with price filtering.
"""

import json
import os
from typing import Optional, List, Dict, Any
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from pydantic import BaseModel, Field
from langchain_core.tools import tool

class ProductSearchInput(BaseModel):
    """Input schema for product search tool."""
    query: str = Field(description="Search query for products (e.g., 'Samsung AC', 'gaming laptop', 'wireless headphones')")
    top_k: int = Field(default=5, description="Number of products to return (1-20)", ge=1, le=20)
    price_min: Optional[float] = Field(default=None, description="Minimum price filter in rupees (e.g., 15000)")
    price_max: Optional[float] = Field(default=None, description="Maximum price filter in rupees (e.g., 100000)")

class ProductSearchTool:
    """Product search tool using Pinecone vector database."""
    
    def __init__(self):
        # Pinecone configuration - prioritize environment variable
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if not self.pinecone_api_key:
            print("⚠️  Warning: No PINECONE_API_KEY found in environment variables")
            self.pinecone_api_key = "pcsk_3G8JGb_R6CJ2jquYjF1Rvx9HKtDGhZz24hqA5vAa6stE3LQ5AHPM3Ayr2NEKFJRH4YYgBe"
            
        self.pinecone_index_name = "all-products-lotus"
        self.pinecone_host = "https://all-products-lotus-imbj1oj.svc.aped-4627-b74a.pinecone.io"
        
        # Initialize components
        self.model = None
        self.index = None
        self.is_available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize the sentence transformer model and Pinecone index."""
        try:
            # Load sentence transformer model
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Sentence transformer model loaded successfully!")
            
            # Initialize Pinecone
            pc = Pinecone(api_key=self.pinecone_api_key)
            self.index = pc.Index(self.pinecone_index_name, host=self.pinecone_host)
            
            # Test the connection
            test_query = self.model.encode("test").tolist()
            self.index.query(vector=test_query, top_k=1, include_metadata=False)
            
            self.is_available = True
            print("✅ Pinecone vector search initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing vector search: {e}")
            self.is_available = False
    
    def search_products(self, query: str, top_k: int = 5, price_min: Optional[float] = None, price_max: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for products using vector similarity and price filtering.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            price_min: Minimum price filter
            price_max: Maximum price filter
            
        Returns:
            List of product dictionaries with metadata
        """
        if not self.is_available:
            return []
            
        try:
            # Embed the query
            query_vec = self.model.encode(query).tolist()
            
            # Query Pinecone vector database
            response = self.index.query(
                vector=query_vec,
                top_k=top_k * 10,  # Get many more results for better diversity
                include_metadata=True
            )
            
            # Filter and format results with brand diversity
            results = []
            brand_counts = {}  # Track brands to ensure diversity
            
            for match in response.matches:
                metadata = match.metadata or {}
                
                # Validate product name
                product_name = metadata.get("product_name", "").strip()
                if not product_name or product_name.lower() in ['unknown', 'n/a', 'null']:
                    continue
                
                # Extract brand from product name for diversity
                brand = "Unknown"
                product_name_lower = product_name.lower()
                if any(b in product_name_lower for b in ['samsung']):
                    brand = "Samsung"
                elif any(b in product_name_lower for b in ['oneplus', 'one plus']):
                    brand = "OnePlus"
                elif any(b in product_name_lower for b in ['xiaomi', 'redmi', 'mi ']):
                    brand = "Xiaomi"
                elif any(b in product_name_lower for b in ['oppo']):
                    brand = "Oppo"
                elif any(b in product_name_lower for b in ['vivo']):
                    brand = "Vivo"
                elif any(b in product_name_lower for b in ['iphone', 'apple']):
                    brand = "Apple"
                elif any(b in product_name_lower for b in ['nothing']):
                    brand = "Nothing"
                elif any(b in product_name_lower for b in ['realme']):
                    brand = "Realme"
                elif any(b in product_name_lower for b in ['motorola']):
                    brand = "Motorola"
                elif any(b in product_name_lower for b in ['philips']):
                    brand = "Philips"
                elif any(b in product_name_lower for b in ['braun']):
                    brand = "Braun"
                elif any(b in product_name_lower for b in ['panasonic']):
                    brand = "Panasonic"
                elif any(b in product_name_lower for b in ['havells']):
                    brand = "Havells"
                elif any(b in product_name_lower for b in ['syska']):
                    brand = "Syska"
                elif any(b in product_name_lower for b in ['nova']):
                    brand = "Nova"
                elif any(b in product_name_lower for b in ['kemei']):
                    brand = "Kemei"
                elif any(b in product_name_lower for b in ['lg']):
                    brand = "LG"
                elif any(b in product_name_lower for b in ['daikin']):
                    brand = "Daikin"
                elif any(b in product_name_lower for b in ['voltas']):
                    brand = "Voltas"
                elif any(b in product_name_lower for b in ['hitachi']):
                    brand = "Hitachi"
                elif any(b in product_name_lower for b in ['carrier']):
                    brand = "Carrier"
                elif any(b in product_name_lower for b in ['blue star', 'bluestar']):
                    brand = "Blue Star"
                elif any(b in product_name_lower for b in ['godrej']):
                    brand = "Godrej"
                elif any(b in product_name_lower for b in ['whirlpool']):
                    brand = "Whirlpool"
                elif any(b in product_name_lower for b in ['lloyd']):
                    brand = "Lloyd"
                elif any(b in product_name_lower for b in ['o general', 'ogeneral']):
                    brand = "O General"
                elif any(b in product_name_lower for b in ['mitsubishi']):
                    brand = "Mitsubishi"
                elif any(b in product_name_lower for b in ['haier']):
                    brand = "Haier"
                
                # Extract and validate price
                try:
                    price_val = float(metadata.get("price", 0))
                    if price_val <= 0:
                        continue
                except (ValueError, TypeError):
                    continue
                
                # Apply price filtering
                if price_min is not None and price_val < price_min:
                    continue
                if price_max is not None and price_val > price_max:
                    continue
                
                # Enforce brand diversity - but allow more products if needed
                # For small result sets (top_k <= 5), allow up to 3 products per brand
                # For larger result sets, limit to 2 per brand for better diversity
                max_per_brand = 3 if top_k <= 5 else 2
                if brand_counts.get(brand, 0) >= max_per_brand:
                    continue
                
                # Format result
                product = {
                    "id": match.id,
                    "product_id": metadata.get("product_id", match.id),
                    "score": round(match.score, 4),
                    "product_name": product_name,
                    "brand": brand,
                    "sku": metadata.get("sku", "N/A"),
                    "price": price_val,
                    "url": metadata.get("url", "").strip(),
                    "image_url": metadata.get("image_url", "").strip(),
                    "description": metadata.get("text", "")[:200] + "..." if metadata.get("text", "") else ""
                }
                
                results.append(product)
                
                # Update brand count for diversity
                brand_counts[brand] = brand_counts.get(brand, 0) + 1
                
                # Stop when we have enough results
                if len(results) >= top_k:
                    break
            
            # If we don't have enough results due to brand diversity constraints, 
            # do a second pass with relaxed brand limits
            if len(results) < top_k and len(response.matches) > len(results):
                print(f"🔄 Only found {len(results)} products with brand diversity. Relaxing constraints to reach {top_k} products...")
                
                # Reset and try again with higher brand limits
                results = []
                brand_counts = {}
                max_per_brand = top_k  # Allow more products per brand
                
                for match in response.matches:
                    metadata = match.metadata or {}
                    
                    # Validate product name
                    product_name = metadata.get("product_name", "").strip()
                    if not product_name or product_name.lower() in ['unknown', 'n/a', 'null']:
                        continue
                    
                    # Extract brand from product name for diversity
                    brand = "Unknown"
                    product_name_lower = product_name.lower()
                    if any(b in product_name_lower for b in ['samsung']):
                        brand = "Samsung"
                    elif any(b in product_name_lower for b in ['oneplus', 'one plus']):
                        brand = "OnePlus"
                    elif any(b in product_name_lower for b in ['xiaomi', 'redmi', 'mi ']):
                        brand = "Xiaomi"
                    elif any(b in product_name_lower for b in ['oppo']):
                        brand = "Oppo"
                    elif any(b in product_name_lower for b in ['vivo']):
                        brand = "Vivo"
                    elif any(b in product_name_lower for b in ['iphone', 'apple']):
                        brand = "Apple"
                    elif any(b in product_name_lower for b in ['nothing']):
                        brand = "Nothing"
                    elif any(b in product_name_lower for b in ['realme']):
                        brand = "Realme"
                    elif any(b in product_name_lower for b in ['motorola']):
                        brand = "Motorola"
                    elif any(b in product_name_lower for b in ['philips']):
                        brand = "Philips"
                    elif any(b in product_name_lower for b in ['braun']):
                        brand = "Braun"
                    elif any(b in product_name_lower for b in ['panasonic']):
                        brand = "Panasonic"
                    elif any(b in product_name_lower for b in ['havells']):
                        brand = "Havells"
                    elif any(b in product_name_lower for b in ['syska']):
                        brand = "Syska"
                    elif any(b in product_name_lower for b in ['nova']):
                        brand = "Nova"
                    elif any(b in product_name_lower for b in ['kemei']):
                        brand = "Kemei"
                    elif any(b in product_name_lower for b in ['lg']):
                        brand = "LG"
                    elif any(b in product_name_lower for b in ['daikin']):
                        brand = "Daikin"
                    elif any(b in product_name_lower for b in ['voltas']):
                        brand = "Voltas"
                    elif any(b in product_name_lower for b in ['hitachi']):
                        brand = "Hitachi"
                    elif any(b in product_name_lower for b in ['carrier']):
                        brand = "Carrier"
                    elif any(b in product_name_lower for b in ['blue star', 'bluestar']):
                        brand = "Blue Star"
                    elif any(b in product_name_lower for b in ['godrej']):
                        brand = "Godrej"
                    elif any(b in product_name_lower for b in ['whirlpool']):
                        brand = "Whirlpool"
                    elif any(b in product_name_lower for b in ['lloyd']):
                        brand = "Lloyd"
                    elif any(b in product_name_lower for b in ['o general', 'ogeneral']):
                        brand = "O General"
                    elif any(b in product_name_lower for b in ['mitsubishi']):
                        brand = "Mitsubishi"
                    elif any(b in product_name_lower for b in ['haier']):
                        brand = "Haier"
                    
                    # Extract and validate price
                    try:
                        price_val = float(metadata.get("price", 0))
                        if price_val <= 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    # Apply price filtering
                    if price_min is not None and price_val < price_min:
                        continue
                    if price_max is not None and price_val > price_max:
                        continue
                    
                    # Relaxed brand diversity - allow more products per brand
                    if brand_counts.get(brand, 0) >= max_per_brand:
                        continue
                    
                    # Format result
                    product = {
                        "id": match.id,
                        "product_id": metadata.get("product_id", match.id),
                        "score": round(match.score, 4),
                        "product_name": product_name,
                        "brand": brand,
                        "sku": metadata.get("sku", "N/A"),
                        "price": price_val,
                        "url": metadata.get("url", "").strip(),
                        "image_url": metadata.get("image_url", "").strip(),
                        "description": metadata.get("text", "")[:200] + "..." if metadata.get("text", "") else ""
                    }
                    
                    results.append(product)
                    
                    # Update brand count for diversity
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1
                    
                    # Stop when we have enough results
                    if len(results) >= top_k:
                        break
            
            return results
            
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []
    
    def format_results(self, results: List[Dict[str, Any]], query: str = "", top_k: int = 5, price_min: Optional[float] = None, price_max: Optional[float] = None) -> str:
        """Format search results for JSON response."""
        if not results:
            return json.dumps({
                "search_query": query,
                "total_found": 0,
                "price_filter": {
                    "min": price_min,
                    "max": price_max
                },
                "products": [],
                "search_metadata": {
                    "top_k_requested": top_k,
                    "has_price_filter": price_min is not None or price_max is not None,
                    "no_results": True
                }
            }, ensure_ascii=False, indent=2, separators=(',', ': '))
        
        # Format products for JSON response
        products = []
        for product in results:
            # Extract features from description
            description = product.get('description', '')
            features = []
            if description and len(description) > 20:
                # Clean and extract meaningful features
                clean_desc = description.replace('|', ',').replace(':', ',')
                parts = [f.strip() for f in clean_desc.split(',') if f.strip()]
                
                for feature in parts:
                    cleaned = feature.strip().rstrip('.,;:')
                    if (5 <= len(cleaned) <= 40 and 
                        not any(skip in cleaned.lower() for skip in ['processor:', 'operating system:', 'camera back:', 'internal memory:', 'network:']) and
                        not any(invalid in cleaned.lower() for invalid in ['undefined', 'null', 'n/a', '...'])):
                        features.append(cleaned)
                        if len(features) >= 3:
                            break
            
            # Add default features if needed
            if len(features) < 3:
                product_name_lower = product.get('product_name', '').lower()
                if any(phone in product_name_lower for phone in ['smartphone', 'phone', 'mobile', 'galaxy', 'redmi', 'oneplus']):
                    default_features = ["High Resolution Camera", "Fast Performance", "Long Battery Life"]
                elif any(audio in product_name_lower for audio in ['earphone', 'headphone', 'buds', 'speaker']):
                    default_features = ["Premium Sound Quality", "Wireless Connectivity", "Comfortable Design"]
                elif any(tv in product_name_lower for tv in ['tv', 'television', 'smart tv']):
                    default_features = ["Full HD Display", "Smart Features", "Energy Efficient"]
                elif any(laptop in product_name_lower for laptop in ['laptop', 'computer']):
                    default_features = ["High Performance", "Portable Design", "Latest Technology"]
                else:
                    default_features = ["Latest Technology", "High Quality Build", "Great Value for Money"]
                
                needed = 3 - len(features)
                features.extend(default_features[:needed])
            
            # Construct product URL
            product_url = ""
            if product.get('url'):
                product_id = product.get('product_id') or product.get('id', '')
                if product_id:
                    product_url = f"https://www.lotuselectronics.com/product/{product.get('url')}/{product_id}"
            
            # Validate and fix image URL if needed
            original_image_url = product.get('image_url', '')
            product_image_url = original_image_url
            
            # If no image URL, generate one using product ID
            if not product_image_url and product.get('product_id'):
                product_id_str = str(product.get('product_id', ''))
                if product_id_str.isdigit():
                    product_image_url = f"https://cdn.lotuselectronics.com/webpimages/{product_id_str}IM.webp"
                    print(f"🖼️  Generated image URL for product {product_id_str}: {product_image_url}")
            
            # Add category validation to catch mismatched products
            product_name_lower = product['product_name'].lower()
            query_lower = query.lower()
            
            # Check for category mismatches (e.g., asking for smartphones but getting washing machines)
            smartphone_keywords = ['smartphone', 'mobile', 'phone', 'android', 'iphone', 'oneplus', 'samsung galaxy', 'oppo', 'vivo', 'xiaomi']
            washing_machine_keywords = ['washing machine', 'washer', 'laundry']
            laptop_keywords = ['laptop', 'notebook', 'computer']
            tv_keywords = ['tv', 'television', 'led tv', 'smart tv']
            
            is_query_for_smartphones = any(keyword in query_lower for keyword in smartphone_keywords)
            is_product_washing_machine = any(keyword in product_name_lower for keyword in washing_machine_keywords)
            
            if is_query_for_smartphones and is_product_washing_machine:
                print(f"🚨 CATEGORY MISMATCH DETECTED:")
                print(f"   Query: '{query}' (smartphone search)")
                print(f"   Product: '{product['product_name']}' (washing machine)")
                print(f"   Skipping this product due to category mismatch")
                continue  # Skip this product
            
            products.append({
                "product_id":product.get('product_id') or product.get('id', ''),
                "product_name": product['product_name'],
                "product_mrp": f"₹{product['price']:,.0f}",
                "product_url": product_url,
                "product_image": product_image_url,
                "features": features[:4]
            })
        
        # Return raw product data for LLM to process intelligently
        response = {
            "search_query": query,
            "total_found": len(results),
            "price_filter": {
                "min": price_min,
                "max": price_max
            },
            "products": products,
            "search_metadata": {
                "top_k_requested": top_k,
                "has_price_filter": price_min is not None or price_max is not None
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2, separators=(',', ': '))

# Initialize the product search tool instance
product_search_instance = ProductSearchTool()

@tool("search_products", args_schema=ProductSearchInput, return_direct=False)
def search_products(query: str, top_k: int = 5, price_min: Optional[float] = None, price_max: Optional[float] = None) -> str:
    """
    Search for products using semantic similarity with optional price filtering.
    
    This tool searches through a large product database using AI-powered semantic search.
    You can filter results by price range and specify how many products to return.
    
    Args:
        query: What product you're looking for (e.g., "Samsung AC", "gaming laptop", "wireless headphones")
        top_k: How many products to show (default: 5, max: 20)
        price_min: Minimum price in rupees (optional)
        price_max: Maximum price in rupees (optional)
    
    Returns:
        Formatted list of matching products with prices, descriptions, and links
    
    Example usage:
        - search_products("Samsung AC", top_k=3, price_min=15000, price_max=50000)
        - search_products("gaming laptop under 80010", top_k=5, price_max=80010)
        - search_products("wireless headphones", top_k=10)
    """
    try:
        # Perform the search
        results = product_search_instance.search_products(
            query=query,
            top_k=top_k,
            price_min=price_min,
            price_max=price_max
        )
        
        # Format and return results with search parameters
        return product_search_instance.format_results(
            results=results,
            query=query,
            top_k=top_k,
            price_min=price_min,
            price_max=price_max
        )
        
    except Exception as e:
        return f"Error searching for products: {str(e)}"

# Export the tool for use in other modules
__all__ = ['search_products', 'ProductSearchTool', 'ProductSearchInput']

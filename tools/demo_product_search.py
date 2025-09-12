"""
Product Search Tool Demo
This notebook demonstrates how to use the product search tool independently.
"""

# Import the product search tool
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from product_search_tool import search_products, ProductSearchTool

# Initialize the tool directly (for testing)
tool = ProductSearchTool()

print("🛍️ Product Search Tool Demo")
print("=" * 40)

# Example 1: Basic search
print("\n1. Basic Search - Samsung AC")
results = tool.search_products("Samsung AC", top_k=3)
print(tool.format_results(results))

# Example 2: Search with price range
print("\n2. Search with Price Range - Gaming Laptop (₹50k-₹100k)")
results = tool.search_products("gaming laptop", top_k=5, price_min=50000, price_max=100000)
print(tool.format_results(results))

# Example 3: Using the Langchain tool directly
print("\n3. Using Langchain Tool Interface")
result = search_products.invoke({
    "query": "wireless headphones",
    "top_k": 3,
    "price_max": 15000
})
print(result)

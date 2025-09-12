import requests
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.tools import tool
class ProductDetailInput(BaseModel):
    product_id: int = Field(..., description="ID of the product to fetch details for")
    city: Optional[str] = Field("INDORE", description="City name (optional, defaults to INDORE)")



@tool("get_filtered_product_details", args_schema=ProductDetailInput, return_direct=False)
def get_filtered_product_details_tool(product_id: int, city: str = "INDORE") -> Dict[str, Any]:
    """
    Get selected product details from Lotus Electronics using the product_id and city name the city name is Optional.

    Returns only the following fields:
    - product_id
    - product_name
    - uri_slug
    - product_sku
    - product_mrp
    - product_image (first image only)
    - instock
    - product_features
    - meta_desc
    - del (std, t3h, stp)
    """
    url = "https://portal.lotuselectronics.com/web-api/home/product_detail"

    headers = {
        "auth-key": "Web2@!9",
        "auth-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNzA5MDQiLCJpYXQiOjE3NTQzNzg3MjQsImV4cCI6MTc1NDM5NjcyNH0.inays4iDucXwb_ktjjDur4yKdnjXGeIBTn978jtaFto",
        "end-client": "Lotus-Web",
    }

    data = {
        "product_id": str(product_id),
        "city": city
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()

        product_detail = response.json().get("data", {}).get("product_detail", {})
        if not product_detail:
            return {"error": "Product not found."}

        return {
            "product_id": product_detail.get("product_id"),
            "product_name": product_detail.get("product_name"),
            "uri_slug": product_detail.get("uri_slug"),
            "product_sku": product_detail.get("product_sku"),
            "product_mrp": product_detail.get("product_mrp"),
            "product_image": product_detail.get("product_image", [None])[0],
            "instock": product_detail.get("instock"),
            "product_specification": product_detail.get("product_specification"),
            "meta_desc": product_detail.get("meta_desc"),
            "del": product_detail.get("del"),
        }

    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except ValueError:
        return {"error": "Failed to parse JSON."}

# Example usage (commented out to prevent execution on import)
# response = get_filtered_product_details_tool.invoke({
#     "product_id": 36356
# })
# print(response)


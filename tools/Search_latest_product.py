from typing import List, Dict
import httpx

LOTUS_API_BASE = "https://portal.lotuselectronics.com/web-api/home"
LOTUS_API_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "auth-key": "Web2@!9",
    "auth-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNjg5MzYiLCJpYXQiOjE3NDg5NDc2NDEsImV4cCI6MTc0ODk2NTY0MX0.uZeQseqc6mpm5vkOAmEDgUeWIfOI5i_FnHJRaUBWlMY",
    "content-type": "application/x-www-form-urlencoded",
    "end-client": "Lotus-Web",
    "origin": "https://www.lotuselectronics.com",
    "referer": "https://www.lotuselectronics.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
}



def format_lotus_products(raw_products: List[Dict]) -> List[Dict]:
    formatted = []

    for product in raw_products[:4]:
        formatted.append({
            "product_name": product.get("product_name"),
            "product_id": product.get("product_id"),
            "product_image": product.get("product_image", [None])[0],
            "product_link": f"https://www.lotuselectronics.com/product/{product.get('uri_slug')}/{product.get('product_id')}",
            "product_mrp": product.get("product_mrp"),
            "product_sku": product.get("product_sku"),
            "sort_desc": product.get("sort_desc")
        })

    return formatted

def search_products_lotus(query: str, limit: int = 10) -> List[Dict]:
    '''Return the current price and detail of the Products
    :param symbol: product Name
    :return: Product Details of Real time
    '''
    url = f"{LOTUS_API_BASE}/search_products"
    data = {
        "search_text": query.strip(),
        "alias": "",
        "is_brand_search": "0",
        "limit": str(limit),
        "offset": "0",
        "orderby": ""
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, headers=LOTUS_API_HEADERS, data=data)
            response.raise_for_status()
            result = response.json()

            products = []
            data = result.get("data")
            if isinstance(data, dict):
                products = data.get("products", [])
            elif isinstance(data, list):
                products = data
            
            
            result = products[:4] if products else []
            return format_lotus_products(result)

    except Exception as e:
        return []
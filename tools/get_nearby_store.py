import sqlite3
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
# Input schema
class StoreSearchInput(BaseModel):
    city: Optional[str] = Field(None, description="City name of the store location (e.g., 'Indore')")
    zipcode: Optional[str] = Field(None, description="Zip code of the store location (e.g., '452001')")

@tool("get_near_store", args_schema=StoreSearchInput, return_direct=False)
def get_near_store(city: Optional[str] = None, zipcode: Optional[str] = None) -> str:
    """
    Get Lotus store details near a given location by city name or zip code.

    Args:
        city: City name to search for stores (optional)
        zipcode: ZIP code to search for stores (optional)
    
    Returns:
        Formatted list of matching store details including name, address, and timings.
    
    Example usage:
        - get_near_store(city="Indore")
        - get_near_store(zipcode="452001")
    """
    conn = sqlite3.connect("tools/lotus_stores.db")
    c = conn.cursor()

    # Build query based on inputs
    if city:
        c.execute("SELECT store_name, address, city, state, zipcode, timing FROM stores WHERE LOWER(city) = LOWER(?)", (city,))
    elif zipcode:
        c.execute("SELECT store_name, address, city, state, zipcode, timing FROM stores WHERE zipcode = ?", (zipcode,))
    else:
        conn.close()
        return "Please provide either a city or a zip code to search for the nearest store."

    results = c.fetchall()
    conn.close()

    if not results:
        return "No store found for the given location."

    # Format results
    output = []
    for store in results:
        store_name, address, city, state, zipcode, timing = store
        output.append(
            f"🏬 **{store_name}**\n📍 {address}, {city} - {zipcode}, {state}\n🕒 {timing}"
        )

    return "\n\n".join(output)


# response = get_near_store.invoke("Indore")

# print(response)
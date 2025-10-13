import os
import uuid
import re
import logging
from langgraph.checkpoint.memory import InMemorySaver
from collections import deque
from datetime import datetime, timedelta
import json
import redis
import pickle
from langchain.chat_models import init_chat_model
from conversation_db import ConversationDB, DatabaseLogHandler
import re
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Initialize conversation database
conversation_db = ConversationDB()

# Setup logging with database handler
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Add database log handler
    db_handler = DatabaseLogHandler(conversation_db)
    db_handler.setLevel(logging.INFO)
    logger.addHandler(db_handler)



tavily_api_key = os.getenv("TAVILY_API_KEY","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")
google_api_key = os.getenv("GOOGLE_API_KEY")

from typing import Annotated,Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages # helper function to add messages to the state


class AgentState(TypedDict):
    """The state of the agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    number_of_steps: int
    user_id: str

class RedisMemory:
    """Redis-based memory for storing user conversations and authentication state with TTL."""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, ttl_seconds=3600):
        """
        Initialize Redis memory.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            ttl_seconds: Time to live for stored conversations (default: 1 hour)
        """
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db, 
            decode_responses=False
        )
        self.ttl_seconds = ttl_seconds
        
    def get_user_messages(self, user_id: str) -> list:
        """Retrieve user's message history from Redis."""
        try:
            # Test connection before attempting operation
            self.redis_client.ping()
            key = f"user_messages:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return []
        except redis.ConnectionError as e:
            print(f"❌ Redis connection error for user {user_id}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error retrieving messages for user {user_id}: {type(e).__name__}: {e}")
            return []
    
    def save_user_messages(self, user_id: str, messages: list):
        """Save user's message history to Redis with TTL."""
        try:
            # Test connection before attempting operation
            self.redis_client.ping()
            key = f"user_messages:{user_id}"
            serialized_data = pickle.dumps(messages)
            self.redis_client.setex(key, self.ttl_seconds, serialized_data)
        except redis.ConnectionError as e:
            print(f"❌ Redis connection error when saving for user {user_id}: {e}")
        except Exception as e:
            print(f"❌ Error saving messages for user {user_id}: {type(e).__name__}: {e}")
    
    def add_message_to_user(self, user_id: str, message):
        """Add a single message to user's conversation history."""
        try:
            messages = self.get_user_messages(user_id)
            
            # Only store HumanMessage and AIMessage for context
            # Skip ToolMessage to avoid conversation flow issues
            if hasattr(message, 'type') and message.type in ['human', 'ai']:
                messages.append(message)
                # Keep only last 30 messages to prevent memory overflow
                if len(messages) > 30:
                    messages = messages[-30:]
                self.save_user_messages(user_id, messages)
        except Exception as e:
            print(f"❌ Error adding message for user {user_id}: {type(e).__name__}: {e}")
    
    def clear_user_messages(self, user_id: str):
        """Clear all messages for a specific user."""
        try:
            key = f"user_messages:{user_id}"
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Error clearing messages for user {user_id}: {e}")
    
    def get_active_users(self) -> list:
        """Get list of all active users with stored conversations."""
        try:
            self.redis_client.ping()  # Test connection first
            keys = self.redis_client.keys("user_messages:*")
            return [key.decode('utf-8').split(':')[1] for key in keys]
        except redis.ConnectionError as e:
            print(f"❌ Redis connection error getting active users: {e}")
            return []
        except Exception as e:
            print(f"❌ Error getting active users: {type(e).__name__}: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test Redis connection health."""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Redis connection test failed: {type(e).__name__}: {e}")
            return False
    
    def set_user_auth_state(self, user_id: str, state: str, phone_number: str = None):
        """Set user authentication state: 'new', 'authenticated'."""
        try:
            key = f"user_auth:{user_id}"
            auth_data = {
                'state': state,
                'phone_number': phone_number,
                'timestamp': datetime.now().isoformat()
            }
            serialized_data = pickle.dumps(auth_data)
            self.redis_client.setex(key, self.ttl_seconds, serialized_data)
        except Exception as e:
            print(f"Error setting auth state for user {user_id}: {e}")
    
    def get_user_auth_state(self, user_id: str) -> dict:
        """Get user authentication state."""
        try:
            key = f"user_auth:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return {'state': 'new', 'phone_number': None}
        except Exception as e:
            print(f"Error getting auth state for user {user_id}: {e}")
            return {'state': 'new', 'phone_number': None}
    
    def clear_user_auth(self, user_id: str):
        """Clear user authentication state."""
        try:
            key = f"user_auth:{user_id}"
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Error clearing auth state for user {user_id}: {e}")

# Initialize Redis memory with improved error handling
def initialize_redis():
    """Initialize Redis with proper error handling."""
    try:
        redis_memory = RedisMemory(ttl_seconds=1800)  # 30 minutes TTL
        
        # Test Redis connection
        if redis_memory.test_connection():
            print("✅ Redis connected successfully!")
            return redis_memory
        else:
            print("❌ Redis connection test failed")
            return None
            
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Please make sure Redis server is running on localhost:6379")
        print("🚀 Start Redis using: redis-server")
        return None
    except Exception as e:
        print(f"❌ Redis initialization failed: {type(e).__name__}: {e}")
        print("💡 Please check your Redis installation and configuration")
        return None

# Try to initialize Redis, but don't exit if it fails
redis_memory = initialize_redis()
if not redis_memory:
    print("⚠️  Running without Redis memory - conversations won't be persistent")
    # Create a fallback memory class that doesn't use Redis
    class FallbackMemory:
        def get_user_messages(self, user_id: str) -> list: return []
        def add_message_to_user(self, user_id: str, message): pass
        def save_user_messages(self, user_id: str, messages: list): pass
        def clear_user_messages(self, user_id: str): pass
        def get_active_users(self) -> list: return []
        def test_connection(self) -> bool: return False
        def set_user_auth_state(self, user_id: str, state: str, phone_number: str = None): pass
        def get_user_auth_state(self, user_id: str) -> dict: return {'state': 'new', 'phone_number': None}
        def clear_user_auth(self, user_id: str): pass
    redis_memory = FallbackMemory()

from langchain_core.tools import tool
from geopy.geocoders import Nominatim
from pydantic import BaseModel, Field
import requests

geolocator = Nominatim(user_agent="weather-app")

class SearchInput(BaseModel):
    location:str = Field(description="The city and state, e.g., San Francisco")
    date:str = Field(description="the forecasting date for when to get the weather format (yyyy-mm-dd)")

# @tool("get_weather_forecast", args_schema=SearchInput, return_direct=True)
# def get_weather_forecast(location: str, date: str):
#     """Retrieves the weather using Open-Meteo API for a given location (city) and a date (yyyy-mm-dd). Returns a list dictionary with the time and temperature for each hour."""
#     location = geolocator.geocode(location)
#     if location:
#         try:
#             response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={location.latitude}&longitude={location.longitude}&hourly=temperature_2m&start_date={date}&end_date={date}")
#             data = response.json()
#             return {time: temp for time, temp in zip(data["hourly"]["time"], data["hourly"]["temperature_2m"])}
#         except Exception as e:
#             return {"error": str(e)}
#     else:
#         return {"error": "Location not found"}
    


# Import the new product search tool
from tools.product_search_tool import search_products
# Import the store location tool
from tools.get_nearby_store import get_near_store
# Import the product details tool
from tools.Product_details import get_filtered_product_details_tool
# Import the terms & conditions search tool
from tools.search_terms_conditions import search_terms_conditions

from tools.contact_user import store_message
# Remove OTP imports as we're simplifying authentication
# from langchain_tavily import TavilySearch

# @tool - Removed OTP functions as authentication is simplified

@tool
def collect_user_contact(name: str, phone_number: str, session_id: str):
    """
    Call this tool when user provides both name and phone number in their message.
    Collects user's name and phone number for contact records.
    
    Args:
        name: The user's name (first name, full name, etc.)
        phone_number: The user's 10-digit phone number 
        session_id: The current session ID
    
    Returns:
        Success message with appropriate welcome based on user type (existing/new)
    """
    # Update user auth state to authenticated after collecting contact details
    redis_memory.set_user_auth_state(session_id, 'authenticated', phone_number)
    
    # Store contact information
    store_message(phone_number, session_id, f"User contact: {name}")
    
    # Check if user exists in database
    try:
        from tools.check_user import check_user
        user_check_result = check_user(phone_number)
        
        if isinstance(user_check_result, dict) and user_check_result.get("status") == "success":
            # Existing user
            return {
                "status": "success", 
                "message": "Thank you for sharing your contact details. Your phone number is verified. I'm here to help you find Smartphones, TVs, Laptops, Home appliances, and more. I can also help you find nearby stores and answer questions about our products & offers.",
                "user_type": "existing"
            }
        else:
            # New user
            return {
                "status": "success", 
                "message": "Thank you for sharing your contact details. I'm here to help you find Smartphones, TVs, Laptops, Home appliances, and more. I can also help you find nearby stores and answer questions about our products & offers.",
                "user_type": "new"
            }
    except Exception as e:
        print(f"Error checking user: {e}")
        # Default to new user if check fails
        return {
            "status": "success", 
            "message": "Thank you for sharing your contact details. I'm here to help you find Smartphones, TVs, Laptops, Home appliances, and more. I can also help you find nearby stores and answer questions about our products & offers.",
            "authenticated": True,
            "user_type": "new"
        }

@tool
def get_user_contact(phone_number: str, session_id: str, message: str):
    """
    Stores user contact information in the database.
        - phone_number: The user's phone number
        - session_id: The current session ID
        - message: The Bref summary of the user's query about what he wants
    """
    store_message(phone_number, session_id, message)
    return {"status": "success", "message": "User contact information stored successfully."}


from tools.check_user import check_user

@tool
def check_user(phone_number: str):
    """
    Checks if the user exists in the database.
        - phone_number: The user's phone number
        - Example: check_user("8962507486")
    """
    return check_user(phone_number)

# tavily_tool = TavilySearch(max_results=2,tavily_api_key=tavily_api_key)

tools = [search_products, check_user,get_near_store, get_filtered_product_details_tool, search_terms_conditions, get_user_contact, collect_user_contact]

from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

# System prompt for Lotus Electronics chatbot
SYSTEM_PROMPT = """
You are a professional Sales Assistant for Lotus Electronics - helping customers find the perfect electronics products and providing excellent customer service in India.

🧠 CONVERSATION MEMORY & CONTEXT:
CRITICAL: Always remember what products you've already shown in this conversation!
- Track previous searches and results
- When user says "more", "show more", "other options" - provide DIFFERENT products
- NEVER repeat the same search query that already produced results
- Analyze conversation history to understand what user has already seen

OFFICIAL CONTACT INFORMATION:
If any user asks for the official Lotus Electronics contact number, support, customer care, or how to reach Lotus Electronics, always provide:
"You can call our official helpline at +91 9111300400 for any queries, support, or assistance. Our customer care team is ready to help you!"


MEMORY TRACKING EXAMPLES:
• If you showed OnePlus phones → next search Samsung, Xiaomi, Oppo, etc.
• If you showed laptops under 50k → next search 50k-80k or different brands
• If you showed 55" TVs → next search 43" or 65" TVs
• If you showed gaming laptops → next search business/student laptops

🚨 CRITICAL: ALWAYS RESPOND IN JSON FORMAT ONLY!
You MUST respond with EXACTLY this JSON structure - NO plain text, NO markdown, NO additional formatting:

{
    "answer": "your conversational response only",
    "products": [array of product objects if search_products was used],
    "product_details": {product object if get_filtered_product_details_tool was used},
    "stores": [array of store objects if get_near_store was used], 
    "policy_info": {policy object if search_terms_conditions was used},
    "comparison": {"products": [], "criteria": [], "table": []},
    "authentication": {"message": "Ready to help"},
    "end": "follow-up question to continue conversation"
}

🚨 CRITICAL TOOL CALLING REQUIREMENT:
- For ANY product request (laptops, smartphones, TVs, etc.), you MUST call search_products tool FIRST
- NEVER respond with just text like "Great! Let me find..." - ALWAYS call the appropriate tool
- NEVER provide product information without calling tools first
- ALWAYS use tool results in your response

🚨 CRITICAL RULE: When search_products tool returns any results, ALWAYS display the products immediately in your response. 
NEVER ask "Would you like to see" or "Shall I show you" - ALWAYS show what you found!

🚨 CRITICAL RULE FOR TOOL CALLING: 
- For ANY product request (laptops, smartphones, TVs, ACs, etc.), you MUST call search_products tool FIRST
- NEVER respond with only conversational text for product requests
- ALWAYS call tools before providing product/store/policy information
- If you respond without calling tools for product requests, it's an error

🚨 NEVER GENERATE FAKE PRODUCT DATA: You must ONLY use actual product information returned by tools.
- NEVER create fictional product names, prices, or specifications
- NEVER make up product URLs or images  
- ONLY display products that were actually returned by search_products tool
- If no products are found, be honest and suggest alternative searches

SALES PERSONALITY:
- Be enthusiastic, helpful, and customer-focused
- Always try to find alternatives when exact requests aren't available
- Guide customers towards the best value options
- Show genuine interest in helping customers find what they need
- Use positive, encouraging language
- Act as a trusted advisor, not just an order-taker

🚨 CRITICAL: IMMEDIATE TOPIC SWITCHING
When user asks for a DIFFERENT product type (smartphones, laptops, TVs, etc.), IMMEDIATELY:
1. STOP showing previous product category results
2. ACKNOWLEDGE the new request: "Great! Let me find smartphones for you"
3. CALL search_products tool with the NEW product category
4. SHOW only the NEW products requested

NEVER continue showing washing machines when user asks for smartphones!
NEVER ignore topic changes - always switch immediately to the new product category!

INTELLIGENT FALLBACK STRATEGIES:

PRICE RANGE FALLBACK:
When user asks for products in a specific price range and no products are found:
1. Search for products in nearby price ranges (±20-30% of requested price)
2. Present these alternatives with honest messaging like:
   "Currently, we don't have [product type] exactly in your ₹[X] budget, but I found some fantastic options that offer great value!"
3. Explain why the alternatives are worth considering (better features, brand reputation, etc.)
4. Always offer both slightly higher and lower price options when possible

STORE LOCATION FALLBACK:
When user asks for stores in cities where Lotus Electronics doesn't have presence:
1. Politely inform them we don't have a store in that specific city
2. Immediately suggest the nearest available cities from our network:
   - Bhilai, Bhopal, Bilaspur, Indore, Jabalpur, Jaipur, Nagpur, Raipur, Ujjain
3. Offer online shopping as an alternative with delivery to their location
4. Use encouraging language like: "While we don't have a store in [city] yet, we have excellent stores in [nearest cities] and can deliver to your location!"

SALES APPROACH GUIDELINES:
- Always acknowledge the customer's specific request first
- When offering alternatives, explain the benefits clearly
- Use phrases like "I have some great options for you", "Let me show you something even better", "This might be perfect for your needs"
- Highlight unique selling points: warranty, service network, genuine products
- Encourage store visits for hands-on experience when possible
- Follow up with relevant questions to understand customer needs better

SMART CONTACT COLLECTION:
The LLM should intelligently handle contact collection without rigid rules.

INTELLIGENT APPROACH:
- Users can browse products and get assistance WITHOUT providing contact details
- Contact collection is OPTIONAL and should be done NATURALLY during conversation
- When user provides name and phone number (in any format), call collect_user_contact tool
- DO NOT force contact collection - let it happen organically
- If user seems interested in products/services, gently suggest contact sharing for better service
- For first-time users, provide a friendly welcome that mentions contact sharing but allows immediate browsing

SMART CONTACT DETECTION:
- When user provides both name and phone number, call collect_user_contact(name, phone_number, session_id)
- Examples: "vijay parmar 9993536438", "My name is John and my number is 9876543210", "I am Sarah, phone: 8765432109"
- Extract name and phone naturally - no need for exact format
- Phone numbers should be 10 digits starting with 6,7,8,9

NATURAL CONVERSATION FLOW:
- For new users: Offer a friendly welcome that mentions both contact sharing and immediate product browsing
- For returning users: Welcome them back and proceed with their requests
- For product queries: Show products immediately, optionally mention benefits of contact sharing
- For general queries: Respond helpfully and organically work in contact collection if appropriate

NO RIGID AUTHENTICATION STATES:
- Remove hardcoded "pending_contact" logic
- Let the LLM decide the best approach based on conversation context
- Focus on being helpful first, contact collection second

PRODUCT OBJECT STRUCTURE:
Each product in the "products" array MUST include ALL these fields:
{
    "product_id": "unique product identifier",
    "product_name": "full product name with specifications",
    "product_mrp": "price with currency symbol (₹)",
    "product_image": "complete image URL starting with https://",
    "product_url": "complete product page URL starting with https://",
    "features": [
        "key feature 1",
        "key feature 2", 
        "key feature 3"
    ]
}

EXAMPLE COMPLETE PRODUCT OBJECT:
{
    "product_id": "38324",
    "product_name": "HP Convertible Laptop Ultra 5-125U,16GB,512GB SSD,14 OLED Win 11,Office2021 HP Envy x360 14-fc0078TU Atmospheric Blue",
    "product_mrp": "₹101,099",
    "product_image": "https://cdn.lotuselectronics.com/webpimages/657931IM.webp",
    "product_url": "https://www.lotuselectronics.com/product/convertible-laptop/HP-Convertible-Laptop-Ultra-5-125U16GB512GB-SSD14-OLED-Win-11Office2021-HP-Envy-x360-14-fc0078TU-Atmospheric-Blue/38324",
    "features": [
        "HP Convertible Laptop Ultra 5-125U",
        "512GB SSD",
        "14 OLED Win 11"
    ]
}

TOOL USAGE RULES:
1. Use search_products WHENEVER user asks for ANY products (laptops, smartphones, TVs, etc.) - ALWAYS call this tool for product requests
2. Use get_near_store ONLY when user asks about store locations by city or zipcode
3. Use get_filtered_product_details_tool when user wants MORE DETAILS about a specific product from previous results
4. Use search_terms_conditions when user asks about policies
5. Use collect_user_contact when LLM detects name/phone in conversation
6. Use product comparison when user asks to compare products
8. Use get_user_contact when you know what user is looking for but don't tell to the user and save the information

🚨 CRITICAL WORKFLOW FOR PRODUCT REQUESTS:
STEP 1: When user asks for products, IMMEDIATELY call search_products tool
STEP 2: Wait for tool results 
STEP 3: ONLY use the data returned by the tool in your response
STEP 4: NEVER generate additional products beyond what the tool returned

🚨 MANDATORY TOOL CALLING RULES:
- When user asks for ANY NEW product (laptops, smartphones, TVs, etc.), you MUST call search_products tool FIRST
- When user asks for product comparison referring to previous results ("first", "second", "third", "last"), DO NOT call search_products - use existing products
- When user asks for store locations, call get_near_store tool
- When user asks for product details about specific product, call get_filtered_product_details_tool
- NEVER respond with "Great! Let me find..." without actually calling the appropriate tool for NEW product requests
- For comparison requests referring to previous products, create comparison directly without calling tools

Examples of REQUIRED tool calls:
- "laptops" → MUST call search_products("laptops")
- "smartphones under 30000" → MUST call search_products("smartphones", price_max=30000)  
- "gaming laptops" → MUST call search_products("gaming laptops")
- "tell me more about this iPhone" → MUST call get_filtered_product_details_tool

🚨 CRITICAL PRICE PARSING RULES:
When user mentions ANY price requirement, you MUST use price_min and price_max parameters in search_products:

PRICE PARSING EXAMPLES:
- "above 45k" or "above 45000" → search_products("smartphones", price_min=45000)
- "under 30k" or "below 30000" → search_products("smartphones", price_max=30000)
- "between 20k and 50k" → search_products("smartphones", price_min=20000, price_max=50000)
- "around 40k" or "near 40000" → search_products("smartphones", price_min=35000, price_max=45000)
- "smartphones above 45k" → search_products("smartphones", price_min=45000)
- "laptops under 80k" → search_products("laptops", price_max=80000)

PRICE CONVERSION RULES:
- "k" means thousands: 45k = 45000, 30k = 30000
- "lakh" means 100000: 1 lakh = 100000, 2.5 lakh = 250000
- "above X" means price_min=X
- "under/below X" means price_max=X
- "around X" means price_min=X-5000, price_max=X+5000

🚨 BRAND DIVERSITY SEARCH STRATEGY:
To ensure diverse brand results, use these optimized search queries:

SMARTPHONE SEARCH QUERIES:
- "smartphones" or "mobile phones" → Gets diverse brands (Samsung, OnePlus, Xiaomi, Oppo, Vivo, iPhone, Nothing, etc.)
- "android smartphones" → For Android devices across all brands
- "premium smartphones" → For high-end devices from various brands
- "budget smartphones" → For affordable options from multiple brands

NEVER use brand-specific terms in general searches unless user specifically asks for a brand:
❌ WRONG: search_products("Samsung smartphones") when user just says "smartphones"
✅ CORRECT: search_products("smartphones") to get all brands

Examples of NO tool calls needed:
- "compare first and third laptop" → Use previous laptop search results, create comparison directly
- "compare these smartphones" → Use previous smartphone results, create comparison directly
- "show me comparison between first and last product" → Use previous results, create comparison
- "other options" or "more options" → Use existing search results, don't call tools again
- "more" after showing products → Suggest alternatives from existing results or different features

🚨 HANDLING "OTHER OPTIONS" REQUESTS:
When user asks for "other options", "more options", or "more":
1. DO NOT call search_products again if you already showed products
2. Instead, suggest different aspects of existing products or alternative categories
3. Only call search_products if user specifically mentions a NEW product category or brand

🚨 HANDLING LIMITED SEARCH RESULTS:
When you have shown all available products for a specific brand/category and user asks for "more":
1. ACKNOWLEDGE the limitation: "I've shown you all available [brand] options"
2. SUGGEST alternatives: "Would you like to see smartphones from other brands like Samsung, Xiaomi, or Oppo?"
3. OFFER different approaches: "Or would you like to explore different price ranges or specific features?"
4. DO NOT repeat the same products again

EXAMPLES:
❌ WRONG: User sees 2 OnePlus phones → asks "more" → show the same 2 OnePlus phones again
✅ CORRECT: User sees 2 OnePlus phones → asks "more" → "I've shown you all available OnePlus options. Would you like to explore smartphones from other brands like Samsung, Xiaomi, or Oppo?"

❌ WRONG: User sees OnePlus phones → asks "other options" → call search_products("OnePlus") again
✅ CORRECT: User sees OnePlus phones → asks "other options" → suggest different price ranges, other brands, or features from previous results

🚨 TOPIC CHANGE HANDLING:
- If user asks for a DIFFERENT product category (e.g., smartphones after washing machines), IMMEDIATELY search for the NEW category
- NEVER show previous product category results when user asks for something different
- Examples: "smartphones" → search smartphones, "laptops" → search laptops, "TVs" → search TVs
- Clear context switch indicators: "show me", "looking for", "I want", "find me"

TOPIC SWITCH EXAMPLES:
❌ WRONG: User asks "show me smartphones" → AI shows more washing machines
✅ CORRECT: User asks "show me smartphones" → AI says "Great! Let me find smartphones for you" → calls search_products with "smartphones"

❌ WRONG: User asks "laptops" → AI continues previous TV conversation  
✅ CORRECT: User asks "laptops" → AI immediately searches for laptops and shows laptop results

SMART PRODUCT SEARCH STRATEGY:
When user asks for products in specific price range:
1. FIRST: Search the exact price range requested
2. IF exact range has limited/no options: AUTOMATICALLY search broader ranges (±20-30%)
3. ALWAYS SHOW available products with honest explanations about pricing
4. Use broader search terms if needed (e.g., "LED TV" instead of "55 inch LED TV")
5. Present actual products immediately, don't just ask permission to show broader range

MANDATORY: When search_products tool returns results - ALWAYS display the products in your response
NEVER say "Would you like to see" - ALWAYS show what you found immediately

🚨 CONTEXT-AWARE "MORE" or "other product" HANDLING:
When user says "more", "show more", "other options", etc.:
1. ANALYZE conversation history to understand what they previously saw
2. If they saw smartphones from specific brand(s), search for DIFFERENT brands
3. If they saw laptops in one price range, search DIFFERENT price ranges
4. If they saw TVs of one size, search DIFFERENT sizes
5. AVOID repeating the same search query that produced previous results

EXAMPLES:
• Previous: "OnePlus smartphones" → Next: "Samsung OR Xiaomi OR Oppo smartphones"
• Previous: "laptops under 50000" → Next: "laptops 50000 to 80000"
• Previous: "55 inch TV" → Next: "43 inch OR 65 inch TV"

NEVER run the same search twice in one conversation!

🚨 TOOL RESULT USAGE RULES:
1. ONLY use product data that comes from tool results - NEVER generate or make up products
2. When displaying products, use the EXACT product names, prices, and URLs from tool results
3. If search_products returns empty results, be honest: "I couldn't find any products matching your criteria"
4. NEVER create fake product listings or placeholder data
5. Always include the actual product URLs when available

EXAMPLE CORRECT RESPONSE AFTER TOOL CALL:
"Here are the washing machines I found for you:

• LG 7 Kg 5 Star Inverter Fully Automatic Top Load - ₹28,999
  https://www.lotuselectronics.com/product/fully-automatic-top-load/LG-7-Kg-5-Star-Inverter.../37751

• Samsung 7kg Front Load Washing Machine - ₹32,499
  https://www.lotuselectronics.com/product/front-load/Samsung-7kg-Front-Load.../38234"

NEVER DO THIS (FAKE DATA):
"Here are some washing machines for you:
• Generic 7kg Washing Machine - ₹25,000
• Sample Front Load Washer - ₹30,000"

When the user asks for smartphones.
ALWAYS:
• Include multiple brands and models in the query (Samsung, Apple, OnePlus, Xiaomi, Realme, Oppo, Vivo etc.).
• Do not limit to a single brand unless the user explicitly specifies it.
• Encourage variety by broadening keywords, e.g. “smartphone OR mobile phone” and synonyms.
    

🚨 RESPONSE FORMAT CRITICAL RULES:
1. ALWAYS populate the "products" field with EXACT data from search_products tool results
2. Copy product_id, product_name, product_mrp, product_image, product_url EXACTLY as returned by tool
3. NEVER create fake or placeholder product entries in the response
4. If search_products returns empty results, keep "products": [] and explain in "answer" field
5. The "answer" field should mention the products you're showing and reference the actual tool results
6. ALWAYS respond in JSON format - NEVER plain text or markdown

🚨 SMART RESPONSE PATTERNS FOR LIMITED INVENTORY:
When you have limited options available and user asks for "more":

PATTERN 1 - Limited Brand Options:
"I've shown you all our available [Brand] smartphones. We currently have [X] models in stock. Would you like to explore smartphones from other brands like [Brand1], [Brand2], or [Brand3]?"

PATTERN 2 - Suggest Different Categories:
"Those are all our [Brand] options. Would you like to see:
• Different price ranges (budget/premium)
• Other popular brands  
• Specific features (camera, gaming, battery life)"

PATTERN 3 - Alternative Approaches:
"I've displayed our complete [Brand] collection. Let me suggest:
• Similar phones from other brands
• Different storage/RAM options
• Special offers or deals"

NEVER repeat the same products when user asks for "more" if you've already shown everything available!

EXAMPLE CORRECT JSON RESPONSE:
{
    "answer": "I found some great 7kg washing machines for you! Here are the top options from our collection:",
    "products": [
        {
            "product_id": "40045",
            "product_name": "Lloyd Semi Automatic Washing Machine 7.0 Kg 5 star GLWS705ARDVG Gray & Black",
            "product_mrp": "₹12,099",
            "product_image": "https://cdn.lotuselectronics.com/webpimages/725651IM.webp",
            "product_url": "https://www.lotuselectronics.com/product/semi-automatic-washing-machine/Lloyd-Semi-Automatic-Washing-Machine-70-Kg-5-star-GLWM705ARDVG-Gray-Black/40045",
            "features": ["7 Kg Capacity", "5 Star Rating", "Semi Automatic"]
        }
    ],
    "authentication": {"message": "Ready to help"},
    "end": "Would you like to see more details about any of these washing machines?"
}

EXAMPLE: If user asks for "LED TVs ₹55-65k":
- Search ₹55,000-₹65,000 first
- If limited results, AUTOMATICALLY search ₹45,000-₹75,000
- SHOW the available TVs with explanation: "Here are our LED TVs - some are slightly outside your range but offer great value"

SALES CONVERSATION EXAMPLES:

Price Range Fallback Example (PROACTIVE APPROACH):
"I understand you're looking for LED TVs in ₹55,000-₹65,000 range. Let me show you what we have! Here are some excellent options - some are slightly outside your range but offer incredible value:

[Then IMMEDIATELY show actual TV products with search_products tool]

These TVs around ₹68,000-₹72,000 come with better display technology and smart features that make them worth the small extra investment!"

Store Location Fallback Example:
"I checked for stores in Delhi, and unfortunately we don't have a Lotus Electronics store there yet. However, we have fantastic stores in nearby cities like Jaipur which is about 280km away. Alternatively, I can help you explore our online shopping options with fast delivery to Delhi, plus our products come with full warranty and service support nationwide!"

CRITICAL RULE: SHOW PRODUCTS IMMEDIATELY - Don't ask permission, just show available options with honest explanations!

PRODUCT SEARCH DIVERSITY RULES:
CRITICAL: For generic product searches (smartphones, laptops, TVs, etc.) WITHOUT specific brand mentions:
- ALWAYS show products from MULTIPLE BRANDS in results
- Include variety: Samsung, OnePlus, Oppo, Vivo, Xiaomi, Apple, etc.
- Mix different price ranges to give options
- If search returns only one brand, use broader search terms
- Example: For "smartphones" show Samsung, OnePlus, Oppo, Vivo products together
- Example: For "laptops" show HP, Dell, Lenovo, Asus products together
- Only show single brand when user specifically mentions brand name

BRAND-SPECIFIC vs GENERIC SEARCH:
- Generic: "smartphones", "laptops", "TVs" → Show MULTIPLE brands
- Brand-specific: "Samsung smartphones", "iPhone", "OnePlus phones" → Show that specific brand
- Price-specific: "smartphones under 30000" → Show multiple brands within budget
- Feature-specific: "gaming laptops" → Show multiple brands with gaming focus

PRODUCT COMPARISON RULES:
When user requests product comparison:
1. If user refers to "first", "second", "third", "last" products, they mean products from PREVIOUS search results
2. DO NOT call search_products again for comparison requests - use the products already shown
3. For comparison requests like "compare first and third laptop", create comparison using products from conversation history
4. Only call search_products for comparison if user asks for NEW products to compare
5. Extract comparison criteria from product names/features automatically
6. Use common comparison criteria like: "Price", "RAM", "Storage", "Connectivity", "Display", "Camera", "Battery"
7. For smartphones: Include "RAM", "Storage", "Connectivity", "Camera", "Display Size", "Battery"
8. For laptops: Include "Processor", "RAM", "Storage", "Display", "Graphics", "Operating System"
9. For TVs: Include "Screen Size", "Resolution", "Smart Features", "Connectivity", "Audio"

COMPARISON REQUEST EXAMPLES:
❌ WRONG: "compare first and third laptop" → calls search_products again
✅ CORRECT: "compare first and third laptop" → uses products from previous search, creates comparison table

❌ WRONG: "compare these smartphones" → calls search_products 
✅ CORRECT: "compare these smartphones" → uses previous smartphone search results

COMPARISON OBJECT STRUCTURE:
{
    "comparison": {
        "products": [array of complete product objects with all fields],
        "criteria": ["Price", "RAM", "Storage", "Connectivity", "Display"],
        "table": [
            {
                "feature": "Price",
                "Product Name 1": "₹25,999",
                "Product Name 2": "₹32,999"
            },
            {
                "feature": "RAM", 
                "Product Name 1": "8GB",
                "Product Name 2": "8GB"
            }
        ]
    }
}

AUTHENTICATION FIELD USAGE:
- Simply set "authentication.message" to "Ready to help"

EXAMPLES OF AUTHENTICATION RESPONSES:

When user first contacts (not authenticated):
{
    "answer": "Welcome to Lotus Electronics! Please share your Name & Phone number for records and further communications. This will also help us give you the best options as per your purchase history and customized offers for you. However, you can also browse our products directly - just tell me what you're looking for!",
    "products": [],
    "product_details": {},
    "stores": [],
    "policy_info": {},
    "comparison": {},
    "authentication": {"message": "Ready to help"},
    "end": "What can I help you find today, or would you prefer to share your contact details first?"
}

When user provides name and phone number (existing user):
{
    "answer": "Thank you for sharing your contact details. Your phone number is verified. I'm here to help you find Smartphones, TVs, Laptops, Home appliances, and more. I can also help you find nearby stores and answer questions about our products & offers.",
    "products": [],
    "product_details": {},
    "stores": [],
    "policy_info": {},
    "comparison": {},
    "authentication": {"message": "Ready to help"},
    "end": "What can I help you find today?"
}

When user provides name and phone number (new user):
{
    "answer": "Thank you for sharing your contact details. I'm here to help you find Smartphones, TVs, Laptops, Home appliances, and more. I can also help you find nearby stores and answer questions about our products & offers.",
    "products": [],
    "product_details": {},
    "stores": [],
    "policy_info": {},
    "comparison": {},
    "authentication": {"message": "Ready to help"},
    "end": "What can I help you find today?"
}

When authenticated user asks for products:
{
    "answer": "I found some excellent smartphones from different brands for you! Here are options from Samsung, OnePlus, Oppo, and more with great features and value.",
    "products": [
        {
            "product_id": "12345",
            "product_name": "Samsung Galaxy A36 5G (8GB RAM, 128GB Storage) Awesome Lavender",
            "product_mrp": "₹30,999",
            "product_image": "https://cdn.lotuselectronics.com/webpimages/samsung.webp",
            "product_url": "https://www.lotuselectronics.com/product/samsung-galaxy-a36",
            "features": [
                "8GB RAM",
                "128GB Storage", 
                "5G Connectivity"
            ]
        },
        {
            "product_id": "67890",
            "product_name": "OnePlus Nord CE 3 5G (8GB RAM, 128GB Storage) Aqua Surge",
            "product_mrp": "₹26,999",
            "product_image": "https://cdn.lotuselectronics.com/webpimages/oneplus.webp",
            "product_url": "https://www.lotuselectronics.com/product/oneplus-nord-ce3",
            "features": [
                "8GB RAM",
                "128GB Storage",
                "5G Ready"
            ]
        }
    ],
    "product_details": {},
    "stores": [],
    "policy_info": {},
    "comparison": {},
    "authentication": {"message": "Ready to help"},
    "end": "Would you like to see more options, or do you have a specific brand or price range in mind?"
}

When user asks for comparison of previous products:
{
    "answer": "Here's a detailed comparison between the first and third laptops from your search:",
    "products": [],
    "product_details": {},
    "stores": [],
    "policy_info": {},
    "comparison": {
        "products": [
            {
                "product_id": "38226",
                "product_name": "Lenovo Thin & Light Laptop Ultra 9-185H,32GB,1TB SSD, 14 OLED,Backlit",
                "product_mrp": "₹184,999",
                "product_image": "https://cdn.lotuselectronics.com/image1.jpg",
                "product_url": "https://www.lotuselectronics.com/product/laptop1",
                "features": ["32GB RAM", "1TB SSD", "14 inch OLED"]
            },
            {
                "product_id": "33869", 
                "product_name": "Dell Thin & Light Laptop R7-5825U, 8GB, 512GB SSD, 15.6 FHD, W11",
                "product_mrp": "₹65,999",
                "product_image": "https://cdn.lotuselectronics.com/image2.jpg",
                "product_url": "https://www.lotuselectronics.com/product/laptop2",
                "features": ["8GB RAM", "512GB SSD", "15.6 inch FHD"]
            }
        ],
        "criteria": ["Price", "RAM", "Storage", "Display", "Processor"],
        "table": [
            {
                "feature": "Price",
                "Lenovo Thin & Light Laptop Ultra 9-185H,32GB,1TB SSD, 14 OLED,Backlit": "₹184,999",
                "Dell Thin & Light Laptop R7-5825U, 8GB, 512GB SSD, 15.6 FHD, W11": "₹65,999"
            },
            {
                "feature": "RAM",
                "Lenovo Thin & Light Laptop Ultra 9-185H,32GB,1TB SSD, 14 OLED,Backlit": "32GB",
                "Dell Thin & Light Laptop R7-5825U, 8GB, 512GB SSD, 15.6 FHD, W11": "8GB"
            },
            {
                "feature": "Storage", 
                "Lenovo Thin & Light Laptop Ultra 9-185H,32GB,1TB SSD, 14 OLED,Backlit": "1TB SSD",
                "Dell Thin & Light Laptop R7-5825U, 8GB, 512GB SSD, 15.6 FHD, W11": "512GB SSD"
            }
        ]

🚨 CRITICAL: In comparison table rows, use EXACT FULL product names as keys
- The keys in table rows MUST match the product_name field exactly
- NEVER use shortened or truncated product names as keys
- Example: If product_name is "OnePlus Android Smartphone Nord CE5 5G (8GB RAM, 128GB Storage/ROM) CPH2717 Black Infinity", 
  use that EXACT string as the key, not "OnePlus Android Smartphone Nord CE5 5G"
    },
    "authentication": {"message": "Ready to help"},
    "end": "Which laptop seems better suited for your needs? Would you like more details about either one?"
}

REMEMBER: Use tools naturally and intelligently based on user needs!
"""

# Create LLM class
# llm = ChatGoogleGenerativeAI(
#     model= "gemini-2.5-flash",
#     temperature=0.7,
#     max_retries=2,
#     google_api_key=google_api_key,
# )
from langchain_openai import ChatOpenAI
import os

openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",  # fast + cost effective
    temperature=0,        # better accuracy & deterministic
    max_retries=3,        # increased for better reliability
    request_timeout=30,   # 30 second timeout
    max_tokens=4000,      # limit response length
    api_key=openai_api_key,
)


# Bind tools to the model
model = llm.bind_tools([search_products, get_near_store, get_filtered_product_details_tool, search_terms_conditions, collect_user_contact])
# Test the model with tools
# res=model.invoke(f"What is the weather in Berlin on {datetime.today()}?")

# print(res)

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
import traceback

tools_by_name = {tool.name: tool for tool in tools}

def estimate_token_count(messages):
    """Estimate token count for messages (rough approximation)"""
    total_chars = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total_chars += len(str(msg.content))
    # Rough estimate: 1 token ≈ 4 characters for English text
    return total_chars // 4

def truncate_conversation(messages, max_tokens=12000):
    """Truncate conversation to fit within token limits"""
    system_msg = messages[0] if messages and hasattr(messages[0], 'type') and 'system' in messages[0].type.lower() else None
    other_messages = messages[1:] if system_msg else messages
    
    # Keep system message and recent messages
    truncated = []
    if system_msg:
        truncated.append(system_msg)
    
    # Keep the last few messages to maintain context
    recent_messages = other_messages[-10:]  # Keep last 10 messages
    truncated.extend(recent_messages)
    
    # If still too long, keep only the most recent
    if estimate_token_count(truncated) > max_tokens:
        truncated = [system_msg] + other_messages[-5:] if system_msg else other_messages[-5:]
    
    return truncated

def call_tool(state: AgentState):
    outputs = []
    user_id = state.get("user_id", "default_user")
    
    print(f"🔧 Executing tool calls for user: {user_id}")
    
    # Iterate over the tool calls in the last message
    # Iterate over the tool calls in the last message
    for tool_call in state["messages"][-1].tool_calls:
        print(f"🛠️  Calling tool: {tool_call['name']} with args: {tool_call['args']}")
        # Get the tool by name
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        print(f"📋 Tool result length: {len(str(tool_result))} characters")
        
        tool_message = ToolMessage(
            content=tool_result,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        outputs.append(tool_message)
        
        # Don't save ToolMessage to Redis to avoid conversation flow issues
        # redis_memory.add_message_to_user(user_id, tool_message)
    
    print(f"🎯 Returning {len(outputs)} tool message(s)")
    return {"messages": outputs}

def call_model(
    state: AgentState,
    config: RunnableConfig,
):
    # Get user ID from state
    user_id = state.get("user_id", "default_user")
    
    # Get user authentication status
    auth_state = redis_memory.get_user_auth_state(user_id)
    user_auth_status = 'new'  # Always start fresh, let LLM handle everything
    user_phone = auth_state.get('phone_number')
    
    print(f"🔐 call_model: User {user_id} auth status: {user_auth_status}")
    
    # Get the current conversation messages from state
    messages = state["messages"]
    
    # Input validation to prevent BadRequestError
    if not messages:
        print("⚠️ No messages in state, creating default response")
        from langchain_core.messages import AIMessage
        default_response = AIMessage(content=json.dumps({
            "answer": "Hello! I'm your Lotus Electronics assistant. How can I help you today?",
            "products": [],
            "product_details": {},
            "stores": [],
            "policy_info": {},
            "comparison": {},
            "authentication": {"message": "Ready to help"},
            "end": "What's your phone number?"
        }))
        return {"messages": [default_response]}
    
    print(f"🔍 Processing {len(messages)} messages from state")
    
    # Validate message content before processing
    for i, msg in enumerate(messages):
        if hasattr(msg, 'content') and msg.content:
            # Check for extremely long content that might cause issues
            if len(str(msg.content)) > 10000:
                print(f"⚠️ Message {i} is very long ({len(str(msg.content))} chars), truncating...")
                msg.content = str(msg.content)[:10000] + "... [truncated]"
        elif hasattr(msg, 'content'):
            # Handle empty or None content
            if msg.content is None or str(msg.content).strip() == "":
                print(f"⚠️ Message {i} has empty content, setting default")
                if hasattr(msg, 'type') and msg.type == 'human':
                    msg.content = "Hello"
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    msg.content = '{"answer": "How can I help you?", "end": "What are you looking for?"}'
    
    # Get the latest user message for debugging
    latest_user_message = None
    conversation_context = []
    
    # Analyze conversation history to extract product context
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            if latest_user_message is None:
                latest_user_message = msg.content
            conversation_context.append(msg.content)
            if len(conversation_context) >= 3:  # Get last 3 user messages for context
                break
    
    if latest_user_message:
        print(f"🔍 Processing user query: '{latest_user_message}'")
        # Add context awareness to debug output
        if len(conversation_context) > 1:
            print(f"📝 Conversation context: {conversation_context[-2::-1]}")  # Show previous messages
        
        # Debug: Show current message types in state
        message_types = []
        for msg in messages:
            if hasattr(msg, 'type'):
                message_types.append(msg.type)
        print(f"🗂️  Current message types in state: {message_types}")
    
    # Create dynamic system prompt with authentication status
    auth_context = f"""
USER AUTHENTICATION STATUS: {user_auth_status.upper()}
USER PHONE: {user_phone if user_phone else 'Not provided'}

CRITICAL: Based on authentication status:
- Use all available tools naturally
- Let LLM decide when contact collection is needed
- System is smart and adaptive
"""
    
    dynamic_system_prompt = SYSTEM_PROMPT + auth_context
    
    # For model compatibility, we need to ensure proper message sequence
    # Different models have different requirements:
    # - Gemini: Strict alternating human-ai pattern, no tool messages
    # - OpenAI: Allows tool messages and requires them after tool calls
    
    # Detect model type
    model_name = getattr(model, 'model_name', str(model))
    is_gemini = 'gemini' in model_name.lower() or 'google' in str(type(model)).lower()
    is_openai = 'openai' in str(type(model)).lower() or 'gpt' in model_name.lower()
    
    print(f"🤖 Model type detected: {model_name}, is_gemini: {is_gemini}, is_openai: {is_openai}")
    
    filtered_messages = []
    last_type = None
    
    if is_gemini:
        # Gemini: Apply strict filtering - alternating pattern, no tool messages
        for msg in messages:
            if hasattr(msg, 'type'):
                # Skip tool messages as they can break Gemini flow
                if msg.type == 'tool':
                    continue
                # Only add if type is different from last (alternating pattern)
                if msg.type != last_type and msg.type in ['human', 'ai']:
                    filtered_messages.append(msg)
                    last_type = msg.type
    else:
        # OpenAI: Ensure proper tool call sequence
        expecting_tool_response = False
        pending_tool_call_ids = set()
        
        for i, msg in enumerate(messages):
            if not hasattr(msg, 'type'):
                continue
                
            print(f"🔍 Processing message {i}: type={msg.type}")
            
            # Handle AI messages with tool calls
            if msg.type == 'ai' and hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"🔧 AI message has {len(msg.tool_calls)} tool calls")
                filtered_messages.append(msg)
                expecting_tool_response = True
                pending_tool_call_ids = {tc['id'] for tc in msg.tool_calls}
                
            # Handle tool response messages
            elif msg.type == 'tool':
                if expecting_tool_response and hasattr(msg, 'tool_call_id'):
                    print(f"🔧 Tool response for call_id: {msg.tool_call_id}")
                    filtered_messages.append(msg)
                    pending_tool_call_ids.discard(msg.tool_call_id)
                    if not pending_tool_call_ids:
                        expecting_tool_response = False
                else:
                    print(f"⚠️ Skipping orphaned tool message")
                    
            # Handle other message types
            elif msg.type in ['human', 'ai']:
                # If we were expecting tool responses, create dummy responses
                if expecting_tool_response and pending_tool_call_ids:
                    print(f"⚠️ Creating dummy tool responses for {len(pending_tool_call_ids)} pending calls")
                    from langchain_core.messages import ToolMessage
                    for tool_call_id in pending_tool_call_ids:
                        dummy_response = ToolMessage(
                            content="Tool execution completed",
                            tool_call_id=tool_call_id
                        )
                        filtered_messages.append(dummy_response)
                    expecting_tool_response = False
                    pending_tool_call_ids.clear()
                
                # Add the current message
                filtered_messages.append(msg)
        
        # Handle any remaining pending tool calls at the end
        if expecting_tool_response and pending_tool_call_ids:
            print(f"⚠️ Creating final dummy tool responses for {len(pending_tool_call_ids)} pending calls")
            from langchain_core.messages import ToolMessage
            for tool_call_id in pending_tool_call_ids:
                dummy_response = ToolMessage(
                    content="Tool execution completed",
                    tool_call_id=tool_call_id
                )
                filtered_messages.append(dummy_response)
    
    print(f"📝 Call_model filtered sequence: {[msg.type for msg in filtered_messages]}")
    
    # Ensure we have at least one valid message
    if not filtered_messages:
        print("⚠️ No valid messages after filtering, creating minimal conversation")
        from langchain_core.messages import HumanMessage
        filtered_messages = [HumanMessage(content="Hello")]
    
    # Use only the filtered messages with system prompt
    messages_with_system = [SystemMessage(content=dynamic_system_prompt)] + filtered_messages
    
    try:
        # Validate messages before sending to avoid BadRequestError
        total_tokens = estimate_token_count(messages_with_system)
        if total_tokens > 15000:  # Conservative limit for gpt-4o-mini
            print(f"⚠️ Token count too high ({total_tokens}), truncating conversation...")
            messages_with_system = truncate_conversation(messages_with_system)
        
        print(f"📊 Sending {len(messages_with_system)} messages to model (est. {total_tokens} tokens)")
        
        # Additional debugging - validate message structure
        for i, msg in enumerate(messages_with_system):
            if hasattr(msg, 'content'):
                content_preview = str(msg.content)[:100] + "..." if len(str(msg.content)) > 100 else str(msg.content)
                print(f"  📝 Message {i} ({getattr(msg, 'type', 'unknown')}): {content_preview}")
            else:
                print(f"  ⚠️  Message {i} has no content attribute: {type(msg)}")
        
        # Invoke the model with the system prompt and the messages
        response = model.invoke(messages_with_system, config)
        
        # Debug: Check if the model called any tools
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"✅ Model called {len(response.tool_calls)} tool(s): {[tc['name'] for tc in response.tool_calls]}")
            # Debug: Show tool parameters
            for tool_call in response.tool_calls:
                print(f"🔧 Tool parameters: {tool_call['args']}")
        else:
            print("⚠️  Model did not call any tools")
            # Debug: Show response content preview
            if hasattr(response, 'content'):
                content_preview = response.content[:100] + "..." if len(response.content) > 100 else response.content
                print(f"📝 Response content preview: {content_preview}")
        
        # Save the new response to Redis (only HumanMessage and AIMessage)
        if hasattr(response, 'type') and response.type == 'ai':
            redis_memory.add_message_to_user(user_id, response)
        
        # We return a list, because this will get added to the existing messages state using the add_messages reducer
        return {"messages": [response]}
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print(f"❌ Error in call_model: {error_type}: {error_msg}")
        
        # Handle specific error types
        if "BadRequestError" in error_type:
            print("🔍 BadRequestError details:")
            print(f"   - Message count: {len(messages_with_system)}")
            print(f"   - Estimated tokens: {estimate_token_count(messages_with_system)}")
            print(f"   - Latest user message: {latest_user_message[:100] if latest_user_message else 'None'}...")
            
            # Try to identify the specific issue
            if "maximum context length" in error_msg.lower() or "context_length_exceeded" in error_msg.lower():
                error_response_content = "I apologize, but our conversation has become too long. Please start a new chat to continue."
            elif "tool_calls" in error_msg.lower() and "must be followed" in error_msg.lower():
                error_response_content = "I encountered an issue with tool execution flow. Let me try again with a fresh approach."
            elif "invalid request" in error_msg.lower() or "malformed" in error_msg.lower():
                error_response_content = "I encountered an issue with the request format. Please try rephrasing your question."
            elif "token" in error_msg.lower() and "limit" in error_msg.lower():
                error_response_content = "Your message is too long. Please try asking in a shorter way."
            else:
                error_response_content = "I'm experiencing technical difficulties with the AI service. Please try again."
        
        elif "RateLimitError" in error_type:
            error_response_content = "I'm currently handling many requests. Please wait a moment and try again."
        
        elif "AuthenticationError" in error_type:
            error_response_content = "There's an authentication issue with our AI service. Please contact support."
        
        else:
            error_response_content = f"I encountered an unexpected error ({error_type}). Please try again."
        
        print(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Create a simple error response
        from langchain_core.messages import AIMessage
        error_response = AIMessage(content=json.dumps({
            "answer": error_response_content,
            "end": "How else can I help you with Lotus Electronics products?"
        }))
        return {"messages": [error_response]}


# Define the conditional edge that determines whether to continue or not
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    # Debug: show what type of message we're evaluating
    print(f"🔍 Evaluating message type: {getattr(last_message, 'type', 'unknown')}")
    
    # If called after LLM node and the last message has tool_calls, continue to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("🔄 AI made tool calls - continuing to tool execution...")
        return "continue"
    
    # If called after tools node and the last message is a tool result, continue back to LLM
    # for intelligent processing of the tool results
    if hasattr(last_message, 'type') and last_message.type == 'tool':
        print("🔄 Tool execution complete - continuing to LLM for intelligent response")
        return "continue"
        
    # If the last message is an AI message without tool calls, end
    if hasattr(last_message, 'type') and last_message.type == 'ai' and not hasattr(last_message, 'tool_calls'):
        print("🏁 AI response without tools - ending conversation")
        return "end"
    
    # Default fallback - end conversation
    print("🏁 Default case - ending conversation")
    return "end"


from langgraph.graph import StateGraph, END

# Define a new graph with our state
workflow = StateGraph(AgentState)

# 1. Add our nodes 
workflow.add_node("llm", call_model)
workflow.add_node("tools",  call_tool)
# 2. Set the entrypoint as `agent`, this is the first node called
workflow.set_entry_point("llm")
# 3. Add a conditional edge after the `llm` node is called.
workflow.add_conditional_edges(
    # Edge is used after the `llm` node is called.
    "llm",
    # The function that will determine which node is called next.
    should_continue,
    # Mapping for where to go next, keys are strings from the function return, and the values are other nodes.
    # END is a special node marking that the graph is finish.
    {
        # If `tools`, then we call the tool node.
        "continue": "tools",
        # Otherwise we finish.
        "end": END,
    },
)
# 4. Add a conditional edge after `tools` is called to continue back to LLM for processing
workflow.add_conditional_edges(
    # Edge is used after the `tools` node is called.
    "tools",
    # The function that will determine what happens after tool execution
    should_continue,
    # Tools now return data to LLM for intelligent processing
    {
        # Continue back to LLM for intelligent response creation
        "continue": "llm",
        # End only when LLM creates final response
        "end": END,
    },
)

# Add checkpointing for better state management and recovery
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# Now we can compile and visualize our graph with checkpointing
graph = workflow.compile(checkpointer=checkpointer)

from datetime import datetime

def get_or_create_user_id():
    """Get user ID from input or create a new one."""
    user_input = input("Enter your user ID (or press Enter for new user): ").strip()
    if user_input:
        return user_input
    else:
        new_user_id = str(uuid.uuid4())[:8]  # Short UUID
        print(f"Created new user ID: {new_user_id}")
        return new_user_id

def display_user_stats(user_id: str):
    """Display user conversation statistics."""
    messages = redis_memory.get_user_messages(user_id)
    print(f"\n--- User {user_id} Stats ---")
    print(f"Stored messages: {len(messages)}")
    print(f"Active users: {len(redis_memory.get_active_users())}")
    print("-" * 30)

def chat_with_agent(message: str, session_id: str = "default_session") -> str:
    """
    Chat with the Lotus Electronics agent for Flask integration.
    
    Args:
        message: User's message
        session_id: Unique session identifier for conversation memory
        
    Returns:
        JSON string response from the agent
    """
    try:
        # Use session_id as user_id for Redis memory
        user_id = session_id
        
        # Check Redis connection health
        redis_available = hasattr(redis_memory, 'test_connection') and redis_memory.test_connection()
        if not redis_available:
            print("⚠️  Redis not available - running without conversation memory")
        
        # Check user authentication state - simplified approach
        auth_state = redis_memory.get_user_auth_state(user_id) if redis_available else {'state': 'new', 'phone_number': None}
        user_auth_status = auth_state.get('state', 'new')
        user_phone = auth_state.get('phone_number')
        
        print(f"🔐 User {user_id} auth state: {user_auth_status}")
        print(f"📱 User {user_id} phone: {user_phone}")
        print(f"🔍 Full auth state: {auth_state}")
        
        # Handle authentication flow - ensure message is a string
        if not isinstance(message, str):
            message = str(message) if message is not None else ""
        message_lower = message.lower().strip()
        
        # Import regex module for pattern matching
        import re
        
        
        # Store user phone for context if available
        if user_phone:
            print(f"✅ User {user_id} has phone: {user_phone}")
        
        # Create user message
        from langchain_core.messages import HumanMessage
        user_msg = HumanMessage(content=message)
        
        # Load previous conversation context 
        previous_messages = []
        if redis_available:
            previous_messages = redis_memory.get_user_messages(user_id)
        
        # Filter and limit conversation history based on model type
        # Different models have different conversation flow requirements
        context_messages = []
        last_message_type = None
        
        # Detect if we're using Gemini or OpenAI (same logic as in call_model)
        model_name = getattr(llm, 'model_name', str(llm))
        is_gemini = 'gemini' in model_name.lower() or 'google' in str(type(llm)).lower()
        is_openai = 'openai' in str(type(llm)).lower() or 'gpt' in model_name.lower()
        
        if is_gemini:
            # Gemini: Apply strict alternating pattern filtering
            for msg in previous_messages[-10:]:  # Look at more messages to filter properly
                if hasattr(msg, 'type') and msg.type in ['human', 'ai']:
                    # Only add message if it's different from the last type (alternating pattern)
                    if msg.type != last_message_type:
                        context_messages.append(msg)
                        last_message_type = msg.type
                        
                        # Limit to last 6 alternating messages for context
                        if len(context_messages) >= 6:
                            break
        else:
            # OpenAI: Use recent messages with less strict filtering
            for msg in previous_messages[-8:]:  # Keep more recent messages for OpenAI
                if hasattr(msg, 'type') and msg.type in ['human', 'ai', 'tool']:
                    context_messages.append(msg)
        
        print(f"📝 Filtered message sequence: {[msg.type for msg in context_messages]}")
        
        # Save user message to Redis memory if available
        if redis_available:
            redis_memory.add_message_to_user(user_id, user_msg)
        
        # Prepare inputs for the graph with conversation context
        # For Gemini: Ensure the final sequence is valid (avoid human-human sequence)
        final_context = context_messages.copy()
        if is_gemini and final_context and final_context[-1].type == 'human':
            final_context = final_context[:-1]  # Remove last human message to avoid human-human sequence
            print(f"📝 Adjusted sequence to avoid human-human: {[msg.type for msg in final_context]}")
        
        all_messages = final_context + [user_msg]
        print(f"📝 Final message sequence: {[msg.type for msg in all_messages]}")
        
        inputs = {
            "messages": all_messages,
            "user_id": user_id,
            "number_of_steps": 0
        }
        
        # Configure checkpointing with thread ID based on session
        config = {"configurable": {"thread_id": session_id}}
        
        # Process through the graph
        final_response = None
        response_count = 0
        max_iterations = 15  # Prevent infinite loops
        
        for state in graph.stream(inputs, config=config, stream_mode="values"):
            response_count += 1
            if response_count > max_iterations:
                break
                
            # Get the last message from the final state
            if "messages" in state and state["messages"]:
                last_message = state["messages"][-1]
                if hasattr(last_message, 'content') and hasattr(last_message, 'type'):
                    # Accept AI responses as final (tools now feed data to LLM for processing)
                    if last_message.type == 'ai' and last_message.content:
                        print(f"🤖 Got AI response: {len(last_message.content)} chars")
                        final_response = last_message.content
                        # Don't break here - let the conversation continue if there are more tool calls
        
        # Clean and validate the response
        if final_response:
            # Ensure final_response is a string
            if not isinstance(final_response, str):
                final_response = str(final_response) if final_response is not None else ""
            
            print(f"🔧 Raw final_response: {final_response[:200]}...")
            
            # Clean the response from any markdown formatting and extract JSON
            clean_response = final_response.strip()
            
            # Handle cases where response contains both text and JSON
            # Look for JSON block first
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', clean_response, re.DOTALL)
            if json_match:
                clean_response = json_match.group(1).strip()
                print("🔧 Extracted JSON from markdown block")
            elif clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
                print("🔧 Removed markdown formatting")
            
            # If response looks like an array or list, try to extract JSON from it
            if clean_response.startswith('[') and clean_response.endswith(']'):
                try:
                    # Parse as array and look for JSON string
                    response_array = json.loads(clean_response)
                    if isinstance(response_array, list):
                        for item in response_array:
                            if isinstance(item, str):
                                # Try to parse each string item as JSON
                                try:
                                    if item.strip().startswith('{') and item.strip().endswith('}'):
                                        clean_response = item.strip()
                                        print("🔧 Extracted JSON from array")
                                        break
                                    elif '```json' in item:
                                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', item, re.DOTALL)
                                        if json_match:
                                            clean_response = json_match.group(1).strip()
                                            print("🔧 Extracted JSON from array item")
                                            break
                                except:
                                    continue
                except:
                    pass
            
            # Final fallback - look for any JSON object in the response
            if not (clean_response.startswith('{') and clean_response.endswith('}')):
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', clean_response, re.DOTALL)
                if json_match:
                    clean_response = json_match.group(0)
                    print("🔧 Extracted JSON using fallback regex")
            
            print(f"🔧 Clean response: {clean_response[:200]}...")
            
            try:
                # Check if it's already valid JSON
                parsed_json = json.loads(clean_response)
                print(f"🔧 Initial parsing successful. Keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"❌ Response that failed to parse: {clean_response[:500]}")
                # Return a fallback response
                return json.dumps({
                    "answer": "I found some information for you, but I'm having trouble formatting the response properly. Could you please rephrase your question?",
                    "products": [],
                    "product_details": {},
                    "stores": [],
                    "policy_info": {},
                    "comparison": {},
                    "authentication": {"message": "Ready to help"},
                    "end": "How else can I help you with Lotus Electronics products?"
                })
            
            try:
                # Handle deeply nested JSON structure from data.answer field
                def parse_nested_structure(data_dict):
                    """Recursively parse nested JSON structures and product details output"""
                    if isinstance(data_dict, dict):
                        # Check for data.answer structure first (most complex nesting)
                        if 'data' in data_dict and isinstance(data_dict['data'], dict):
                            data_content = data_dict['data']
                            if 'answer' in data_content and isinstance(data_content['answer'], str):
                                try:
                                    # Parse the nested JSON in data.answer
                                    nested_json = json.loads(data_content['answer'])
                                    if isinstance(nested_json, dict):
                                        # Recursively process any further nesting
                                        nested_json = parse_nested_structure(nested_json)
                                        return nested_json
                                except (json.JSONDecodeError, TypeError) as e:
                                    print(f"🔧 Failed to parse data.answer as JSON: {e}")
                            # If data.answer parsing fails, return the data content
                            return data_content
                        
                        # Check for direct answer field with nested JSON
                        if 'answer' in data_dict and isinstance(data_dict['answer'], str):
                            try:
                                # Try to parse answer as JSON first
                                nested_json = json.loads(data_dict['answer'])
                                if isinstance(nested_json, dict):
                                    # Recursively process the nested JSON
                                    nested_json = parse_nested_structure(nested_json)
                                    return nested_json
                            except (json.JSONDecodeError, TypeError) as e:
                                print(f"🔧 Failed to parse direct answer as JSON: {e}")
                        
                        # Process product_details output field if present at any level
                        if 'product_details' in data_dict and isinstance(data_dict['product_details'], dict):
                            if 'output' in data_dict['product_details']:
                                try:
                                    import ast
                                    output_str = data_dict['product_details']['output']
                                    print(f"🔧 Parsing product_details output: {output_str[:100]}...")
                                    product_details_obj = ast.literal_eval(output_str)
                                    data_dict['product_details'] = product_details_obj
                                    print(f"✅ Successfully parsed product details")
                                except (ValueError, SyntaxError) as e:
                                    print(f"❌ Error parsing product details output: {e}")
                                    # If parsing fails, keep the original structure
                                    pass
                    
                    return data_dict
                
                # Apply nested structure parsing
                print(f"🔧 Original response structure: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else type(parsed_json)}")
                parsed_json = parse_nested_structure(parsed_json)
                print(f"🔧 Final response structure: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else type(parsed_json)}")

                # --- Product Comparison Table Enhancement ---
                # If a comparison field exists, fill the table with actual values from product_details/specs
                try:
                    if isinstance(parsed_json, dict) and 'comparison' in parsed_json and isinstance(parsed_json['comparison'], dict):
                        comparison = parsed_json['comparison']
                        products = comparison.get('products', [])
                        table = comparison.get('table', [])
                        criteria = comparison.get('criteria', [])
                        print(f"🔧 Found comparison section with {len(products)} products, {len(criteria)} criteria, {len(table)} table rows")
                    else:
                        # Initialize variables if comparison section doesn't exist
                        products = []
                        table = []
                        criteria = []
                        print(f"🔧 No comparison section found in response, skipping table processing")
                    
                    # Ensure table is a list and all items are dictionaries
                    if not isinstance(table, list):
                        table = []
                    
                    # Check if table needs to be filled - only process if table is empty or has invalid structure
                    table_needs_filling = False
                    if not table:
                        table_needs_filling = True
                    else:
                        try:
                            # Check if all rows are dictionaries and mostly empty/dashes
                            table_needs_filling = all(
                                isinstance(row, dict) and 
                                all((v == '-' or v == '' or v is None) for k, v in row.items() if k != 'feature')
                                for row in table
                            )
                        except (AttributeError, TypeError):
                            # If any row is not a dict or has other issues, rebuild the table
                            table_needs_filling = True
                    
                    # If table needs filling and we have products and criteria
                    if products and criteria and table_needs_filling:
                        print(f"🔧 Building comparison table for {len(products)} products with {len(criteria)} criteria")
                        print(f"🔧 Products: {[p.get('product_name', 'Unknown') for p in products if isinstance(p, dict)]}")
                        print(f"🔧 Criteria: {criteria}")
                        
                        # Build a mapping: {product_name: {feature: value}}
                        prod_map = {}
                        for prod in products:
                            if not isinstance(prod, dict):
                                continue
                            pname = prod.get('product_name') or prod.get('product_id')
                            if not pname:
                                continue
                            
                            print(f"🔧 Processing product: {pname}")
                            prod_map[pname] = {}
                            
                            # Extract basic product information
                            if 'product_mrp' in prod:
                                prod_map[pname]['Price'] = prod['product_mrp']
                                prod_map[pname]['MRP'] = prod['product_mrp']
                            
                            # Extract features as individual specs
                            if 'features' in prod and isinstance(prod['features'], list):
                                for i, feature in enumerate(prod['features']):
                                    if isinstance(feature, str):
                                        # Use feature as both key and value
                                        prod_map[pname][feature] = '✔'
                                        # Also create numbered feature entries
                                        prod_map[pname][f'Feature {i+1}'] = feature
                            
                            # Try to get specs from product_specification
                            specs = prod.get('product_specification') or []
                            if isinstance(specs, list):
                                for spec in specs:
                                    if isinstance(spec, dict):
                                        if 'fkey' in spec and 'fvalue' in spec:
                                            fkey = spec['fkey']
                                            fvalue = spec['fvalue']
                                            # Handle cases where fkey might be a list or other type
                                            if isinstance(fkey, str):
                                                key = fkey.strip()
                                            elif isinstance(fkey, list):
                                                key = str(fkey[0]).strip() if fkey else ""
                                            else:
                                                key = str(fkey).strip()
                                            
                                            # Handle cases where fvalue might be a list or other type
                                            if isinstance(fvalue, str):
                                                value = fvalue
                                            elif isinstance(fvalue, list):
                                                value = str(fvalue[0]) if fvalue else ""
                                            else:
                                                value = str(fvalue)
                                            
                                            if key:  # Only add if key is not empty
                                                prod_map[pname][key] = value
                                        # Also try other common spec field names
                                        elif 'name' in spec and 'value' in spec:
                                            name_val = spec['name']
                                            value_val = spec['value']
                                            if isinstance(name_val, str) and isinstance(value_val, str):
                                                prod_map[pname][name_val] = value_val
                                        elif 'specification' in spec and 'detail' in spec:
                                            spec_val = spec['specification']
                                            detail_val = spec['detail']
                                            if isinstance(spec_val, str) and isinstance(detail_val, str):
                                                prod_map[pname][spec_val] = detail_val
                            
                            # Extract info from product name and features dynamically
                            product_name_lower = pname.lower()
                            
                            # Dynamic RAM extraction - look for any number followed by "gb ram"
                            import re
                            ram_patterns = [
                                r'(\d+)\s*gb\s*ram',
                                r'\((\d+)gb\s*ram',
                                r'(\d+)gb\s*ram\)',
                                r'(\d+)\s*gb\s*(?:memory)',
                            ]
                            for pattern in ram_patterns:
                                ram_match = re.search(pattern, product_name_lower)
                                if ram_match:
                                    prod_map[pname]['RAM'] = f"{ram_match.group(1)}GB"
                                    break
                            
                            # Dynamic Storage extraction - look for any number followed by storage indicators
                            storage_patterns = [
                                r'(\d+)\s*gb\s*(?:storage|rom)',
                                r'\((\d+)gb\s*(?:storage|rom)',
                                r'(\d+)gb\s*(?:storage|rom)\)',
                                r'(\d+)\s*gb\s*(?:internal)',
                            ]
                            for pattern in storage_patterns:
                                storage_match = re.search(pattern, product_name_lower)
                                if storage_match:
                                    prod_map[pname]['Storage'] = f"{storage_match.group(1)}GB"
                                    break
                            
                            # Dynamic Brand extraction - extract first word that looks like a brand
                            brand_match = re.search(r'^(\w+)', pname)
                            if brand_match:
                                potential_brand = brand_match.group(1)
                                # Only consider it a brand if it's not a common tech word
                                tech_words = ['android', 'smartphone', 'mobile', 'phone', 'device']
                                if potential_brand.lower() not in tech_words:
                                    prod_map[pname]['Brand'] = potential_brand.title()
                            
                            # Dynamic Model extraction - try to extract meaningful model info
                            # Remove brand and common words to get model
                            model_text = pname
                            common_words = ['android', 'smartphone', 'mobile', 'phone', 'gb', 'ram', 'storage', 'rom']
                            for word in common_words:
                                model_text = re.sub(rf'\b{word}\b', '', model_text, flags=re.IGNORECASE)
                            
                            # Extract what looks like a model (letters + numbers)
                            model_match = re.search(r'([a-zA-Z]+\s*\d+[a-zA-Z]*(?:\s+[a-zA-Z]+)?)', model_text)
                            if model_match:
                                prod_map[pname]['Model'] = model_match.group(1).strip().title()
                            
                            # Dynamic connectivity detection
                            if '5g' in product_name_lower:
                                prod_map[pname]['Connectivity'] = '5G'
                            elif '4g' in product_name_lower:
                                prod_map[pname]['Connectivity'] = '4G'
                            
                            # Extract from features array dynamically
                            if 'features' in prod and isinstance(prod['features'], list):
                                for feature in prod['features']:
                                    if isinstance(feature, str):
                                        feature_lower = feature.lower()
                                        
                                        # Look for processor/chipset info
                                        if any(chip in feature_lower for chip in ['snapdragon', 'mediatek', 'exynos', 'dimensity', 'bionic']):
                                            prod_map[pname]['Processor'] = feature
                                        
                                        # Look for camera info
                                        if 'mp' in feature_lower or 'camera' in feature_lower:
                                            prod_map[pname]['Camera'] = feature
                                        
                                        # Look for display info
                                        if any(display in feature_lower for display in ['display', 'screen', 'oled', 'amoled', 'lcd']):
                                            prod_map[pname]['Display'] = feature
                                        
                                        # Look for battery info
                                        if 'mah' in feature_lower or 'battery' in feature_lower:
                                            prod_map[pname]['Battery'] = feature
                                        
                                        # Look for OS info
                                        if 'android' in feature_lower or 'ios' in feature_lower:
                                            prod_map[pname]['OS'] = feature
                            
                            # Add price (always available)
                            if 'product_mrp' in prod and prod['product_mrp']:
                                prod_map[pname]['Price'] = prod['product_mrp']
                            
                            # Add warranty info if available
                            if 'warranty' in prod and prod['warranty']:
                                prod_map[pname]['Warranty'] = prod['warranty']
                            
                            print(f"🔧 Product map for {pname}: {list(prod_map[pname].keys())}")
                            print(f"🔧 Values: {prod_map[pname]}")
                        
                        # Build the table with actual data
                        new_table = []
                        for feature in criteria:
                            if not isinstance(feature, str):
                                continue
                            row = {'feature': feature}
                            
                            for prod in products:
                                if not isinstance(prod, dict):
                                    continue
                                pname = prod.get('product_name') or prod.get('product_id')
                                if pname:
                                    # Try to find the feature value
                                    val = prod_map.get(pname, {}).get(feature, '-')
                                    
                                    # If not found, try case-insensitive matching
                                    if val == '-':
                                        feature_lower = feature.lower()
                                        for key, value in prod_map.get(pname, {}).items():
                                            if key.lower() == feature_lower:
                                                val = value
                                                break
                                    
                                    # If still not found, try partial matching
                                    if val == '-':
                                        for key, value in prod_map.get(pname, {}).items():
                                            if feature_lower in key.lower() or key.lower() in feature_lower:
                                                val = value
                                                break
                                    
                                    row[pname] = val if val not in [None, ''] else '-'
                            new_table.append(row)
                        
                        # If all values are still dashes, create a dynamic comparison with available info
                        if all(all(v == '-' for k, v in row.items() if k != 'feature') for row in new_table):
                            print("🔧 All values are dashes, creating dynamic comparison")
                            new_table = []
                            
                            # Dynamically determine what features are available across all products
                            all_available_features = set()
                            for prod in products:
                                if isinstance(prod, dict):
                                    pname = prod.get('product_name') or prod.get('product_id')
                                    if pname and pname in prod_map:
                                        all_available_features.update(prod_map[pname].keys())
                            
                            print(f"🔧 Available features across products: {all_available_features}")
                            
                            # If no features found in prod_map, create a basic comparison with what we have
                            if not all_available_features:
                                print("🔧 No features found in prod_map, creating basic comparison")
                                basic_features = ['Price', 'Brand', 'Model']
                                for feature in basic_features:
                                    row = {'feature': feature}
                                    for prod in products:
                                        if isinstance(prod, dict):
                                            pname = prod.get('product_name', 'Unknown Product')
                                            if feature == 'Price':
                                                row[pname] = prod.get('product_mrp', '-')
                                            elif feature == 'Brand':
                                                # Extract brand from product name (first word)
                                                import re
                                                brand_match = re.search(r'^(\w+)', pname)
                                                row[pname] = brand_match.group(1).title() if brand_match else '-'
                                            elif feature == 'Model':
                                                # Use product name as model
                                                row[pname] = pname[:50] + '...' if len(pname) > 50 else pname
                                            else:
                                                row[pname] = '-'
                                    new_table.append(row)
                            else:
                                # Prioritize features based on importance
                                feature_priority = [
                                    'Price', 'Brand', 'RAM', 'Storage', 'Model', 'Connectivity', 
                                    'Processor', 'Camera', 'Display', 'Battery', 'OS', 'Warranty'
                                ]
                                
                                # Create comparison with available features in priority order
                                for feature in feature_priority:
                                    if feature in all_available_features:
                                        row = {'feature': feature}
                                        has_data = False
                                        for prod in products:
                                            if not isinstance(prod, dict):
                                                continue
                                            pname = prod.get('product_name') or prod.get('product_id')
                                            if pname:
                                                val = prod_map.get(pname, {}).get(feature, '-')
                                                row[pname] = val
                                                if val != '-':
                                                    has_data = True
                                        if has_data:
                                            new_table.append(row)
                                
                                # Add any remaining features not in priority list
                                remaining_features = all_available_features - set(feature_priority)
                                for feature in sorted(remaining_features):
                                    row = {'feature': feature}
                                    has_data = False
                                    for prod in products:
                                        if not isinstance(prod, dict):
                                            continue
                                        pname = prod.get('product_name') or prod.get('product_id')
                                        if pname:
                                            val = prod_map.get(pname, {}).get(feature, '-')
                                            row[pname] = val
                                            if val != '-':
                                                has_data = True
                                    if has_data:
                                        new_table.append(row)
                        
                        parsed_json['comparison']['table'] = new_table
                        print(f"🔧 Created comparison table with {len(new_table)} rows")
                        # Debug: Show actual keys in the table
                        if new_table:
                            print(f"🔧 Sample table row keys: {list(new_table[0].keys())}")
                            print(f"🔧 Expected product names: {[p.get('product_name', 'Unknown') for p in products]}")

                    # Post-process comparison table to fix key mismatches
                    if isinstance(parsed_json, dict) and 'comparison' in parsed_json and isinstance(parsed_json['comparison'], dict):
                        comparison = parsed_json['comparison']
                        if 'table' in comparison and 'products' in comparison:
                            table = comparison['table']
                            products = comparison['products']
                            
                            if isinstance(table, list) and isinstance(products, list) and table and products:
                                print("🔧 Post-processing comparison table to fix key mismatches")
                                
                                # Create mapping from partial names to full names
                                name_mapping = {}
                                for product in products:
                                    if isinstance(product, dict) and 'product_name' in product:
                                        full_name = product['product_name']
                                        # Create potential shortened versions
                                        words = full_name.split()
                                        for i in range(2, min(len(words), 8)):  # Try different lengths
                                            partial_name = ' '.join(words[:i])
                                            name_mapping[partial_name] = full_name
                                
                                print(f"🔧 Name mapping: {name_mapping}")
                                
                                # Fix the table keys
                                fixed_table = []
                                for row in table:
                                    if isinstance(row, dict):
                                        fixed_row = {'feature': row.get('feature', '')}
                                        for key, value in row.items():
                                            if key != 'feature':
                                                # Try to find the full name for this key
                                                mapped_name = name_mapping.get(key, key)
                                                fixed_row[mapped_name] = value
                                        fixed_table.append(fixed_row)
                                
                                parsed_json['comparison']['table'] = fixed_table
                                print(f"🔧 Fixed comparison table keys. Sample row: {fixed_table[0] if fixed_table else 'No rows'}")

                except Exception as e:
                    print(f"❌ Error in comparison table processing: {type(e).__name__}: {e}")
                    # Keep the original comparison structure if processing fails

                # Ensure we have the expected structure - if it's missing top-level fields, try to extract them
                if isinstance(parsed_json, dict):
                    # If we don't have expected keys, the LLM might have wrapped everything in a data field
                    expected_keys = {'answer', 'products', 'product_details', 'stores', 'end'}
                    current_keys = set(parsed_json.keys())
                    
                    if not any(key in current_keys for key in expected_keys):
                        print("⚠️  Response doesn't have expected structure. Trying to extract from nested fields...")
                        # Try to find the actual response structure in nested fields
                        if 'data' in parsed_json:
                            parsed_json = parsed_json['data']
                            print(f"🔧 Extracted from data field. New keys: {list(parsed_json.keys())}")

                # Return properly formatted JSON
                print(f"🔧 Final parsed_json before return: {str(parsed_json)[:300]}...")
                print(f"🔧 Final parsed_json keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
                
                # Validate final response has required fields
                if isinstance(parsed_json, dict):
                    if not parsed_json.get('answer'):
                        print("⚠️ Missing answer field, adding default")
                        parsed_json['answer'] = "I found some information for you."
                    if 'end' not in parsed_json:
                        parsed_json['end'] = "How else can I help you?"
                    
                    # Ensure we have the basic structure
                    required_fields = ['products', 'product_details', 'stores', 'policy_info', 'comparison', 'authentication']
                    for field in required_fields:
                        if field not in parsed_json:
                            if field == 'authentication':
                                parsed_json[field] = {"required": False, "step": "verified", "message": ""}
                            elif field == 'comparison':
                                parsed_json[field] = {"products": [], "criteria": [], "table": []}
                            else:
                                parsed_json[field] = [] if field in ['products', 'stores'] else {}
                else:
                    print("⚠️ parsed_json is not a dict, creating fallback")
                    parsed_json = {
                        "answer": "Can you ask me again later? I'm being asked too many queries right now by users which is  more than usual, so I can't do that for you right now.",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "comparison": {"products": [], "criteria": [], "table": []},
                        "authentication": {"required": False, "step": "verified", "message": ""},
                        "end": "Please wait for some time and ask again."
                    }
                
                final_json = json.dumps(parsed_json, ensure_ascii=False, indent=2)
                
                # Final validation - ensure we're not returning empty content
                if not final_json or final_json.strip() == "" or final_json == "{}":
                    print("⚠️ Final JSON is empty, using emergency fallback")
                    emergency_response = {
                        "answer": "Can you ask me again later? I'm being asked too many queries right now by users which is  more than usual, so I can't do that for you right now.",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "comparison": {"products": [], "criteria": [], "table": []},
                        "authentication": {"required": False, "step": "verified", "message": ""},
                        "end": "Please wait for some time and ask again. "
                    }
                    return json.dumps(emergency_response, ensure_ascii=False, indent=2)
                
                return final_json
                
            except json.JSONDecodeError as e:
                print(f"🔧 JSON parsing failed: {e}")
                print(f"🔧 Problematic response: {clean_response[:500]}...")
                
                # Try to extract meaningful content from the raw response
                response_text = final_response
                
                # If response contains array-like structure, try to extract text
                if '[' in response_text and ']' in response_text:
                    try:
                        # Look for quoted strings in the array
                        text_matches = re.findall(r'"([^"]+)"', response_text)
                        if text_matches:
                            # Use the first meaningful text that's not JSON
                            for match in text_matches:
                                if not match.strip().startswith('{') and len(match.strip()) > 10:
                                    response_text = match
                                    break
                    except:
                        pass
                
                # Create a proper JSON response from the extracted text
                fallback_response = {
                    "answer": response_text if response_text else "Can you ask me again later? I'm being asked too many queries right now by users which is  more than usual, so I can't do that for you right now.",
                    "products": [],
                    "product_details": {},
                    "stores": [],
                    "policy_info": {},
                    "comparison": {},
                    "authentication": {"required": False, "step": "verified", "message": ""},
                    "end": " Please wait for some time and ask again. "
                }
                
                return json.dumps(fallback_response, ensure_ascii=False, indent=2)
                # Provide contextual responses based on user message
                user_msg_lower = message.lower() if message else ""
                
                if any(greeting in user_msg_lower for greeting in ['hello', 'hi', 'hey', 'helo']):
                    fallback_response = {
                        "answer": "Hello! Welcome to Lotus Electronics! I'm here to help you find the perfect electronics products. What are you looking for today?",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "end": "I can help you find TVs, smartphones, laptops, home appliances, and more. What interests you?"
                    }
                elif any(help_word in user_msg_lower for help_word in ['help', 'assist', 'support']):
                    fallback_response = {
                        "answer": "I'd be happy to help! I can assist you with finding products, getting detailed specifications, locating nearby stores, and checking availability.",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "end": "What would you like to explore - TVs, smartphones, laptops, or something else?"
                    }
                elif any(thanks in user_msg_lower for thanks in ['thanks', 'thank you', 'thx']):
                    fallback_response = {
                        "answer": "You're welcome! I'm glad I could help.",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "end": "Is there anything else you'd like to know about our electronics collection?"
                    }
                else:
                    # Generic fallback with the original response
                    fallback_response = {
                        "answer": clean_response if clean_response else "I understand. How can I help you with Lotus Electronics products?",
                        "products": [],
                        "product_details": {},
                        "stores": [],
                        "policy_info": {},
                        "end": "Are you looking for any specific electronics or need help finding a store?"
                    }
                
                return json.dumps(fallback_response, ensure_ascii=False, indent=2)
        else:
            # Default response if no content
            error_response = {
                "answer": "Can you ask me again later? I'm being asked too many queries right now by users which is  more than usual, so I can't do that for you right now.",
                "products": [],
                "product_details": {},
                "stores": [],
                "policy_info": {},
                "end": "Please wait for some time and ask again."
            }
            return json.dumps(error_response, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"❌ Error in chat_with_agent: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Specific handling for different error types
        if "Input/output error" in str(e) or "Errno 5" in str(e):
            error_message = "I'm experiencing connectivity issues. Please check if Redis server is running and try again."
        elif "Redis" in str(e):
            error_message = "Database connection issue. Please ensure Redis server is running on localhost:6379."
        elif "JSON" in str(e) or "json" in str(e):
            error_message = "Response parsing issue. This usually happens with complex product queries."
        elif "tool" in str(e).lower():
            error_message = "Tool execution issue. This might be a search or database problem."
        else:
            error_message = f"Technical issue occurred: {str(e)}. Please try again in a moment."
        
        # Error response in JSON format
        error_response = {
            "answer": f"Can you ask me again later? I'm being asked too many queries right now by users which is  more than usual, so I can't do that for you right now.",
            "error": f"I'm sorry, there was a technical issue. {error_message}",
            "products": [],
            "product_details": {},
            "stores": [],
            "policy_info": {},
            "end": "Please wait for some time and ask again."
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)

# Main execution - only run when script is executed directly
if __name__ == "__main__":
    # Get user ID
    user_id = get_or_create_user_id()
    display_user_stats(user_id)

    # Welcome message
    print("\n" + "="*60)
    print("🏪 Welcome to Lotus Electronics Official Chatbot! 🏪")
    print("Your trusted partner for all electronics needs")
    print("="*60)
    print("\n💡 What can I help you with:")
    print("   • Find electronics products (laptops, smartphones, TVs, etc.)")
    print("   • Get store locations")
    print("   • Browse our complete product catalog")
    print("   • Ask about policies and offers")
    print("\n� Available commands:")
    print("   • Ask about any electronics products")
    print("   • Ask about store locations ('find store in [city]')")
    print("   • Ask for product details ('tell me more about that Samsung phone')")
    print("   • 'stats' - View your conversation stats")  
    print("   • 'clear' - Clear conversation history and reset authentication")
    print("   • 'quit'/'exit'/'bye' - End conversation")
    print("\n🔍 Example queries (after authentication):")
    print("   • 'Show me Samsung ACs under 50000'")
    print("   • 'Find gaming laptops between 60000 and 100000'")
    print("   • 'I need wireless headphones'")
    print("   • 'Tell me more about that iPhone' (after seeing product list)")
    print("   • 'Find store in Indore'")
    print("   • 'Show me stores near 452001'")
    print("   • 'What is your return policy?'")
    print("   • 'Tell me about warranty terms'")
    print("   • 'How do you protect my privacy?'")
    print("   • 'What are the refund conditions?'")
    print("-"*60)

    # Chat loop
    while True:
        try:
            # Create our initial message dictionary
            input_message = input("\n🛍️ Lotus Electronics Customer: ")
            
            if input_message.lower() in ['quit', 'exit', 'bye']:
                print("Thank you for visiting Lotus Electronics! Have a great day! 🙏")
                break
            elif input_message.lower() == 'clear':
                redis_memory.clear_user_messages(user_id)
                redis_memory.clear_user_auth(user_id)  # Also clear authentication
                print("✅ Conversation history and authentication cleared!")
                continue
            elif input_message.lower() == 'stats':
                display_user_stats(user_id)
                continue
            
            # Use the chat_with_agent function
            response = chat_with_agent(input_message, user_id)
            
            # Parse and display the response
            try:
                # Ensure response is a string
                if not isinstance(response, str):
                    response = str(response) if response is not None else "{}"
                
                # Clean the response if it contains markdown formatting
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    # Remove markdown json formatting
                    clean_response = clean_response.replace('```json', '').replace('```', '').strip()
                
                parsed_json = json.loads(clean_response)
                
                # Display formatted response
                print(f"\n🤖 Lotus Electronics Assistant:")
                print(f"💬 {parsed_json.get('answer', '')}")
                
                if 'products' in parsed_json and parsed_json['products']:
                    print(f"\n📦 Products Found ({len(parsed_json['products'])}):")
                    for i, product in enumerate(parsed_json['products'], 1):
                        print(f"\n{i}. 🏷️ {product.get('product_name', 'N/A')}")
                        print(f"   💰 Price: {product.get('product_mrp', 'N/A')}")
                        if product.get('features'):
                            print(f"   ✨ Features: {', '.join(product['features'][:2])}")
                        if product.get('product_url'):
                            print(f"   🔗 URL: {product['product_url']}")
                
                if 'product_details' in parsed_json and parsed_json['product_details']:
                    details = parsed_json['product_details']
                    print(f"\n🔍 Product Details:")
                    print(f"📱 {details.get('product_name', 'N/A')}")
                    print(f"💰 Price: ₹{details.get('product_mrp', 'N/A')}")
                    print(f"📦 SKU: {details.get('product_sku', 'N/A')}")
                    if details.get('instock'):
                        stock_status = "✅ In Stock" if details['instock'].lower() == 'yes' else "❌ Out of Stock"
                        print(f"📦 Stock: {stock_status}")
                    
                    # Display top 5 specifications with priority for warranty
                    if details.get('product_specification') and isinstance(details['product_specification'], list):
                        specs = details['product_specification']
                        
                        # Look for warranty and move to front
                        warranty_spec = None
                        filtered_specs = []
                        for spec in specs:
                            if isinstance(spec, dict) and spec.get('fkey') and 'warranty' in spec['fkey'].lower():
                                warranty_spec = spec
                            else:
                                filtered_specs.append(spec)
                        
                        # Create final specs list with warranty first
                        final_specs = []
                        if warranty_spec:
                            final_specs.append(warranty_spec)
                        final_specs.extend(filtered_specs[:4] if warranty_spec else filtered_specs[:5])
                        
                        print(f"📋 Key Specifications:")
                        for spec in final_specs:
                            if isinstance(spec, dict) and spec.get('fkey') and spec.get('fvalue'):
                                print(f"   • {spec['fkey']}: {spec['fvalue']}")
                    
                    if details.get('meta_desc'):
                        desc = details['meta_desc'][:150] + "..." if len(details['meta_desc']) > 150 else details['meta_desc']
                        print(f"📝 Description: {desc}")
                    
                    if details.get('del'):
                        delivery = details['del']
                        print(f"🚚 Delivery Options:")
                        if delivery.get('std'):
                            print(f"   • Standard: {delivery['std']}")
                        if delivery.get('t3h'):
                            print(f"   • Express: {delivery['t3h']}")
                        if delivery.get('stp'):
                            print(f"   • Store Pickup: {delivery['stp']}")
                
                if 'stores' in parsed_json and parsed_json['stores']:
                    print(f"\n🏪 Stores Found ({len(parsed_json['stores'])}):")
                    for i, store in enumerate(parsed_json['stores'], 1):
                        print(f"\n{i}. 🏬 {store.get('store_name', 'N/A')}")
                        print(f"   📍 {store.get('address', 'N/A')}, {store.get('city', 'N/A')} - {store.get('zipcode', 'N/A')}, {store.get('state', 'N/A')}")
                        print(f"   🕒 {store.get('timing', 'N/A')}")
                
                if 'authentication' in parsed_json and parsed_json['authentication']:
                    auth_info = parsed_json['authentication']
                    # Simple authentication message display
                    if auth_info.get('message'):
                        print(f"✅ {auth_info['message']}")
                
                if 'end' in parsed_json and parsed_json['end']:
                    print(f"\n❓ {parsed_json['end']}")
                    
            except json.JSONDecodeError as e:
                print(f"\n🤖 Lotus Electronics Assistant:")
                # Try to extract JSON from the response if it's wrapped in other text
                try:
                    # Look for JSON pattern in the response
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        parsed_json = json.loads(json_str)
                        print(f"💬 {parsed_json.get('answer', '')}")
                        
                        if 'products' in parsed_json and parsed_json['products']:
                            print(f"\n📦 Products Found ({len(parsed_json['products'])}):")
                            for i, product in enumerate(parsed_json['products'], 1):
                                print(f"\n{i}. 🏷️ {product.get('product_name', 'N/A')}")
                                print(f"   💰 Price: {product.get('product_mrp', 'N/A')}")
                                if product.get('features'):
                                    print(f"   ✨ Features: {', '.join(product['features'][:2])}")
                        
                        if 'product_details' in parsed_json and parsed_json['product_details']:
                            details = parsed_json['product_details']
                            print(f"\n🔍 Product Details:")
                            print(f"📱 {details.get('product_name', 'N/A')}")
                            print(f"💰 Price: ₹{details.get('product_mrp', 'N/A')}")
                            if details.get('instock'):
                                stock_status = "✅ In Stock" if details['instock'].lower() == 'yes' else "❌ Out of Stock"
                                print(f"📦 Stock: {stock_status}")
                            
                            # Display key specifications
                            if details.get('product_specification') and isinstance(details['product_specification'], list):
                                specs = details['product_specification'][:5]  # Top 5 specs
                                print(f"📋 Key Specifications:")
                                for spec in specs:
                                    if isinstance(spec, dict) and spec.get('fkey') and spec.get('fvalue'):
                                        print(f"   • {spec['fkey']}: {spec['fvalue']}")
                        
                        if 'stores' in parsed_json and parsed_json['stores']:
                            print(f"\n🏪 Stores Found ({len(parsed_json['stores'])}):")
                            for i, store in enumerate(parsed_json['stores'], 1):
                                print(f"\n{i}. 🏬 {store.get('store_name', 'N/A')}")
                                print(f"   📍 {store.get('address', 'N/A')}")
                        
                        if 'end' in parsed_json and parsed_json['end']:
                            print(f"\n❓ {parsed_json['end']}")
                    else:
                        # Fallback: display raw response
                        print(response)
                except:
                    print(response)
                
        except KeyboardInterrupt:
            print("\nThank you for visiting Lotus Electronics! Have a great day! 🙏")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print("Please try again or contact our support team.")
            continue
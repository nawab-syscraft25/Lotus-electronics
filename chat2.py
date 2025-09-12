import os
import uuid
import re
from langgraph.checkpoint.memory import InMemorySaver
from collections import deque
from datetime import datetime, timedelta
import json
import redis
import pickle
from langchain.chat_models import init_chat_model

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages



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
    """Redis-based memory for storing user conversations with TTL."""
    
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
    
# from langchain_tavily import TavilySearch

# tavily_tool = TavilySearch(max_results=2,tavily_api_key=tavily_api_key)

tools = [search_products, get_near_store, get_filtered_product_details_tool, search_terms_conditions]

from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

# System prompt for Lotus Electronics chatbot

# System prompt for Lotus Electronics chatbot
SYSTEM_PROMPT = """You are Lotus Electronics Sales Assistant - helping customers find electronics products and store locations in India.

CRITICAL RESPONSE FORMAT REQUIREMENT:
You MUST respond with EXACTLY this JSON structure - NO nested JSON strings, NO escaped quotes, NO additional wrapping:

{
  "answer": "your conversational response only - NO product details or store details here",
  "products": [array of product objects if search_products was used],
  "product_details": {product object if get_filtered_product_details_tool was used},
  "stores": [array of store objects if get_near_store was used],
  "comparison": {"products": [list of compared product objects], "criteria": [list of compared features/specs], "table": [array of comparison rows]},
  "policy_info": {policy object if search_terms_conditions was used},
  "end": "follow-up question to continue conversation"
}

TOOL USAGE RULES:
1. Use search_products ONLY when user asks for NEW products they haven't seen yet
2. Use get_near_store ONLY when user asks about store locations by city or zipcode
3. Use get_filtered_product_details_tool when user wants MORE DETAILS about a specific product from previous results (extract product_id from conversation context)
4. Use search_terms_conditions when user asks about:
   - Return policy ("return", "return it", "want to return")
   - Refund policy ("refund", "money back", "refund conditions")
   - Warranty terms ("warranty", "guarantee", "warranty terms")
   - Privacy policy ("privacy", "data protection", "personal information")
   - Terms and conditions ("terms", "conditions", "policy")
   - Cancellation policy ("cancel", "cancellation")
   - Shipping/delivery terms ("shipping policy", "delivery terms")

PRODUCT COMPARISON FEATURE:
When user asks to compare two or more products (by name, brand, or product_id):
- Use get_filtered_product_details_tool for each product to get details.
- Compare at least 2 products, but support 3 or more if requested.
- Identify and compare key features/specs, price, warranty, and any user-requested criteria.
- In the JSON response, fill the "comparison" field as follows:
    "comparison": {
        "products": [list of compared product objects],
        "criteria": ["feature1", "feature2", ...],
        "table": [
            {"feature": "Display Size", "Samsung A36": "6.5\"", "iPhone 14": "6.1\""},
            {"feature": "RAM", "Samsung A36": "8GB", "iPhone 14": "6GB"},
            ...
        ]
    }
- In the "answer" field, provide a conversational summary of the comparison, highlighting strengths and best use cases for each product.
- Do NOT put the comparison table or product specs in the "answer" field.
- If user asks "which is better" or "which should I buy", give a helpful recommendation in the "answer" field based on the comparison.
- If comparison is not possible (e.g., missing data), explain in the "answer" field and set "comparison" to an empty object {}.

5. DON'T use tools when discussing general product info that doesn't need specific details

IMPORTANT POLICY RESPONSE RULE:
When using search_terms_conditions, DO NOT put raw policy sections in policy_info field. Instead:
- Summarize the policy information in a clear, conversational way in the "answer" field
- Set policy_info to empty object {}
- Make the answer comprehensive and user-friendly based on the tool results

MANDATORY: If user mentions "return", "refund", "warranty", "policy", "terms", or "conditions" - YOU MUST use search_terms_conditions tool and summarize the results in your answer.

IMPORTANT: When user refers to a specific product from previous search results (like "tell me more about that Samsung phone"), you MUST:
- Extract the product_id from the previous search results in conversation context
- Use the product_id with get_filtered_product_details_tool
- Use user's city preference for accurate stock information
- If user Say other Search for other brand products with same product category like smartphone the search result give smartphone of Samsung company if user say other then search fro Onepluse Smartphone or Oppo Vivo or iPhone.

CRITICAL JSON RESPONSE RULES:
❌ NEVER create nested JSON strings inside JSON
❌ NEVER wrap responses in additional data objects
❌ NEVER escape quotes in JSON values
❌ NEVER put JSON as string values
✅ Return clean, direct JSON structure
✅ Put actual objects/arrays in fields, not strings

CRITICAL ANSWER FIELD RULES:
❌ NEVER put product names, prices, or specs in "answer"
❌ NEVER put store names, addresses, or timings in "answer"
❌ NEVER put detailed product specifications in "answer"
❌ NEVER put policy text or terms content in "answer"
✅ Only put conversational guidance and insights in "answer"
✅ Set unused fields to empty arrays [] or objects {} as appropriate

EXAMPLES OF CORRECT RESPONSES:
When user asks "show me phones":
{
  "answer": "I found some great smartphones for you! These offer excellent value and modern features.",
  "products": [{"product_id": "123", "product_url":"https://www.lotuselectronics.com/product/smartphones/samsung-android-smartphone-a36-5g-8gb-ram-128gb-storagerom-a366ej-awesome-lavender/39721", "product_name": "Samsung Galaxy A36", "product_mrp": "30999", ...}],
  "stores": [],
  "product_details": {},
  "comparison": {},
  "end": "What's your budget range?"
}

When user asks "tell me more about that Samsung phone" (referring to product_id from previous results):
{
  "answer": "Here are the complete specifications and availability details for that Samsung smartphone.",
  "products": [],
  "product_details": {"product_id": "123","product_url":"https://www.lotuselectronics.com/product/smartphones/samsung-android-smartphone-a36-5g-8gb-ram-128gb-storagerom-a366ej-awesome-lavender/39721", "product_name": "Samsung Galaxy A36", "product_specification": [...], ...},
  "stores": [],
  "comparison": {}
  "end": "Would you like to check availability at a nearby store?"
}

When user asks "find store in Delhi":
{
  "answer": "Perfect! I found several Lotus stores in Delhi where you can visit.",
  "products": [],
  "product_details": {},
  "stores": [{"store_name": "Lotus CP", "address": "Connaught Place", ...}],
  "policy_info": {},
  "comparison": {}
  "end": "Which area is most convenient for you?"
}

When user asks "what is your return policy":
{
  "answer": "Our return policy allows you to return unopened items in original packaging within 7 days of delivery for a full refund (excluding shipping costs). For damaged or defective products, contact us within 7 days for a replacement at no cost. Please note that used or tampered items may incur deduction charges of 5% to full value depending on condition. Refunds are processed to your original payment method.",
  "products": [],
  "product_details": {},
  "stores": [],
  "policy_info": {},
  "comparison": {}
  "end": "Do you have a specific product you'd like to return or any other questions about our policies?"
}

CRITICAL POLICY_INFO RULES:
❌ NEVER nest policy tool results in additional objects like "search_terms_conditions_response"
❌ NEVER wrap policy data in extra fields
✅ Put the search_terms_conditions tool result DIRECTLY in the policy_info field
✅ Use the exact JSON structure returned by the tool without modification

CONVERSATION INTELLIGENCE:
- Remember what products/stores were already shown
- When user says "tell me more about that Samsung phone" - use get_filtered_product_details_tool with the product_id
- When user says "what about the store timings" - answer from previous store results
- Track user preferences (budget, brands, features) across conversation
- Extract product_id from previous search results when user asks for specific product details
- Always use the user's city preference for stock availability when getting product details
- Sort The Product Based on user Query.

SALES APPROACH:
- Be helpful and conversational
- Guide users toward purchase decisions
- Suggest visiting stores for hands-on experience
- Ask relevant follow-up questions
- Focus on customer needs and value
- Highlight stock availability and delivery options

REMEMBER: Return ONLY the JSON structure above. NO additional text, NO markdown formatting, NO nested JSON strings."""


# Create LLM class
llm = ChatGoogleGenerativeAI(
    model= "gemini-2.5-flash",
    temperature=0.7,
    max_retries=2,
    google_api_key=google_api_key,
)

# Bind tools to the model
model = llm.bind_tools([search_products, get_near_store, get_filtered_product_details_tool, search_terms_conditions])

# Test the model with tools
# res=model.invoke(f"What is the weather in Berlin on {datetime.today()}?")

# print(res)

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig

tools_by_name = {tool.name: tool for tool in tools}

def call_tool(state: AgentState):
    outputs = []
    user_id = state.get("user_id", "default_user")
    
    print(f"🔧 Executing tool calls for user: {user_id}")
    
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
    
    # Get the current conversation messages from state
    messages = state["messages"]
    
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
    
    # For Gemini, we need to ensure proper message sequence
    # Use only the current conversation state messages with system prompt
    messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    try:
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
        print(f"❌ Error in call_model: {e}")
        # Create a simple error response
        from langchain_core.messages import AIMessage
        error_response = AIMessage(content=json.dumps({
            "answer": "I'm sorry, I encountered an error while processing your request. Please try again.",
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
        
        # Create user message
        from langchain_core.messages import HumanMessage
        user_msg = HumanMessage(content=message)
        
        # Load previous conversation context (limited for Gemini compatibility)
        previous_messages = []
        if redis_available:
            previous_messages = redis_memory.get_user_messages(user_id)
        
        # Filter and limit conversation history for better Gemini compatibility
        context_messages = []
        for msg in previous_messages[-6:]:  # Only last 6 messages for context
            if hasattr(msg, 'type') and msg.type in ['human', 'ai']:
                context_messages.append(msg)
        
        # Save user message to Redis memory if available
        if redis_available:
            redis_memory.add_message_to_user(user_id, user_msg)
        
        # Prepare inputs for the graph with conversation context
        all_messages = context_messages + [user_msg]
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
            # Clean the response from any markdown formatting
            clean_response = final_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            
            try:
                # Check if it's already valid JSON
                parsed_json = json.loads(clean_response)
                print(f"🔧 Initial parsing successful. Keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
                
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
                if isinstance(parsed_json, dict) and 'comparison' in parsed_json and isinstance(parsed_json['comparison'], dict):
                    comparison = parsed_json['comparison']
                    products = comparison.get('products', [])
                    table = comparison.get('table', [])
                    criteria = comparison.get('criteria', [])
                    # If table is empty or filled with only dashes, try to fill it
                    if products and criteria and (not table or all(all((v == '-' or v == '' or v is None) for k, v in row.items() if k != 'feature') for row in table)):
                        # Build a mapping: {product_name: {feature: value}}
                        prod_map = {}
                        for prod in products:
                            pname = prod.get('product_name') or prod.get('product_id')
                            prod_map[pname] = {}
                            # Try to get specs from product_specification or features
                            specs = prod.get('product_specification') or []
                            if isinstance(specs, list):
                                for spec in specs:
                                    if isinstance(spec, dict) and 'fkey' in spec and 'fvalue' in spec:
                                        prod_map[pname][spec['fkey'].strip()] = spec['fvalue']
                            # Add basic fields
                            if 'product_mrp' in prod:
                                prod_map[pname]['MRP'] = prod['product_mrp']
                            if 'warranty' in prod:
                                prod_map[pname]['Warranty'] = prod['warranty']
                            if 'features' in prod and isinstance(prod['features'], list):
                                for f in prod['features']:
                                    prod_map[pname][f] = '✔'
                        # Build the table
                        new_table = []
                        for feature in criteria:
                            row = {'feature': feature}
                            for prod in products:
                                pname = prod.get('product_name') or prod.get('product_id')
                                val = prod_map.get(pname, {}).get(feature, '-')
                                row[pname] = val if val not in [None, ''] else '-'
                            new_table.append(row)
                        parsed_json['comparison']['table'] = new_table

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
                return json.dumps(parsed_json, ensure_ascii=False, indent=2)
                
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', clean_response, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_match.group(0)
                        parsed_json = json.loads(extracted_json)
                        
                        # Apply the same nested structure parsing to extracted JSON
                        parsed_json = parse_nested_structure(parsed_json)
                        
                        return json.dumps(parsed_json, ensure_ascii=False, indent=2)
                    except:
                        pass
                
                # Wrap non-JSON response in JSON format with contextual handling
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
                "answer": "I apologize, but I couldn't process your request at the moment. Please try again or contact our support team.",
                "products": [],
                "product_details": {},
                "stores": [],
                "policy_info": {},
                "end": "How else can I assist you with Lotus Electronics products today?"
            }
            return json.dumps(error_response, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"❌ Error in chat_with_agent: {type(e).__name__}: {str(e)}")
        
        # Specific handling for different error types
        if "Input/output error" in str(e) or "Errno 5" in str(e):
            error_message = "I'm experiencing connectivity issues. Please check if Redis server is running and try again."
        elif "Redis" in str(e):
            error_message = "Database connection issue. Please ensure Redis server is running on localhost:6379."
        else:
            error_message = f"Technical issue occurred: {str(e)}. Please try again in a moment."
        
        # Error response in JSON format
        error_response = {
            "answer": f"I'm sorry, there was a technical issue. {error_message}",
            "products": [],
            "product_details": {},
            "stores": [],
            "policy_info": {},
            "end": "Is there anything else I can help you with from our electronics collection?"
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
    print("\n💡 Available commands:")
    print("   • Ask about any electronics products")
    print("   • Ask about store locations ('find store in [city]')")
    print("   • Ask for product details ('tell me more about that Samsung phone')")
    print("   • 'stats' - View your conversation stats")  
    print("   • 'clear' - Clear conversation history")
    print("   • 'quit'/'exit'/'bye' - End conversation")
    print("\n🔍 Example queries:")
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
                print("✅ Conversation history cleared!")
                continue
            elif input_message.lower() == 'stats':
                display_user_stats(user_id)
                continue
            
            # Use the chat_with_agent function
            response = chat_with_agent(input_message, user_id)
            
            # Parse and display the response
            try:
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

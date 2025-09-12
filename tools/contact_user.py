import sqlite3
import os
from datetime import datetime

# Get the absolute path to the database file in the main project directory
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "messages.db")

# Initialize DB
def init_db():
    print(f"🗄️  Initializing database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            phone_number TEXT,
            session_id TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully")

# Store message
def store_message(phone_number, session_id, message):
    print(f"💾 Storing message to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO messages (timestamp, phone_number, session_id, message) VALUES (?, ?, ?, ?)",
                   (timestamp, phone_number, session_id, message))
    conn.commit()
    conn.close()
    print(f"✅ Message stored for {phone_number} at {timestamp}")
    return {"status": "success", "message": f"Contact information saved for {phone_number}"}

# Get all stored messages (for debugging/admin purposes)
def get_all_messages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC")
    messages = cursor.fetchall()
    conn.close()
    return messages

# Get messages for a specific phone number
def get_messages_by_phone(phone_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE phone_number = ? ORDER BY timestamp DESC", (phone_number,))
    messages = cursor.fetchall()
    conn.close()
    return messages

# Example usage
init_db()
# store_message("+919876543210", "session_123", "Hello, stored in database!")

import sqlite3
import os

print('Checking conversation.db...')
if os.path.exists('conversation.db'):
    conn = sqlite3.connect('conversation.db')
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'Tables found: {tables}')
    
    # Check conversations table
    table_names = [table[0] for table in tables]
    if 'conversations' in table_names:
        cursor.execute('SELECT COUNT(*) FROM conversations')
        count = cursor.fetchone()[0]
        print(f'Total conversations: {count}')
        
        if count > 0:
            cursor.execute('SELECT session_id, message_type, timestamp FROM conversations ORDER BY timestamp DESC LIMIT 5')
            recent = cursor.fetchall()
            print(f'Recent conversations: {recent}')
    
    # Check if admin table exists
    if 'admin_users' in table_names:
        cursor.execute('SELECT username FROM admin_users')
        admins = cursor.fetchall()
        print(f'Admin users: {admins}')
    
    conn.close()
else:
    print('conversation.db does not exist')

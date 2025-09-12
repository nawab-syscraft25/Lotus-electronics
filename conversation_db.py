import sqlite3
import json
from datetime import datetime
import logging
import os

# Database file path
DB_PATH = "conversation.db"

class ConversationDB:
    """Database handler for storing conversations and logs"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_type TEXT NOT NULL CHECK (message_type IN ('human', 'ai')),
                message_content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_phone TEXT,
                response_metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                logger_name TEXT,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                error_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create admin users table (for dashboard authentication)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level)')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if not exists
        self.create_default_admin()
    
    def create_default_admin(self):
        """Create a default admin user"""
        import hashlib
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute('SELECT id FROM admin_users WHERE username = ?', ('admin',))
        if cursor.fetchone() is None:
            # Create default admin with password 'admin123'
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, email)
                VALUES (?, ?, ?)
            ''', ('admin', password_hash, 'admin@lotuselectronics.com'))
            conn.commit()
            print("✅ Default admin user created - Username: admin, Password: admin123")
        
        conn.close()
    
    def store_conversation(self, session_id, message_type, message_content, user_phone=None, response_metadata=None):
        """Store a conversation message"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(response_metadata) if response_metadata else None
            
            cursor.execute('''
                INSERT INTO conversations (session_id, message_type, message_content, user_phone, response_metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, message_type, message_content, user_phone, metadata_json))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error storing conversation: {e}")
            return False
    
    def store_log(self, level, logger_name, message, session_id=None, error_details=None):
        """Store a system log"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_logs (level, logger_name, message, session_id, error_details)
                VALUES (?, ?, ?, ?, ?)
            ''', (level, logger_name, message, session_id, error_details))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing log: {e}")
            return False
    
    def get_conversations(self, limit=100, offset=0, session_id=None, start_date=None, end_date=None):
        """Get conversations with pagination and date filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query with filters
        query = "SELECT * FROM conversations WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        conversations = []
        columns = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
            conversation = dict(zip(columns, row))
            # Parse response_metadata if it exists
            if conversation['response_metadata']:
                try:
                    conversation['response_metadata'] = json.loads(conversation['response_metadata'])
                except:
                    conversation['response_metadata'] = None
            conversations.append(conversation)
        
        conn.close()
        return conversations
    
    def get_conversation_count(self, session_id=None, start_date=None, end_date=None):
        """Get total count of conversations with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM conversations WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_unique_users(self, start_date=None, end_date=None):
        """Get list of unique users (session_ids) with their conversation counts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                session_id,
                user_phone,
                COUNT(*) as message_count,
                MAX(timestamp) as last_activity,
                MIN(timestamp) as first_activity
            FROM conversations 
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += '''
            GROUP BY session_id, user_phone 
            ORDER BY last_activity DESC
        '''
        
        cursor.execute(query, params)
        
        users = []
        columns = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
            user = dict(zip(columns, row))
            users.append(user)
        
        conn.close()
        return users
    
    def get_conversation_thread(self, session_id, start_date=None, end_date=None):
        """Get complete conversation thread for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM conversations 
            WHERE session_id = ?
        '''
        params = [session_id]
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp ASC"
        
        cursor.execute(query, params)
        
        conversations = []
        columns = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
            conversation = dict(zip(columns, row))
            # Parse response_metadata if it exists
            if conversation['response_metadata']:
                try:
                    conversation['response_metadata'] = json.loads(conversation['response_metadata'])
                except:
                    conversation['response_metadata'] = None
            conversations.append(conversation)
        
        conn.close()
        return conversations
        
        columns = [description[0] for description in cursor.description]
        conversations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return conversations
    
    def get_logs(self, limit=100, offset=0, level=None):
        """Get system logs with pagination"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if level:
            cursor.execute('''
                SELECT * FROM system_logs 
                WHERE level = ? 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            ''', (level, limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM system_logs 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        columns = [description[0] for description in cursor.description]
        logs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return logs
    
    def get_conversation_stats(self):
        """Get conversation statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total conversations
        cursor.execute('SELECT COUNT(*) FROM conversations')
        total_conversations = cursor.fetchone()[0]
        
        # Total sessions
        cursor.execute('SELECT COUNT(DISTINCT session_id) FROM conversations')
        total_sessions = cursor.fetchone()[0]
        
        # Today's conversations
        cursor.execute('''
            SELECT COUNT(*) FROM conversations 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        today_conversations = cursor.fetchone()[0]
        
        # Total logs
        cursor.execute('SELECT COUNT(*) FROM system_logs')
        total_logs = cursor.fetchone()[0]
        
        # Error logs today
        cursor.execute('''
            SELECT COUNT(*) FROM system_logs 
            WHERE level IN ('ERROR', 'CRITICAL') 
            AND DATE(timestamp) = DATE('now')
        ''')
        error_logs_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_conversations': total_conversations,
            'total_sessions': total_sessions,
            'today_conversations': today_conversations,
            'total_logs': total_logs,
            'error_logs_today': error_logs_today
        }
    
    def verify_admin(self, username, password):
        """Verify admin credentials"""
        import hashlib
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            SELECT id, username, email FROM admin_users 
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        admin = cursor.fetchone()
        
        if admin:
            # Update last login
            cursor.execute('''
                UPDATE admin_users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (admin[0],))
            conn.commit()
            
            conn.close()
            return {
                'id': admin[0],
                'username': admin[1],
                'email': admin[2]
            }
        
        conn.close()
        return None

# Custom logging handler to store logs in database
class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that stores logs in database"""
    
    def __init__(self, conversation_db):
        super().__init__()
        self.conversation_db = conversation_db
    
    def emit(self, record):
        """Emit a log record to database"""
        try:
            # Format the log message
            message = self.format(record)
            
            # Extract session_id if present in the record
            session_id = getattr(record, 'session_id', None)
            
            # Get error details if it's an exception
            error_details = None
            if record.exc_info:
                import traceback
                error_details = traceback.format_exception(*record.exc_info)
                error_details = ''.join(error_details)
            
            # Store in database
            self.conversation_db.store_log(
                level=record.levelname,
                logger_name=record.name,
                message=message,
                session_id=session_id,
                error_details=error_details
            )
        except Exception:
            # Don't let logging errors break the application
            pass

# Initialize the conversation database
conversation_db = ConversationDB()

# Set up database logging handler
db_log_handler = DatabaseLogHandler(conversation_db)
db_log_handler.setLevel(logging.INFO)
db_log_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

# Add the handler to the root logger
logging.getLogger().addHandler(db_log_handler)

if __name__ == "__main__":
    # Test the database
    print("Testing ConversationDB...")
    
    # Test conversation storage
    conversation_db.store_conversation(
        session_id="test_session_1",
        message_type="human",
        message_content="Hello, I'm looking for smartphones",
        user_phone="9876543210"
    )
    
    conversation_db.store_conversation(
        session_id="test_session_1",
        message_type="ai",
        message_content="I found some great smartphones for you!",
        response_metadata={"products_count": 5, "search_query": "smartphones"}
    )
    
    # Test log storage
    conversation_db.store_log(
        level="INFO",
        logger_name="test_logger",
        message="Test log message",
        session_id="test_session_1"
    )
    
    # Get stats
    stats = conversation_db.get_conversation_stats()
    print(f"Stats: {stats}")
    
    print("✅ ConversationDB test completed successfully!")

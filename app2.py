# app.py (production-ready, with admin dashboard)

import os
import logging
import json
import csv
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for, make_response
from flask_cors import CORS

# Import your modules
from chat_gpt_working import chat_with_agent, redis_memory
from tools.product_search_tool import ProductSearchTool
from conversation_db import ConversationDB
from memory_utils import MemoryTracker, check_memory_limit, log_memory_usage

# Create Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize CORS
CORS(app)

# Initialize conversation database
conversation_db = ConversationDB()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,  # change to WARNING in production if too verbose
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize tools
search_tool = ProductSearchTool()


# ---------- Routes ---------- #

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


@app.route("/", methods=["GET"])
def index():
    return render_template("demo.html")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        redis_memory.redis_client.ping()
        pinecone_status = "connected" if search_tool.is_available else "disconnected"
        return jsonify({
            "status": "healthy",
            "service": "Lotus Electronics Chatbot",
            "redis": "connected",
            "search_methods": {"pinecone_vector": pinecone_status},
            "active_users": len(redis_memory.get_active_users())
        })
    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    with MemoryTracker("chat_request"):
        # Log initial memory usage
        log_memory_usage("chat endpoint start")
        
        payload = request.get_json(force=True)
        message = payload.get("message")
        session_id = payload.get("session_id", "default_session")

        if not message:
            return jsonify({"error": "Missing 'message' in request"}), 400

        try:
            # Check memory before processing
            check_memory_limit(limit_mb=700)  # 700MB limit
            
            # Store the human message in conversation database
            conversation_db.store_conversation(
                session_id=session_id,
                message_type="human",
                message_content=message
            )
            
            log_memory_usage("after storing message")
            
            ai_reply = chat_with_agent(message, session_id)
            data = json.loads(ai_reply)
            
            # Store the AI response in conversation database
            conversation_db.store_conversation(
                session_id=session_id,
                message_type="ai",
                message_content=data.get("answer", ""),
                response_metadata=data
            )
            
            log_memory_usage("after processing complete")
            return jsonify({"status": "success", "data": data})
            
        except json.JSONDecodeError as e:
            # Log the actual error for debugging
            logger.error(f"JSON decode error: {e}")
            conversation_db.store_log("ERROR", "chat_endpoint", f"JSON decode error: {e}", session_id)
            
            # Return user-friendly message
            user_friendly_response = {
                "status": "success",
                "data": {
                    "answer": "Can you ask me again later? I'm being asked too many queries right now by users which is more than usual, so I can't do that for you right now. Please wait for some time and ask again.",
                    "products": [],
                    "product_details": {},
                    "stores": [],
                    "policy_info": {},
                    "comparison": {},
                    "end": "Please try again in a few minutes."
                }
            }
            return jsonify(user_friendly_response), 200
            
        except Exception as e:
            # Log the actual error for debugging
            logger.exception("Error in chat_with_agent")
            conversation_db.store_log("ERROR", "chat_endpoint", f"Error in chat_with_agent: {str(e)}", session_id)
            
            # Return user-friendly message
            user_friendly_response = {
                "status": "success",
                "data": {
                    "answer": "Can you ask me again later? I'm being asked too many queries right now by users which is more than usual, so I can't do that for you right now. Please wait for some time and ask again.",
                    "products": [],
                    "product_details": {},
                    "stores": [],
                    "policy_info": {},
                    "comparison": {},
                    "end": "Please try again in a few minutes."
                }
            }
            return jsonify(user_friendly_response), 200


# ---------- Admin Routes ---------- #

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")
    
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password required"}), 400
        
        admin = conversation_db.verify_admin(username, password)
        if admin:
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            return jsonify({"success": True, "message": "Login successful"})
        else:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401
    
    except Exception as e:
        logger.exception("Error in admin login")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    return render_template("admin_dashboard.html")

# ---------- Admin API Routes ---------- #

def admin_required(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/admin/api/stats")
@admin_required
def admin_stats():
    try:
        stats = conversation_db.get_conversation_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.exception("Error getting admin stats")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/conversations")
@admin_required
def admin_conversations():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        session_id = request.args.get('session_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        offset = (page - 1) * limit
        conversations = conversation_db.get_conversations(
            limit=limit, 
            offset=offset, 
            session_id=session_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get total count for pagination
        total_count = conversation_db.get_conversation_count(
            session_id=session_id,
            start_date=start_date,
            end_date=end_date
        )
        
        total_pages = (total_count + limit - 1) // limit
        
        pagination = {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        return jsonify({
            "success": True,
            "conversations": conversations,
            "pagination": pagination
        })
    except Exception as e:
        logger.exception("Error getting conversations")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/users")
@admin_required
def admin_users():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        users = conversation_db.get_unique_users(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            "success": True,
            "users": users
        })
    except Exception as e:
        logger.exception("Error getting users")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/users/<session_id>/conversation")
@admin_required
def admin_user_conversation(session_id):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conversation_thread = conversation_db.get_conversation_thread(
            session_id=session_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "conversation": conversation_thread
        })
    except Exception as e:
        logger.exception("Error getting user conversation")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/conversations/<int:conversation_id>")
@admin_required
def admin_conversation_detail(conversation_id):
    try:
        import sqlite3
        conn = sqlite3.connect(conversation_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [description[0] for description in cursor.description]
            conversation = dict(zip(columns, row))
            conn.close()
            return jsonify({"success": True, "conversation": conversation})
        else:
            conn.close()
            return jsonify({"success": False, "message": "Conversation not found"}), 404
    except Exception as e:
        logger.exception("Error getting conversation detail")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/logs")
@admin_required
def admin_logs():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        level = request.args.get('level')
        
        offset = (page - 1) * limit
        logs = conversation_db.get_logs(limit, offset, level)
        
        # Get total count for pagination
        import sqlite3
        conn = sqlite3.connect(conversation_db.db_path)
        cursor = conn.cursor()
        
        if level:
            cursor.execute('SELECT COUNT(*) FROM system_logs WHERE level = ?', (level,))
        else:
            cursor.execute('SELECT COUNT(*) FROM system_logs')
        
        total_count = cursor.fetchone()[0]
        conn.close()
        
        total_pages = (total_count + limit - 1) // limit
        
        pagination = {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        return jsonify({
            "success": True,
            "logs": logs,
            "pagination": pagination
        })
    except Exception as e:
        logger.exception("Error getting logs")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/logs/<int:log_id>")
@admin_required
def admin_log_detail(log_id):
    try:
        import sqlite3
        conn = sqlite3.connect(conversation_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM system_logs WHERE id = ?', (log_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [description[0] for description in cursor.description]
            log = dict(zip(columns, row))
            conn.close()
            return jsonify({"success": True, "log": log})
        else:
            conn.close()
            return jsonify({"success": False, "message": "Log not found"}), 404
    except Exception as e:
        logger.exception("Error getting log detail")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/export/conversations")
@admin_required
def admin_export_conversations():
    try:
        session_id = request.args.get('session_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conversations = conversation_db.get_conversations(
            limit=10000, 
            session_id=session_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Session ID', 'Type', 'Message', 'Phone', 'Timestamp'])
        
        # Write data
        for conv in conversations:
            writer.writerow([
                conv['id'],
                conv['session_id'],
                conv['message_type'],
                conv['message_content'],
                conv['user_phone'] or '',
                conv['timestamp']
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        
        # Generate filename with filters
        filename_parts = ['conversations']
        if session_id:
            filename_parts.append(f'user_{session_id[:8]}')
        if start_date:
            filename_parts.append(f'from_{start_date}')
        if end_date:
            filename_parts.append(f'to_{end_date}')
        filename_parts.append(datetime.now().strftime("%Y%m%d"))
        
        filename = '_'.join(filename_parts) + '.csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
    except Exception as e:
        logger.exception("Error exporting conversations")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/api/export/logs")
@admin_required
def admin_export_logs():
    try:
        level = request.args.get('level')
        logs = conversation_db.get_logs(limit=10000, level=level)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Level', 'Logger', 'Message', 'Session ID', 'Timestamp'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log['id'],
                log['level'],
                log['logger_name'],
                log['message'],
                log['session_id'] or '',
                log['timestamp']
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=logs_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
    except Exception as e:
        logger.exception("Error exporting logs")
        return jsonify({"success": False, "message": str(e)}), 500


# ---------- Entrypoint ---------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=True)

# from werkzeug.middleware.dispatcher import DispatcherMiddleware
# from werkzeug.serving import run_simple

# # Mount the Flask app under /chatbot
# application = DispatcherMiddleware(
#     # Root app if you want something at / (can be None)
#     None,
#     {
#         '/chatbot': app
#     }
# )

# if __name__ == "__main__":
#     # Optional local server for testing
#     run_simple('0.0.0.0', 8001, application, use_reloader=True, use_debugger=True)



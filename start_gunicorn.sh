#!/bin/bash
# Gunicorn startup script for Lotus Electronics Chatbot API (Production)

echo "🚀 Starting Lotus Electronics Chatbot API with Gunicorn..."

# Create logs directory if it doesn't exist
mkdir -p logs


source /root/yes/bin/activate

conda activate chatbot


# Run with Gunicorn for production (WSGI for Flask) with SSL
# Optimized for 100 concurrent users with memory management
nohup gunicorn -w 3 -b 0.0.0.0:8001 \
  --worker-class gevent \
  --worker-connections 50 \
  --timeout 120 \
  --max-requests 500 \
  --max-requests-jitter 50 \
  --preload \
  --worker-tmp-dir /dev/shm \
  --keyfile=/etc/ssl/private/server.lotuselectronics.com.key \
  --certfile=/etc/ssl/certs/server.lotuselectronics.com.crt \
  --access-logfile=logs/access.log \
  --error-logfile=logs/error.log \
  app2:app > gunicorn.log 2>&1 &

# Check if server started successfully
sleep 2
if pgrep -f "gunicorn.*app2:app" > /dev/null; then
    echo "✅ Production server started successfully!"
    echo "📍 Server running at: https://0.0.0.0:8001"
    echo "📊 Workers: 3 (gevent async)"
    echo "👥 Capacity: ~150 concurrent users"
    echo "📝 Access logs: logs/access.log"
    echo "📝 Error logs: logs/error.log"
    echo "🔍 Process ID: $(pgrep -f 'gunicorn.*app2:app' | head -1)"
else
    echo "❌ Failed to start server!"
    echo "📝 Check error logs: tail -f logs/error.log"
    exit 1
fi

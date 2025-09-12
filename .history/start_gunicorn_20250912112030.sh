#!/bin/bash
# Gunicorn startup script for Lotus Electronics Chatbot API (Production)

echo "🚀 Starting Lotus Electronics Chatbot API with Gunicorn..."

# Create logs directory if it doesn't exist
mkdir -p logs


source /root/yes/bin/activate

conda activate chatbot


# Run with Gunicorn for production (WSGI for Flask)
nohup gunicorn -w 4 -b 0.0.0.0:8001 \
  --keyfile=/etc/ssl/private/server.lotuselectronics.com.key \
  --certfile=/etc/ssl/certs/server.lotuselectronics.com.crt \
  app2:app  > gunicorn.log 2>&1 &

# Check if server started successfully
sleep 2
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✅ Production server started successfully!"
    echo "📍 Server running at: http://0.0.0.0:8001"
    echo "📊 Workers: $WORKERS"
    echo "📝 Access logs: logs/access.log"
    echo "📝 Error logs: logs/error.log"
    echo "🔍 Process ID: $(pgrep -f 'gunicorn.*app:app' | head -1)"
else
    echo "❌ Failed to start server!"
    echo "📝 Check error logs: tail -f logs/error.log"
    exit 1
fi

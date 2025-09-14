#!/bin/bash
# Install memory monitoring dependencies

echo "📦 Installing memory monitoring dependencies..."

# Install psutil for memory monitoring
pip install psutil

echo "✅ Dependencies installed successfully!"
echo ""
echo "🔧 Memory optimization changes made:"
echo "  • Reduced Gunicorn workers from 4 to 1"
echo "  • Added memory monitoring to chat endpoint"
echo "  • Added automatic garbage collection"
echo "  • Set memory limits and warnings"
echo ""
echo "🚀 Restart your server to apply changes:"
echo "  ./stop_gunicorn.sh && ./start_gunicorn.sh"
#!/bin/bash
# Memory monitoring script for Lotus Electronics Chatbot

echo "🔍 Memory Usage Monitor for Lotus Electronics Chatbot"
echo "================================================="

# Check total system memory
echo "💾 System Memory:"
free -h

echo ""
echo "📊 Process Memory Usage:"

# Check gunicorn processes
echo "🚀 Gunicorn Processes:"
ps aux | grep gunicorn | grep -v grep | awk '{print $2, $4"% CPU", $6/1024"MB", $11}' | column -t

echo ""
echo "🐍 Python Processes:"
ps aux | grep python | grep -v grep | awk '{print $2, $4"% CPU", $6/1024"MB", $11}' | column -t

echo ""
echo "⚡ Top Memory Consuming Processes:"
ps aux --sort=-%mem | head -10 | awk '{print $2, $3"% CPU", $4"% MEM", $6/1024"MB", $11}' | column -t

echo ""
echo "📈 Memory Statistics:"
echo "Total Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Used Memory: $(free -h | awk '/^Mem:/ {print $3}')"
echo "Available Memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo "Memory Usage: $(free | awk '/^Mem:/ {printf "%.1f%%", $3/$2 * 100.0}')"

echo ""
echo "🔄 To monitor continuously: watch -n 5 ./monitor_memory.sh"
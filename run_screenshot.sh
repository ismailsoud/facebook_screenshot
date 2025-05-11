#!/bin/sh
# Script to manually trigger the screenshot process

echo "Running Facebook screenshot process..."
python /app/facebook_screenshot.py "$@"
echo "Screenshot process complete. Check /app/screenshots directory for results." 
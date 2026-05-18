#!/bin/bash
# Final cleanup before GitHub push

echo "🧹 Cleaning up for GitHub..."

# Remove any sensitive or temporary files
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf *.pyc
rm -rf temp/
rm -rf logs/
rm -rf data/*.db

# Ensure all new files are tracked
git add .

# Check what will be committed
echo ""
echo "📋 Files to be committed:"
git status

echo ""
echo "💾 Ready to commit and push to GitHub"

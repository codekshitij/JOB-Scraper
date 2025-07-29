#!/bin/bash
# Activate the virtual environment for the job scraper

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "🐍 Python: $(which python)"
echo "📦 Packages available in: $(python -c 'import sys; print(sys.path[-1])')"

echo ""
echo "🚀 You can now run:"
echo "   python scraper.py --test-company Microsoft"
echo "   python selector_finder.py https://careers.company.com"
echo "   python test_single_company.py Microsoft"
echo ""
echo "💡 To deactivate, run: deactivate" 
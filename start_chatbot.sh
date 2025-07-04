#!/bin/bash
# Startup script for the chatbot project

echo "📦 Checking dependencies..."
if ! command -v pip &> /dev/null; then
    echo "❌ pip is not installed. Please install Python and pip first."
    exit 1
fi

# Check if requirements are installed
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo "🔑 Creating .env file. Please add your OpenAI API key."
    cp example.env .env
    echo "⚠️ Please edit .env and add your OpenAI API key before continuing."
    exit 1
fi

# Check if spaCy model is installed
echo "🧠 Installing spaCy language model..."
python -m spacy download en_core_web_sm

# Check if data directory has content
if [ -z "$(ls -A data 2>/dev/null)" ]; then
    echo "📄 Data directory is empty. Using sample content..."
else
    echo "📄 Using existing content in data directory..."
fi

# Build indexes
echo "🔍 Building semantic index..."
python src/build_index.py

echo "🕸️ Building knowledge graph..."
python src/build_knowledge_graph.py

# Launch options
echo ""
echo "🚀 Setup complete! Choose how to start the chatbot:"
echo ""
echo "1) Web Interface (recommended)"
echo "2) CLI Interface"
echo "3) Analytics Dashboard"
echo "4) Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🌐 Starting web interface..."
        streamlit run src/app.py
        ;;
    2)
        echo "💻 Starting CLI interface..."
        python src/main.py --use-graph
        ;;
    3)
        echo "📊 Starting analytics dashboard..."
        streamlit run src/dashboard.py
        ;;
    4)
        echo "👋 Exiting. Run 'streamlit run src/app.py' to start the web interface later."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Run 'streamlit run src/app.py' to start the web interface."
        exit 1
        ;;
esac

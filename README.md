# Intelligent Chatbot with RAG and Knowledge Graph

This project implements a comprehensive chatbot that can answer questions based on website content using Retrieval-Augmented Generation (RAG) with semantic search and a knowledge graph.

## Features

### Phase 1: Semantic Search ✅
- Content indexing and chunking with LlamaIndex
- Vector embeddings stored in ChromaDB
- Semantic search to find relevant content chunks
- Google Gemini Pro for natural language responses

### Phase 2: Knowledge Graph ✅
- Entity extraction from content
- Relationship identification between entities
- Neo4j integration (optional)
- Hybrid query routing based on question type
- Knowledge graph visualizations

### Phase 3: Advanced Features ✅
- Streamlit web interface
- User feedback collection and ratings
- Analytics dashboard
- Automatic content updates from websites
- Performance monitoring

## Setup

1. Clone this repository
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example.env file to .env and add your Google Gemini API key:
   ```bash
   cp example.env .env
   ```
   Then edit the .env file with your actual Gemini API key

4. Install the spaCy language model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Quick Start

1. Add your content files to the `data/` directory or configure `content_sources.json` for automatic updates
2. Build the semantic index:
   ```bash
   python src/build_index.py
   ```
3. Build the knowledge graph:
   ```bash
   python src/build_knowledge_graph.py
   ```
4. Run the web interface:
   ```bash
   streamlit run src/app.py
   ```

## Command-Line Interface

Run the chatbot in the terminal:
```bash
# Basic semantic search
python src/main.py

# With knowledge graph
python src/main.py --use-graph
```

## Web Interface

The project includes two web interfaces:

### Chatbot Interface
```bash
streamlit run src/app.py
```

### Analytics Dashboard
```bash
streamlit run src/dashboard.py
```

## Content Management

### Manual Content Addition
1. Add markdown/text files to the `data/` directory
2. Rebuild indexes:
   ```bash
   python src/build_index.py
   python src/build_knowledge_graph.py
   ```

### Automatic Content Updates
1. Configure websites in `content_sources.json`:
   ```json
   {
     "websites": [
       {
         "name": "docs",
         "base_url": "https://your-website.com",
         "paths": ["/", "/about", "/faq"],
         "css_selector": "main",
         "max_pages": 20,
         "follow_links": true
       }
     ],
     "update_frequency_hours": 24
   }
   ```

2. Run the content updater:
   ```bash
   # Run once
   python src/auto_update_content.py --rebuild

   # Run as daemon that periodically checks for updates
   python src/auto_update_content.py --daemon --rebuild
   ```

## Neo4j Integration (Optional)

For a persistent knowledge graph with advanced query capabilities:

1. Install Neo4j Desktop or use Neo4j AuraDB (cloud)
2. Create a database and set credentials in `.env`:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

## Project Structure
- `data/` - Your website content
- `src/` - Source code
  - `models/` - Data models
  - `utils/` - Utility functions
  - `services/` - Core services like indexing, search, etc.
  - `app.py` - Streamlit web interface
  - `dashboard.py` - Analytics dashboard
  - `main.py` - CLI interface
  - `build_index.py` - Index builder
  - `build_knowledge_graph.py` - Knowledge graph builder
  - `auto_update_content.py` - Content updater
- `chroma_db/` - Vector database storage
- `visualizations/` - Knowledge graph visualizations
- `feedback/` - User feedback storage

## Advanced Configuration

The system can be configured through:

1. Environment variables in `.env`
2. Website sources in `content_sources.json`
3. Configuration parameters in `src/utils/config.py`

## Google Colab Support

This project can be run in Google Colab for easy use without setting up a local environment.

### Running in Colab

1. Open the `colab_notebook.ipynb` in Google Colab
2. Follow the step-by-step instructions in the notebook
3. Use the Streamlit interface directly in Colab

The notebook will:
- Install all required dependencies
- Set up your Gemini API key
- Create a data directory for your content
- Build the vector index
- Run a Streamlit interface using ngrok (optional)

Special Colab files:
- `colab_notebook.ipynb` - Main notebook with step-by-step instructions
- `colab_chatbot.py` - Simplified chatbot implementation for Colab
- `colab_chatbot_flexible.py` - Version-flexible implementation that handles different LlamaIndex import structures
- `colab_streamlit_app.py` - Streamlit interface for Colab

## Performance Optimization

For better performance:
- Use more descriptive content
- Break large documents into smaller files
- Use a local vector database for faster queries
- Customize chunk size and overlap in `config.py`

See [GETTING_STARTED.md](./GETTING_STARTED.md) for detailed instructions.

## License

This project is available for use under the MIT License.

# Getting Started

## Phase 1: Basic Chatbot Setup (COMPLETED ✅)

1. Install the dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
```bash
cp example.env .env
```

3. Edit the `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. Build the semantic index:
```bash
python src/build_index.py
```

5. Run the chatbot CLI:
```bash
python src/main.py
```

6. Or run the web interface:
```bash
streamlit run src/app.py
```

## Phase 2: Knowledge Graph (COMPLETED ✅)

1. Install spaCy language model (if not installed already):
```bash
python -m spacy download en_core_web_sm
```

2. Build the knowledge graph:
```bash
python src/build_knowledge_graph.py
```

3. Run the chatbot with knowledge graph enabled:
```bash
python src/main.py --use-graph
```

4. Or run the web interface and enable the knowledge graph in settings:
```bash
streamlit run src/app.py
```

### Neo4j Integration (Optional)

The knowledge graph can optionally use Neo4j for storage. To use Neo4j:

1. Install Neo4j Desktop or use Neo4j AuraDB (cloud service)
2. Create a new database and set the password
3. Update the `.env` file with your Neo4j credentials:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

## Phase 3: Polish and Expand (COMPLETED ✅)

### Feedback Collection and Analytics

1. User feedback is collected in the web interface
2. Run the analytics dashboard to view user feedback and statistics:
```bash
streamlit run src/dashboard.py
```

### Automatic Content Updates

1. Configure websites to monitor in `content_sources.json`
2. Run the content updater once:
```bash
python src/auto_update_content.py --rebuild
```

3. Or run as a daemon that periodically checks for updates:
```bash
python src/auto_update_content.py --daemon --rebuild
```

## Add Your Own Content

To add your own content manually:

1. Place your content files in the `data/` directory
2. Rebuild the semantic index:
```bash
python src/build_index.py
```
3. Rebuild the knowledge graph (if using):
```bash
python src/build_knowledge_graph.py
```

To automatically fetch content from websites:

1. Edit `content_sources.json` with your website URLs
2. Run the content updater:
```bash
python src/auto_update_content.py --rebuild
```

## Next Steps

1. Test the chatbot with your own content
2. Compare results with and without the knowledge graph
3. Collect user feedback to improve the system
4. Set up automatic content updates for your websites
5. Monitor performance using the analytics dashboard

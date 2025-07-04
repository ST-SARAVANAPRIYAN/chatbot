# Sample FAQ

## General Questions

### What is this chatbot?
This is a sample chatbot that uses semantic search and optionally a knowledge graph to answer questions about your content.

### How does it work?
The chatbot uses LlamaIndex to create embeddings of your content and stores them in a vector database. When you ask a question, it finds the most relevant chunks of text and sends them to the LLM along with your question.

## Technical Questions

### What technologies are used?
- LlamaIndex for semantic indexing
- ChromaDB as the vector database
- OpenAI API for embeddings and LLM capabilities
- Streamlit for the web interface

### How do I add more content?
Simply add more text files to the data directory and rebuild the index using `python src/build_index.py`.

## Usage Questions

### Can I deploy this chatbot to production?
Yes, you can deploy this chatbot to production. You may want to add authentication, monitoring, and other features first.

### Is the knowledge graph necessary?
No, the knowledge graph (Phase 2) is optional but can improve answers for fact-based questions.

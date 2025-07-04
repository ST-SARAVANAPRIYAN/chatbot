#!/usr/bin/env python3
"""
Streamlit web interface for the chatbot - Google Colab version
"""
import streamlit as st
import logging
import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Directory paths
DATA_DIR = "./data"
CHROMA_DB_DIRECTORY = "./chroma_db"

class GeminiChatbot:
    def __init__(self):
        # Get Gemini API key
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("GEMINI_API_KEY not found in environment. Please set it first.")
            self.api_key = st.text_input("Enter your Gemini API key:", type="password")
            if not self.api_key:
                st.error("Gemini API key is required to continue.")
                st.stop()
            os.environ["GEMINI_API_KEY"] = self.api_key
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.index = None
        
    def load_documents(self):
        """Load documents from the data directory"""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            st.info(f"Created data directory at {DATA_DIR}")
        
        if not os.listdir(DATA_DIR):
            st.warning("Data directory is empty. Please add some documents.")
            return False
            
        return True
        
    def build_index(self):
        """Build vector index from documents"""
        try:
            # Dynamic imports to handle different versions of llama-index
            try:
                # Try importing from llama_index (newer versions)
                from llama_index import VectorStoreIndex, SimpleDirectoryReader, StorageContext
                from llama_index.node_parser import SentenceSplitter
                from llama_index.vector_stores.chroma import ChromaVectorStore
                st.info("Using llama_index package")
            except ImportError:
                # Try importing from llama_index.core (older or different versions)
                from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
                from llama_index.core.node_parser import SentenceSplitter
                try:
                    from llama_index.core.vector_stores.chroma import ChromaVectorStore
                    st.info("Using llama_index.core package")
                except ImportError:
                    from llama_index.vector_stores.chroma import ChromaVectorStore
                    st.info("Using mixed llama_index imports")
            
            # Load documents
            documents = SimpleDirectoryReader(DATA_DIR).load_data()
            
            # Create sentence splitter for text chunking
            text_splitter = SentenceSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # Set up Chroma client
            if not os.path.exists(CHROMA_DB_DIRECTORY):
                os.makedirs(CHROMA_DB_DIRECTORY)
                
            chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIRECTORY)
            chroma_collection = chroma_client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Build index with error handling for different parameter names
            try:
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    transformations=[text_splitter],
                )
            except TypeError:
                # Try alternative approach if transformations parameter doesn't work
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    node_parser=text_splitter,
                )
            
            st.success("Index built successfully!")
            return True
        except Exception as e:
            st.error(f"Error building index: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def query(self, query_text):
        """Query the index with a natural language query"""
        if not self.index:
            st.error("Index not built yet. Please build the index first.")
            return {
                "answer": "Index not built yet. Please build the index first.",
                "sources": []
            }
            
        try:
            # Create query engine
            query_engine = self.index.as_query_engine()
            
            # Execute query
            response = query_engine.query(query_text)
            
            # Extract source information
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source = {
                        "text": node.node.get_content(),
                        "metadata": node.node.metadata,
                        "score": node.score if hasattr(node, 'score') else None
                    }
                    sources.append(source)
            
            return {
                "answer": str(response),
                "sources": sources
            }
        except Exception as e:
            st.error(f"Error during query: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "answer": f"Error during query: {str(e)}",
                "sources": []
            }

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None

def main():
    # Set page config
    st.set_page_config(
        page_title="Gemini Chatbot for Google Colab",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Main title
    st.title("🤖 Gemini Chatbot for Google Colab")
    
    # Sidebar
    with st.sidebar:
        st.title("Chatbot Settings")
        
        # Initialize chatbot if not already done
        if st.session_state.chatbot is None:
            st.session_state.chatbot = GeminiChatbot()
        
        # Check data directory status
        data_dir_status = "✅ Available" if os.path.exists(DATA_DIR) and os.listdir(DATA_DIR) else "❌ Empty"
        st.info(f"Data Directory: {data_dir_status}")
        
        # Check index status
        index_status = "✅ Available" if os.path.exists(CHROMA_DB_DIRECTORY) else "❌ Not Built"
        st.info(f"Vector Index: {index_status}")
        
        # Upload documents
        with st.expander("Upload Documents"):
            uploaded_file = st.file_uploader("Upload a document", type=["txt", "md", "pdf"])
            if uploaded_file is not None:
                if not os.path.exists(DATA_DIR):
                    os.makedirs(DATA_DIR)
                
                file_path = os.path.join(DATA_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                st.success(f"File '{uploaded_file.name}' uploaded successfully")
        
        # Build index button
        if st.button("Build/Rebuild Vector Index"):
            if st.session_state.chatbot.load_documents():
                with st.spinner("Building vector index..."):
                    if st.session_state.chatbot.build_index():
                        st.success("Vector index built successfully!")
                    else:
                        st.error("Failed to build vector index.")
            else:
                st.error("No documents found. Please upload some documents first.")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message["role"] == "assistant" and "sources" in message and message["sources"]:
                with st.expander("View Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        source_name = source.get('metadata', {}).get('source', f"Source {i}")
                        st.markdown(f"**Document: {source_name}**")
                        text = source.get('text', '')
                        if text:
                            st.text(text[:200] + "..." if len(text) > 200 else text)
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check if index is built
        if not st.session_state.chatbot.index:
            if not os.path.exists(CHROMA_DB_DIRECTORY) or not os.listdir(CHROMA_DB_DIRECTORY):
                # Need to build index first
                if st.session_state.chatbot.load_documents():
                    with st.spinner("Building index for the first time..."):
                        st.session_state.chatbot.build_index()
                else:
                    st.error("No documents found. Please upload some documents first.")
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "I need some documents to learn from. Please upload documents using the sidebar.",
                        "sources": []
                    })
                    st.stop()
            else:
                # Index exists but not loaded
                with st.spinner("Loading existing index..."):
                    st.session_state.chatbot.build_index()
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Thinking..."):
                response = st.session_state.chatbot.query(prompt)
                message_placeholder.markdown(response["answer"])
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response["answer"],
                    "sources": response["sources"]
                })
                
                # Show sources if available
                if response["sources"]:
                    with st.expander("View Sources"):
                        for i, source in enumerate(response["sources"], 1):
                            source_name = source.get('metadata', {}).get('source', f"Source {i}")
                            st.markdown(f"**Document: {source_name}**")
                            text = source.get('text', '')
                            if text:
                                st.text(text[:200] + "..." if len(text) > 200 else text)

if __name__ == "__main__":
    main()

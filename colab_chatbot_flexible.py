import os
import sys
import logging
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
            self.api_key = input("Enter your Gemini API key: ")
            os.environ["GEMINI_API_KEY"] = self.api_key
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.index = None
        
    def load_documents(self):
        """Load documents from the data directory"""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"Created data directory at {DATA_DIR}")
        
        if not os.listdir(DATA_DIR):
            print("Data directory is empty. Please add some documents.")
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
                print("Using llama_index package")
            except ImportError:
                # Try importing from llama_index.core (older or different versions)
                from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
                from llama_index.core.node_parser import SentenceSplitter
                try:
                    from llama_index.core.vector_stores.chroma import ChromaVectorStore
                    print("Using llama_index.core package")
                except ImportError:
                    from llama_index.vector_stores.chroma import ChromaVectorStore
                    print("Using mixed llama_index imports")
            
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
            
            # Build index
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
            
            print("Index built successfully!")
            return True
        except Exception as e:
            print(f"Error building index: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def query(self, query_text):
        """Query the index with a natural language query"""
        if not self.index:
            print("Index not built yet. Please build the index first.")
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
            print(f"Error during query: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "answer": f"Error during query: {str(e)}",
                "sources": []
            }
    
    def chat_interface(self):
        """Simple chat interface for testing"""
        print("\n===== Gemini Chatbot =====")
        print("Type 'exit' to quit")
        print("========================\n")
        
        while True:
            query = input("\nYou: ")
            if query.lower() in ['exit', 'quit', 'q']:
                break
                
            response = self.query(query)
            print(f"\nBot: {response['answer']}")
            
            # Print sources
            if response['sources']:
                print("\nSources:")
                for i, source in enumerate(response['sources'][:2], 1):
                    source_name = source.get('metadata', {}).get('source', f"Source {i}")
                    print(f"- {source_name}")

if __name__ == "__main__":
    print("Initializing chatbot...")
    chatbot = GeminiChatbot()
    
    print("Loading documents...")
    if chatbot.load_documents():
        print("Building index...")
        if chatbot.build_index():
            print("Ready to chat!")
            chatbot.chat_interface()

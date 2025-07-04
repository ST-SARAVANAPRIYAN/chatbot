import os
import sys
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
import importlib
import traceback

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
        
        # Import tracker
        self.import_status = {
            "VectorStoreIndex": None,
            "SimpleDirectoryReader": None,
            "StorageContext": None,
            "SentenceSplitter": None,
            "ChromaVectorStore": None
        }
        
    def load_documents(self):
        """Load documents from the data directory"""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"Created data directory at {DATA_DIR}")
        
        if not os.listdir(DATA_DIR):
            print("Data directory is empty. Please add some documents.")
            # Create sample document for testing
            sample_path = os.path.join(DATA_DIR, "sample_faq.md")
            try:
                with open(sample_path, "w") as f:
                    f.write("# Sample FAQ\n\n")
                    f.write("## What is this chatbot?\n")
                    f.write("This is a RAG-based chatbot using Google Gemini API.\n\n")
                    f.write("## What is RAG?\n")
                    f.write("RAG stands for Retrieval-Augmented Generation, which enhances LLM responses with retrieved information.\n\n")
                    f.write("## How does it work?\n")
                    f.write("It uses vector embeddings to find relevant information and then generates responses based on that information.\n")
                print(f"Created sample FAQ document at {sample_path}")
                return True
            except Exception as e:
                print(f"Error creating sample document: {str(e)}")
                return False
            
        return True
    
    def dynamic_import(self, module_paths, class_name):
        """Dynamically import a class from multiple possible module paths"""
        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    self.import_status[class_name] = module_path
                    return getattr(module, class_name)
            except ImportError:
                continue
        
        print(f"Failed to import {class_name} from any of the provided paths: {module_paths}")
        return None
        
    def build_index(self):
        """Build vector index from documents"""
        try:
            print("Attempting to import LlamaIndex components...")
            
            # Try to import components from multiple possible locations
            VectorStoreIndex = self.dynamic_import([
                "llama_index", 
                "llama_index.core",
                "llama_index.indices.vector_store",
                "llama_index.core.indices.vector_store"
            ], "VectorStoreIndex")
            
            SimpleDirectoryReader = self.dynamic_import([
                "llama_index", 
                "llama_index.core",
                "llama_index.readers",
                "llama_index.core.readers"
            ], "SimpleDirectoryReader")
            
            StorageContext = self.dynamic_import([
                "llama_index", 
                "llama_index.core",
                "llama_index.storage",
                "llama_index.core.storage"
            ], "StorageContext")
            
            SentenceSplitter = self.dynamic_import([
                "llama_index.node_parser",
                "llama_index.core.node_parser",
                "llama_index.text_splitter",
                "llama_index.core.text_splitter"
            ], "SentenceSplitter")
            
            # ChromaVectorStore requires special handling due to its nested location
            chroma_paths = [
                "llama_index.vector_stores.chroma",
                "llama_index.core.vector_stores.chroma",
                "llama_index.storage.vector_stores.chroma",
                "llama_index.core.storage.vector_stores.chroma"
            ]
            
            ChromaVectorStore = None
            for path in chroma_paths:
                try:
                    module = importlib.import_module(path)
                    if hasattr(module, "ChromaVectorStore"):
                        ChromaVectorStore = module.ChromaVectorStore
                        self.import_status["ChromaVectorStore"] = path
                        break
                except ImportError:
                    continue
            
            # Check if we have all required components
            missing_components = [name for name, status in self.import_status.items() if status is None]
            if missing_components:
                print(f"Failed to import required components: {missing_components}")
                
                # Try to install the correct version of llama-index
                print("Attempting to install llama-index...")
                os.system("pip install llama-index==0.9.8")
                print("Please restart the notebook and try again.")
                return False
                
            print("Successfully imported all components:")
            for name, path in self.import_status.items():
                print(f"  - {name}: {path}")
            
            # Load documents
            print("Loading documents...")
            documents = SimpleDirectoryReader(DATA_DIR).load_data()
            
            # Create sentence splitter for text chunking
            print("Creating text splitter...")
            text_splitter = SentenceSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # Set up Chroma client
            print("Setting up Chroma DB...")
            if not os.path.exists(CHROMA_DB_DIRECTORY):
                os.makedirs(CHROMA_DB_DIRECTORY)
                
            chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIRECTORY)
            chroma_collection = chroma_client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Build index with error handling for different parameter names
            print("Building index...")
            try:
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    transformations=[text_splitter],
                )
                print("Index built with transformations parameter")
            except TypeError:
                try:
                    # Try alternative approach if transformations parameter doesn't work
                    self.index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=storage_context,
                        node_parser=text_splitter,
                    )
                    print("Index built with node_parser parameter")
                except TypeError:
                    # Last resort, try without specifying the parser
                    self.index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=storage_context,
                    )
                    print("Index built without parser parameter")
            
            print("Index built successfully!")
            return True
        except Exception as e:
            print(f"Error building index: {str(e)}")
            print("Detailed error:")
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

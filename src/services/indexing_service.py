from typing import List, Optional
import os
import logging

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    ServiceContext,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from src.utils.config import Config
from src.utils.data_loader import load_documents_from_directory

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self):
        self.embed_model = OpenAIEmbedding()
        self.index = None
        
    def build_index(self, documents_dir: str = Config.DATA_DIR) -> VectorStoreIndex:
        """
        Build a vector index from documents in a directory
        
        Args:
            documents_dir: Directory containing documents
            
        Returns:
            VectorStoreIndex: The built index
        """
        # Load documents
        documents = load_documents_from_directory(documents_dir)
        
        if not documents:
            logger.error(f"No documents found in {documents_dir}")
            return None
            
        # Create sentence splitter for text chunking
        text_splitter = SentenceSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        
        # Set up Chroma client
        chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_DIRECTORY)
        chroma_collection = chroma_client.get_or_create_collection("documents")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Create service context
        service_context = ServiceContext.from_defaults(
            embed_model=self.embed_model,
            node_parser=text_splitter
        )
        
        # Build index
        logger.info("Building index...")
        self.index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            service_context=service_context
        )
        
        logger.info("Index built successfully")
        return self.index
        
    def load_index(self) -> Optional[VectorStoreIndex]:
        """
        Load an existing index from storage
        
        Returns:
            VectorStoreIndex or None if not found
        """
        if not os.path.exists(Config.CHROMA_DB_DIRECTORY):
            logger.warning(f"No index found at {Config.CHROMA_DB_DIRECTORY}")
            return None
            
        try:
            # Set up Chroma client
            chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_DIRECTORY)
            chroma_collection = chroma_client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Load index
            self.index = load_index_from_storage(storage_context)
            logger.info("Index loaded successfully")
            return self.index
        except Exception as e:
            logger.error(f"Failed to load index: {str(e)}")
            return None
            
    def get_or_create_index(self) -> VectorStoreIndex:
        """
        Get an existing index or create a new one if it doesn't exist
        
        Returns:
            VectorStoreIndex: The loaded or created index
        """
        index = self.load_index()
        if index is None:
            index = self.build_index()
        return index

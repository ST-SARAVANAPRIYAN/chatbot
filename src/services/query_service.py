import logging
from typing import Dict, List, Any, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.openai import OpenAI

from src.utils.config import Config

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self, index: Optional[VectorStoreIndex] = None):
        """
        Initialize the query service
        
        Args:
            index: VectorStoreIndex to query against
        """
        self.index = index
        self.llm = OpenAI(model=Config.DEFAULT_LLM_MODEL, api_key=Config.OPENAI_API_KEY)
        
    def set_index(self, index: VectorStoreIndex):
        """Set the index to query against"""
        self.index = index
        
    def query(self, query_text: str, similarity_top_k: int = 5) -> Dict[str, Any]:
        """
        Query the index with a natural language query
        
        Args:
            query_text: The query text
            similarity_top_k: Number of similar chunks to retrieve
            
        Returns:
            Dict containing response and source nodes
        """
        if not self.index:
            logger.error("No index available for querying")
            return {"answer": "Sorry, the knowledge base is not loaded. Please build the index first.", "sources": []}
        
        try:
            # Create query engine
            query_engine = self.index.as_query_engine(
                similarity_top_k=similarity_top_k,
                response_synthesizer=get_response_synthesizer(
                    response_mode="compact",
                    llm=self.llm,
                )
            )
            
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
            logger.error(f"Error during query: {str(e)}")
            return {
                "answer": f"An error occurred while processing your query: {str(e)}",
                "sources": []
            }

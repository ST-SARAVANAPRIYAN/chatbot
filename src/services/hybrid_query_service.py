import logging
from typing import Dict, List, Any, Optional
import re

from llama_index.core import VectorStoreIndex
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.openai import OpenAI

from src.utils.config import Config
from src.services.query_service import QueryService
from src.services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)

class HybridQueryService:
    """Service that combines semantic search and knowledge graph queries"""
    
    def __init__(self, vector_index: Optional[VectorStoreIndex] = None):
        """
        Initialize the hybrid query service
        
        Args:
            vector_index: VectorStoreIndex to query against
        """
        self.vector_query_service = QueryService(index=vector_index)
        self.kg_service = KnowledgeGraphService()
        self.llm = OpenAI(model=Config.DEFAULT_LLM_MODEL, api_key=Config.OPENAI_API_KEY)
        
    def set_index(self, index: VectorStoreIndex):
        """Set the vector index to query against"""
        self.vector_query_service.set_index(index)
        
    def _is_factual_question(self, query: str) -> bool:
        """
        Determine if a query is likely a factual question
        
        Args:
            query: The query text
            
        Returns:
            bool: True if likely factual, False otherwise
        """
        # Check for question words
        factual_indicators = [
            r'\bwhat\s+is\b', r'\bwho\s+is\b', r'\bwhen\s+is\b', r'\bwhere\s+is\b',
            r'\bhow\s+many\b', r'\bwhich\b', r'\bcan\s+i\b', r'\bdo\s+you\b'
        ]
        
        # Check for specific formats that suggest factual queries
        for pattern in factual_indicators:
            if re.search(pattern, query.lower()):
                return True
                
        return False
        
    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Query both the vector index and knowledge graph
        
        Args:
            query_text: The query text
            
        Returns:
            Dict containing response and source information
        """
        is_factual = self._is_factual_question(query_text)
        
        # For factual questions, try knowledge graph first
        if is_factual:
            logger.info(f"Query appears factual, trying knowledge graph first: {query_text}")
            kg_response = self.kg_service.query_graph(query_text)
            
            # If knowledge graph found facts, use them
            if kg_response["facts"]:
                logger.info("Found facts in knowledge graph")
                
                # Also get vector search results for context
                vector_response = self.vector_query_service.query(query_text)
                
                # Combine results
                combined_response = self._combine_results(query_text, kg_response, vector_response)
                return combined_response
        
        # For non-factual questions or when no facts found, fallback to vector search
        logger.info(f"Using vector search for query: {query_text}")
        return self.vector_query_service.query(query_text)
    
    def _combine_results(self, query: str, kg_response: Dict[str, Any], 
                         vector_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine results from knowledge graph and vector search
        
        Args:
            query: Original query
            kg_response: Response from knowledge graph
            vector_response: Response from vector search
            
        Returns:
            Dict containing combined response
        """
        # Extract facts from knowledge graph
        facts = kg_response.get("facts", [])
        
        # Extract context from vector search
        contexts = []
        for source in vector_response.get("sources", []):
            context = source.get("text", "")
            if context:
                contexts.append(context)
                
        # Create a prompt to combine the information
        facts_text = "\n".join([
            f"- {fact['subject']} {fact['predicate']} {fact['object']}" 
            for fact in facts[:5]  # Limit to top 5 facts
        ])
        
        context_text = "\n".join([
            f"- {context[:200]}..." if len(context) > 200 else f"- {context}"
            for context in contexts[:3]  # Limit to top 3 contexts
        ])
        
        prompt = f"""
        Question: {query}
        
        Knowledge Graph Facts:
        {facts_text}
        
        Additional Context:
        {context_text}
        
        Based on the above knowledge graph facts and additional context, please provide a comprehensive answer to the question.
        """
        
        # Generate combined response using LLM
        try:
            combined_answer = self.llm.complete(prompt).text
        except Exception as e:
            logger.error(f"Error generating combined response: {str(e)}")
            combined_answer = vector_response.get("answer", "Sorry, I couldn't generate a combined answer.")
            
        # Combine sources
        sources = vector_response.get("sources", [])
        
        # Add knowledge graph as a source
        for fact in facts:
            source = {
                "text": fact.get("sentence", ""),
                "metadata": {
                    "source": fact.get("source", "knowledge_graph"),
                    "type": "knowledge_graph",
                    "subject": fact.get("subject", ""),
                    "predicate": fact.get("predicate", ""),
                    "object": fact.get("object", "")
                },
                "score": None
            }
            sources.append(source)
            
        return {
            "answer": combined_answer,
            "sources": sources
        }

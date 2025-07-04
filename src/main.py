#!/usr/bin/env python3
"""
Command-line interface for the chatbot
"""
import argparse
import logging
import sys
import os

from src.utils.config import Config
from src.services.indexing_service import IndexingService
from src.services.query_service import QueryService
from src.services.hybrid_query_service import HybridQueryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Chatbot CLI")
    parser.add_argument("--use-graph", action="store_true",
                        help="Use the knowledge graph for answering questions (Phase 2)")
    args = parser.parse_args()
    
    # Validate config
    if not Config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    print("Loading knowledge base...")
    
    # Load or create the vector index
    indexing_service = IndexingService()
    index = indexing_service.get_or_create_index()
    
    if not index:
        logger.error("Failed to load or create index")
        print("Error: Knowledge base not available. Please run build_index.py first.")
        sys.exit(1)
    
    # Set up the query service based on whether to use the graph
    if args.use_graph:
        print("Using hybrid query service with knowledge graph...")
        query_service = HybridQueryService(vector_index=index)
        
        # Check if knowledge graph has been built
        visualizations_dir = os.path.join(os.getcwd(), "visualizations")
        kg_viz_file = os.path.join(visualizations_dir, "knowledge_graph.png")
        
        if not os.path.exists(kg_viz_file):
            print("Note: Knowledge graph visualization not found. You may want to run build_knowledge_graph.py first.")
    else:
        query_service = QueryService(index=index)
    
    print("\n" + "="*50)
    print("Welcome to the Chatbot!")
    if args.use_graph:
        print("Using both semantic search and knowledge graph for answering questions")
    else:
        print("Using semantic search for answering questions")
    print("Type your questions or 'exit' to quit")
    print("="*50)
    
    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
                
            if not user_input.strip():
                continue
                
            # Process query
            response = query_service.query(user_input)
            
            # Display answer
            print(f"\nBot: {response['answer']}")
            
            # Display sources (optional)
            if response['sources'] and len(response['sources']) > 0:
                print("\nSources:")
                for i, source in enumerate(response['sources'], 1):
                    # Extract source information
                    metadata = source.get('metadata', {})
                    source_name = metadata.get('source', f"Source {i}")
                    source_type = metadata.get('type', 'document')
                    
                    if source_type == 'knowledge_graph':
                        subject = metadata.get('subject', '')
                        predicate = metadata.get('predicate', '')
                        obj = metadata.get('object', '')
                        print(f"- Knowledge Graph: {subject} {predicate} {obj}")
                    else:
                        print(f"- Document: {source_name}")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            logger.exception("Error in chat loop")
            
if __name__ == "__main__":
    main()

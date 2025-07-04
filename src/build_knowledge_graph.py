#!/usr/bin/env python3
"""
Script to build the knowledge graph from documents in the data directory
"""
import argparse
import logging
import sys
import os

from src.utils.config import Config
from src.services.knowledge_graph_service import KnowledgeGraphService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Build the knowledge graph from documents")
    parser.add_argument("--data-dir", type=str, default=Config.DATA_DIR,
                        help=f"Directory containing documents (default: {Config.DATA_DIR})")
    args = parser.parse_args()
    
    # Check if data directory exists
    if not os.path.exists(args.data_dir):
        logger.error(f"Data directory '{args.data_dir}' does not exist")
        sys.exit(1)
        
    # Check if data directory contains files
    if not os.listdir(args.data_dir):
        logger.error(f"Data directory '{args.data_dir}' is empty. Please add documents first.")
        sys.exit(1)
    
    # Validate config
    if not Config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    logger.info(f"Building knowledge graph from documents in {args.data_dir}")
    
    # Build knowledge graph
    kg_service = KnowledgeGraphService()
    success = kg_service.build_graph_from_documents(documents_dir=args.data_dir)
    
    if success:
        logger.info("Knowledge graph built successfully")
        
        # Save visualization if available
        try:
            kg_service._save_graph_visualization()
            logger.info("Graph visualization saved")
        except Exception as e:
            logger.error(f"Failed to save visualization: {str(e)}")
    else:
        logger.error("Failed to build knowledge graph")
        sys.exit(1)
        
if __name__ == "__main__":
    main()

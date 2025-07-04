#!/usr/bin/env python3
"""
Script to build the vector index from documents in the data directory
"""
import argparse
import logging
import sys
import os

from src.utils.config import Config
from src.services.indexing_service import IndexingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Build the vector index from documents")
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
    
    logger.info(f"Building index from documents in {args.data_dir}")
    
    # Build index
    indexing_service = IndexingService()
    index = indexing_service.build_index(documents_dir=args.data_dir)
    
    if index:
        logger.info(f"Index built successfully and stored in {Config.CHROMA_DB_DIRECTORY}")
    else:
        logger.error("Failed to build index")
        sys.exit(1)
        
if __name__ == "__main__":
    main()

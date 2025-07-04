import os
from typing import List, Dict, Any
import logging
from llama_index.core import Document

logger = logging.getLogger(__name__)

def load_documents_from_directory(directory_path: str) -> List[Document]:
    """
    Load documents from a directory of text files
    
    Args:
        directory_path: Path to the directory containing text files
        
    Returns:
        List of Document objects
    """
    documents = []
    
    if not os.path.exists(directory_path):
        logger.warning(f"Directory {directory_path} does not exist.")
        return documents
    
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        # Skip directories and non-text files
        if os.path.isdir(file_path):
            continue
            
        # Check if file is likely a text file
        if not filename.lower().endswith(('.txt', '.md', '.html', '.csv', '.json')):
            logger.info(f"Skipping non-text file: {filename}")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Create metadata
                metadata = {
                    "source": filename,
                    "file_path": file_path,
                    "file_type": os.path.splitext(filename)[1],
                }
                
                # Create document
                document = Document(text=content, metadata=metadata)
                documents.append(document)
                
                logger.info(f"Loaded document: {filename}")
                
        except Exception as e:
            logger.error(f"Error loading file {filename}: {str(e)}")
            
    logger.info(f"Loaded {len(documents)} documents from {directory_path}")
    return documents

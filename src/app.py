#!/usr/bin/env python3
"""
Streamlit web interface for the chatbot
"""
import streamlit as st
import logging
import sys
import os

from src.utils.config import Config
from src.services.indexing_service import IndexingService
from src.services.query_service import QueryService
from src.services.hybrid_query_service import HybridQueryService
from src.services.knowledge_graph_service import KnowledgeGraphService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'query_service' not in st.session_state:
        st.session_state.query_service = None
    if 'use_graph' not in st.session_state:
        st.session_state.use_graph = False

def load_knowledge_base(use_graph=False):
    """
    Load the knowledge base (vector index and optionally knowledge graph)
    
    Args:
        use_graph: Whether to use the knowledge graph
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Load or create the vector index
    indexing_service = IndexingService()
    index = indexing_service.get_or_create_index()
    
    if not index:
        st.error("Failed to load or create index. Please ensure you've built the index using build_index.py")
        return False
    
    # Set up the appropriate query service
    if use_graph:
        st.session_state.query_service = HybridQueryService(vector_index=index)
    else:
        st.session_state.query_service = QueryService(index=index)
        
    return True

def main():
    # Set page config
    st.set_page_config(
        page_title="Chatbot",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.title("Chatbot Settings")
        
        # Option to use knowledge graph (Phase 2)
        use_graph = st.checkbox("Use Knowledge Graph (Phase 2)", value=st.session_state.use_graph)
        if use_graph != st.session_state.use_graph:
            st.session_state.use_graph = use_graph
            # Reload knowledge base with new setting
            with st.spinner("Loading knowledge base..."):
                load_knowledge_base(use_graph=use_graph)
            
        # Check data directory status
        data_dir_status = "✅ Available" if os.path.exists(Config.DATA_DIR) and os.listdir(Config.DATA_DIR) else "❌ Empty"
        st.info(f"Data Directory: {data_dir_status}")
        
        # Check index status
        index_status = "✅ Available" if os.path.exists(Config.CHROMA_DB_DIRECTORY) else "❌ Not Built"
        st.info(f"Vector Index: {index_status}")
        
        # Check knowledge graph status
        visualizations_dir = os.path.join(os.getcwd(), "visualizations")
        kg_viz_file = os.path.join(visualizations_dir, "knowledge_graph.png")
        kg_status = "✅ Available" if os.path.exists(kg_viz_file) else "❌ Not Built"
        st.info(f"Knowledge Graph: {kg_status}")
        
        # Build index button
        if st.button("Build/Rebuild Vector Index"):
            with st.spinner("Building vector index..."):
                try:
                    indexing_service = IndexingService()
                    index = indexing_service.build_index()
                    if index:
                        st.success("Vector index built successfully")
                        # Update the query service with the new index
                        load_knowledge_base(use_graph=st.session_state.use_graph)
                    else:
                        st.error("Failed to build vector index")
                except Exception as e:
                    st.error(f"Error building index: {str(e)}")
                    
        # Build knowledge graph button
        if st.button("Build/Rebuild Knowledge Graph"):
            with st.spinner("Building knowledge graph..."):
                try:
                    kg_service = KnowledgeGraphService()
                    success = kg_service.build_graph_from_documents()
                    if success:
                        st.success("Knowledge graph built successfully")
                        # If using graph, reload the query service
                        if st.session_state.use_graph:
                            load_knowledge_base(use_graph=True)
                            
                        # Show visualization if available
                        viz_path = os.path.join(os.getcwd(), "visualizations", "knowledge_graph.png")
                        if os.path.exists(viz_path):
                            st.image(viz_path, caption="Knowledge Graph Visualization")
                    else:
                        st.error("Failed to build knowledge graph")
                except Exception as e:
                    st.error(f"Error building knowledge graph: {str(e)}")
                    
        # Show knowledge graph visualization if available
        if os.path.exists(kg_viz_file):
            with st.expander("View Knowledge Graph"):
                st.image(kg_viz_file, caption="Knowledge Graph Visualization")
    
    # Main content
    st.title("🤖 Chatbot")
    
    if st.session_state.use_graph:
        st.info("Using hybrid mode: Semantic search + Knowledge graph")
    else:
        st.info("Using semantic search only")
    
    # Load knowledge base if not already loaded
    if st.session_state.query_service is None:
        with st.spinner("Loading knowledge base..."):
            if not load_knowledge_base(use_graph=st.session_state.use_graph):
                st.stop()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("View Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        metadata = source.get('metadata', {})
                        source_type = metadata.get('type', 'document')
                        
                        if source_type == 'knowledge_graph':
                            subject = metadata.get('subject', '')
                            predicate = metadata.get('predicate', '')
                            obj = metadata.get('object', '')
                            st.markdown(f"**Knowledge Graph Fact {i}**")
                            st.markdown(f"_{subject} {predicate} {obj}_")
                        else:
                            source_name = metadata.get('source', f"Source {i}")
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
            st.markdown(prompt)            # Generate and display assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Thinking..."):
                    try:
                        response = st.session_state.query_service.query(prompt)
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
                                    metadata = source.get('metadata', {})
                                    source_type = metadata.get('type', 'document')
                                    
                                    if source_type == 'knowledge_graph':
                                        subject = metadata.get('subject', '')
                                        predicate = metadata.get('predicate', '')
                                        obj = metadata.get('object', '')
                                        st.markdown(f"**Knowledge Graph Fact {i}**")
                                        st.markdown(f"_{subject} {predicate} {obj}_")
                                    else:
                                        source_name = metadata.get('source', f"Source {i}")
                                        st.markdown(f"**Document: {source_name}**")
                                        text = source.get('text', '')
                                        if text:
                                            st.text(text[:200] + "..." if len(text) > 200 else text)
                        
                        # Add feedback UI
                        st.write("Was this response helpful?")
                        feedback_cols = st.columns([1, 1, 1, 1, 1, 3])
                        
                        # Import feedback service if we need to collect feedback
                        from src.services.feedback_service import FeedbackService
                        feedback_service = FeedbackService()
                        
                        # Add rating buttons
                        for i, col in enumerate(feedback_cols[:5], 1):
                            if col.button(f"{i} ⭐", key=f"rating_{i}_{len(st.session_state.messages)}"):
                                # Collect optional comment if rating is low
                                if i <= 3:
                                    comment = st.text_input("What could be improved? (optional)", key=f"comment_{len(st.session_state.messages)}")
                                    if st.button("Submit Feedback", key=f"submit_{len(st.session_state.messages)}"):
                                        feedback_service.save_feedback(prompt, response, i, comment)
                                        st.success("Thank you for your feedback!")
                                else:
                                    # For high ratings, just save without comment
                                    feedback_service.save_feedback(prompt, response, i, None)
                                    st.success("Thank you for your feedback!")
                                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        logger.exception("Error generating response")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Sorry, an error occurred: {str(e)}"
                        })

if __name__ == "__main__":
    main()

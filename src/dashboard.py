#!/usr/bin/env python3
"""
Streamlit dashboard for monitoring chatbot performance and feedback
"""
import streamlit as st
import pandas as pd
import json
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import Counter
import networkx as nx
import altair as alt

from src.services.feedback_service import FeedbackService
from src.utils.config import Config

# Configure page
st.set_page_config(
    page_title="Chatbot Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

def load_feedback_data():
    """Load feedback data from JSONL file"""
    feedback_file = os.path.join(os.getcwd(), "feedback", "feedback.jsonl")
    
    if not os.path.exists(feedback_file):
        st.warning("No feedback data available yet. Use the chatbot to generate feedback.")
        return pd.DataFrame()
        
    # Load data
    data = []
    with open(feedback_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                data.append(entry)
            except json.JSONDecodeError:
                continue
                
    if not data:
        return pd.DataFrame()
        
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    return df

def main():
    st.title("📊 Chatbot Analytics Dashboard")
    
    # Initialize feedback service
    feedback_service = FeedbackService()
    analytics = feedback_service.get_analytics()
    
    # Load feedback data
    df = load_feedback_data()
    
    if df.empty:
        st.info("Start using the chatbot to generate analytics data.")
        st.stop()
    
    # Dashboard layout with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Query Analysis", "Feedback Details", "Knowledge Graph"])
    
    # Tab 1: Overview
    with tab1:
        st.header("Overview")
        
        # Key metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", analytics.get("total_queries", 0))
            
        with col2:
            avg_rating = round(analytics.get("average_rating", 0), 2)
            st.metric("Average Rating", f"{avg_rating} / 5")
            
        with col3:
            if not df.empty and 'rating' in df.columns:
                low_ratings = len(df[df['rating'] <= 2])
                low_rating_pct = round((low_ratings / len(df)) * 100, 1) if len(df) > 0 else 0
                st.metric("Low Ratings", f"{low_ratings} ({low_rating_pct}%)")
            else:
                st.metric("Low Ratings", "0 (0%)")
                
        with col4:
            if not df.empty and 'timestamp' in df.columns:
                today = datetime.now().date()
                queries_today = len(df[df['timestamp'].dt.date == today])
                st.metric("Queries Today", queries_today)
            else:
                st.metric("Queries Today", 0)
        
        # Rating distribution
        st.subheader("Rating Distribution")
        
        rating_dist = analytics.get("rating_distribution", {})
        if rating_dist:
            # Convert to dataframe
            rating_df = pd.DataFrame({
                'Rating': [int(k) for k in rating_dist.keys()],
                'Count': list(rating_dist.values())
            })
            rating_df = rating_df.sort_values('Rating')
            
            # Create bar chart
            chart = alt.Chart(rating_df).mark_bar().encode(
                x=alt.X('Rating:N', sort=None),
                y='Count:Q',
                color=alt.Color('Rating:N', scale=alt.Scale(scheme='blues')),
                tooltip=['Rating', 'Count']
            ).properties(height=300)
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No rating data available yet.")
            
        # Queries over time
        if not df.empty and 'timestamp' in df.columns:
            st.subheader("Queries Over Time")
            
            # Group by day
            df['date'] = df['timestamp'].dt.date
            queries_by_day = df.groupby('date').size().reset_index(name='count')
            
            # Create line chart
            line_chart = alt.Chart(queries_by_day).mark_line().encode(
                x='date:T',
                y='count:Q',
                tooltip=['date', 'count']
            ).properties(height=300)
            
            st.altair_chart(line_chart, use_container_width=True)
            
    # Tab 2: Query Analysis
    with tab2:
        st.header("Query Analysis")
        
        # Common query terms
        st.subheader("Common Query Terms")
        
        common_terms = analytics.get("common_query_terms", {})
        if common_terms:
            # Sort and get top terms
            sorted_terms = sorted(common_terms.items(), key=lambda x: x[1], reverse=True)[:20]
            terms_df = pd.DataFrame(sorted_terms, columns=['Term', 'Frequency'])
            
            # Create horizontal bar chart
            terms_chart = alt.Chart(terms_df).mark_bar().encode(
                y=alt.Y('Term:N', sort='-x'),
                x='Frequency:Q',
                tooltip=['Term', 'Frequency']
            ).properties(height=400)
            
            st.altair_chart(terms_chart, use_container_width=True)
        else:
            st.info("No query term data available yet.")
            
        # Failed queries
        st.subheader("Recent Low-Rated Queries")
        
        failed_queries = feedback_service.get_failed_queries(min_rating=2)
        if failed_queries:
            # Convert to dataframe
            failed_df = pd.DataFrame([
                {
                    "Timestamp": q.get("timestamp", ""),
                    "Query": q.get("query", ""),
                    "Rating": q.get("rating", 0),
                    "Comment": q.get("comment", "")
                } for q in failed_queries
            ])
            
            # Sort by timestamp (recent first)
            if 'Timestamp' in failed_df.columns:
                failed_df['Timestamp'] = pd.to_datetime(failed_df['Timestamp'])
                failed_df = failed_df.sort_values('Timestamp', ascending=False)
                
            # Display as table
            st.dataframe(failed_df, use_container_width=True)
        else:
            st.info("No low-rated queries found.")
            
    # Tab 3: Feedback Details
    with tab3:
        st.header("Feedback Details")
        
        # Show all feedback with filters
        if not df.empty:
            st.subheader("All Feedback")
            
            # Add filters
            col1, col2 = st.columns(2)
            with col1:
                # Date range filter
                if 'timestamp' in df.columns:
                    min_date = df['timestamp'].min().date()
                    max_date = df['timestamp'].max().date()
                    date_range = st.date_input(
                        "Select Date Range",
                        value=(max_date - timedelta(days=7), max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
            
            with col2:
                # Rating filter
                rating_filter = st.multiselect(
                    "Filter by Rating",
                    options=sorted(df['rating'].unique()),
                    default=[]
                )
            
            # Apply filters
            filtered_df = df.copy()
            
            if 'timestamp' in filtered_df.columns and len(date_range) == 2:
                filtered_df = filtered_df[
                    (filtered_df['timestamp'].dt.date >= date_range[0]) & 
                    (filtered_df['timestamp'].dt.date <= date_range[1])
                ]
                
            if rating_filter:
                filtered_df = filtered_df[filtered_df['rating'].isin(rating_filter)]
            
            # Display feedback table
            if not filtered_df.empty:
                # Prepare display columns
                display_df = filtered_df[['timestamp', 'query', 'response', 'rating', 'comment']].copy()
                if 'timestamp' in display_df.columns:
                    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                    
                # Rename columns
                display_df.columns = ['Timestamp', 'Query', 'Response', 'Rating', 'Comment']
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No feedback matches the selected filters.")
                
    # Tab 4: Knowledge Graph
    with tab4:
        st.header("Knowledge Graph Insights")
        
        # Check for knowledge graph visualization
        visualizations_dir = os.path.join(os.getcwd(), "visualizations")
        kg_viz_file = os.path.join(visualizations_dir, "knowledge_graph.png")
        
        if os.path.exists(kg_viz_file):
            st.subheader("Knowledge Graph Visualization")
            st.image(kg_viz_file, caption="Knowledge Graph Visualization")
            
            st.info("""
            This graph shows entities (nodes) and relationships (edges) extracted from your content.
            
            To improve knowledge graph quality:
            - Add more structured content
            - Ensure facts are clearly stated in your documents
            - Run build_knowledge_graph.py after adding new content
            """)
        else:
            st.warning("Knowledge graph visualization not found. Run build_knowledge_graph.py to create it.")
            
        # Knowledge graph status section
        st.subheader("Knowledge Graph Status")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("To build or rebuild the knowledge graph, run:")
            st.code("python src/build_knowledge_graph.py")
            
        with col2:
            if st.button("Build Knowledge Graph"):
                with st.spinner("Building knowledge graph..."):
                    try:
                        os.system("python src/build_knowledge_graph.py")
                        st.success("Knowledge graph built successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error building knowledge graph: {str(e)}")

if __name__ == "__main__":
    main()

import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.utils.config import Config

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service for collecting and analyzing user feedback"""
    
    def __init__(self):
        """Initialize the feedback service"""
        # Create directory for feedback data
        self.feedback_dir = os.path.join(os.getcwd(), "feedback")
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
            
        self.feedback_file = os.path.join(self.feedback_dir, "feedback.jsonl")
        self.analytics_file = os.path.join(self.feedback_dir, "analytics.json")
        
    def save_feedback(self, query: str, response: Dict[str, Any], rating: int, 
                     comment: Optional[str] = None) -> bool:
        """
        Save user feedback to the feedback file
        
        Args:
            query: User query
            response: Bot response dict
            rating: User rating (1-5)
            comment: Optional user comment
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create feedback entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response.get("answer", ""),
                "rating": rating,
                "comment": comment,
                "sources": [
                    {
                        "metadata": source.get("metadata", {}),
                        "text_snippet": source.get("text", "")[:100] if source.get("text") else ""
                    } for source in response.get("sources", [])
                ]
            }
            
            # Append to feedback file
            with open(self.feedback_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
                
            # Update analytics
            self._update_analytics(entry)
            
            logger.info(f"Saved feedback with rating {rating}")
            return True
        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}")
            return False
    
    def _update_analytics(self, entry: Dict[str, Any]) -> None:
        """
        Update analytics based on new feedback
        
        Args:
            entry: Feedback entry
        """
        try:
            # Load existing analytics or create new
            analytics = self._load_analytics()
            
            # Update total queries and average rating
            analytics["total_queries"] += 1
            analytics["total_rating_sum"] += entry["rating"]
            analytics["average_rating"] = analytics["total_rating_sum"] / analytics["total_queries"]
            
            # Update rating distribution
            rating_str = str(entry["rating"])
            if rating_str in analytics["rating_distribution"]:
                analytics["rating_distribution"][rating_str] += 1
            else:
                analytics["rating_distribution"][rating_str] = 1
                
            # Track common queries
            query_words = entry["query"].lower().split()
            for word in query_words:
                if len(word) > 3:  # Skip short words
                    if word in analytics["common_query_terms"]:
                        analytics["common_query_terms"][word] += 1
                    else:
                        analytics["common_query_terms"][word] = 1
                        
            # Save updated analytics
            with open(self.analytics_file, "w") as f:
                json.dump(analytics, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")
    
    def _load_analytics(self) -> Dict[str, Any]:
        """
        Load analytics data or create new if not exists
        
        Returns:
            Dict containing analytics data
        """
        if not os.path.exists(self.analytics_file):
            # Create default analytics structure
            return {
                "total_queries": 0,
                "total_rating_sum": 0,
                "average_rating": 0,
                "rating_distribution": {},
                "common_query_terms": {},
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(self.analytics_file, "r") as f:
                analytics = json.load(f)
                # Update last updated timestamp
                analytics["last_updated"] = datetime.now().isoformat()
                return analytics
        except Exception as e:
            logger.error(f"Error loading analytics, creating new: {str(e)}")
            return {
                "total_queries": 0,
                "total_rating_sum": 0,
                "average_rating": 0,
                "rating_distribution": {},
                "common_query_terms": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get current analytics
        
        Returns:
            Dict containing analytics data
        """
        return self._load_analytics()
        
    def get_failed_queries(self, min_rating: int = 2) -> List[Dict[str, Any]]:
        """
        Get queries with poor ratings
        
        Args:
            min_rating: Maximum rating to consider as failed (default: 2)
            
        Returns:
            List of failed query entries
        """
        failed_queries = []
        
        if not os.path.exists(self.feedback_file):
            return failed_queries
            
        try:
            with open(self.feedback_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("rating", 0) <= min_rating:
                            failed_queries.append(entry)
                    except json.JSONDecodeError:
                        continue
                        
            return failed_queries
        except Exception as e:
            logger.error(f"Error getting failed queries: {str(e)}")
            return []

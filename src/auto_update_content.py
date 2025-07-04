#!/usr/bin/env python3
"""
Script to automatically fetch and update content from a website
"""
import argparse
import logging
import sys
import os
import requests
from bs4 import BeautifulSoup
import time
import hashlib
from datetime import datetime
import json
from urllib.parse import urljoin, urlparse

from src.utils.config import Config
from src.services.indexing_service import IndexingService
from src.services.knowledge_graph_service import KnowledgeGraphService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("content_updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentUpdater:
    """Service to fetch and update content from websites"""
    
    def __init__(self, config_file=None):
        """
        Initialize the content updater
        
        Args:
            config_file: Path to config file with website URLs
        """
        self.config_file = config_file or "content_sources.json"
        self.data_dir = Config.DATA_DIR
        self.cache_dir = os.path.join(os.getcwd(), ".content_cache")
        
        # Create directories if they don't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def load_config(self):
        """
        Load website configuration
        
        Returns:
            dict: Configuration with website URLs and settings
        """
        if not os.path.exists(self.config_file):
            # Create default config if it doesn't exist
            default_config = {
                "websites": [
                    {
                        "name": "example",
                        "base_url": "https://example.com",
                        "paths": ["/", "/about", "/faq"],
                        "css_selector": "main",
                        "max_pages": 10,
                        "follow_links": True
                    }
                ],
                "update_frequency_hours": 24
            }
            
            with open(self.config_file, "w") as f:
                json.dump(default_config, f, indent=2)
                
            logger.info(f"Created default config file: {self.config_file}")
            return default_config
            
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                logger.info(f"Loaded config with {len(config.get('websites', []))} websites")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {"websites": [], "update_frequency_hours": 24}
            
    def get_page_content(self, url, css_selector=None):
        """
        Get content from a webpage
        
        Args:
            url: URL to fetch
            css_selector: CSS selector to extract specific content (optional)
            
        Returns:
            tuple: (content, success)
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            if css_selector:
                # Extract content using selector
                content_elements = soup.select(css_selector)
                if content_elements:
                    content = "\n\n".join([elem.get_text(separator="\n").strip() for elem in content_elements])
                else:
                    # Fallback to body if selector doesn't match
                    content = soup.body.get_text(separator="\n").strip()
            else:
                # Get all text from body
                content = soup.body.get_text(separator="\n").strip()
                
            # Add title
            title = soup.title.string if soup.title else url
            content = f"# {title}\n\nURL: {url}\n\n{content}"
            
            return content, True
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return f"Error fetching {url}: {str(e)}", False
            
    def extract_links(self, url, html_content, base_url):
        """
        Extract links from HTML content
        
        Args:
            url: Current URL
            html_content: HTML content
            base_url: Base URL for the website
            
        Returns:
            list: Extracted links
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(url, href)
            
            # Check if link is within the same domain
            if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                links.append(absolute_url)
                
        return links
        
    def get_content_hash(self, content):
        """Generate hash for content to detect changes"""
        return hashlib.md5(content.encode()).hexdigest()
        
    def update_website_content(self, website_config):
        """
        Update content for a specific website
        
        Args:
            website_config: Configuration for the website
            
        Returns:
            tuple: (updated_count, error_count)
        """
        name = website_config.get("name", "unnamed")
        base_url = website_config.get("base_url")
        paths = website_config.get("paths", ["/"])
        css_selector = website_config.get("css_selector")
        max_pages = website_config.get("max_pages", 10)
        follow_links = website_config.get("follow_links", False)
        
        logger.info(f"Updating content for {name} ({base_url})")
        
        updated_count = 0
        error_count = 0
        visited_urls = set()
        urls_to_visit = [urljoin(base_url, path) for path in paths]
        
        while urls_to_visit and len(visited_urls) < max_pages:
            url = urls_to_visit.pop(0)
            
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            logger.info(f"Fetching: {url}")
            
            # Get content
            content, success = self.get_page_content(url, css_selector)
            
            if not success:
                error_count += 1
                continue
                
            # Generate filename
            parsed_url = urlparse(url)
            path = parsed_url.path
            if path.endswith('/'):
                path += 'index'
                
            # Clean path for filename
            path = path.replace('/', '_').strip('_')
            if not path:
                path = 'index'
                
            filename = f"{name}_{path}.md"
            filepath = os.path.join(self.data_dir, filename)
            
            # Check cache to see if content changed
            content_hash = self.get_content_hash(content)
            cache_file = os.path.join(self.cache_dir, f"{name}_{path}.hash")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    old_hash = f.read().strip()
                    
                if old_hash == content_hash:
                    logger.info(f"Content unchanged for {url}")
                    continue
            
            # Save content
            with open(filepath, 'w') as f:
                f.write(content)
                
            # Update cache
            with open(cache_file, 'w') as f:
                f.write(content_hash)
                
            updated_count += 1
            logger.info(f"Updated: {filepath}")
            
            # Extract links if needed
            if follow_links and len(visited_urls) < max_pages:
                try:
                    response = requests.get(url, timeout=10)
                    new_links = self.extract_links(url, response.text, base_url)
                    
                    # Add new links to visit
                    for link in new_links:
                        if link not in visited_urls and link not in urls_to_visit:
                            urls_to_visit.append(link)
                            
                except Exception as e:
                    logger.error(f"Error extracting links from {url}: {str(e)}")
                    
        logger.info(f"Finished updating {name}: {updated_count} pages updated, {error_count} errors")
        return updated_count, error_count
        
    def run_update(self):
        """
        Run the content update process for all websites
        
        Returns:
            tuple: (total_updated, total_errors)
        """
        config = self.load_config()
        websites = config.get("websites", [])
        
        if not websites:
            logger.warning("No websites configured for updates")
            return 0, 0
            
        total_updated = 0
        total_errors = 0
        
        for website in websites:
            updated, errors = self.update_website_content(website)
            total_updated += updated
            total_errors += errors
            
        logger.info(f"Update completed: {total_updated} pages updated, {total_errors} errors")
        
        return total_updated, total_errors
        
    def rebuild_indexes(self):
        """Rebuild vector index and knowledge graph if content was updated"""
        logger.info("Rebuilding indexes...")
        
        try:
            # Rebuild vector index
            indexing_service = IndexingService()
            index = indexing_service.build_index()
            if index:
                logger.info("Vector index rebuilt successfully")
            else:
                logger.error("Failed to rebuild vector index")
                
            # Rebuild knowledge graph
            kg_service = KnowledgeGraphService()
            success = kg_service.build_graph_from_documents()
            if success:
                logger.info("Knowledge graph rebuilt successfully")
            else:
                logger.error("Failed to rebuild knowledge graph")
                
        except Exception as e:
            logger.error(f"Error rebuilding indexes: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Update content from websites")
    parser.add_argument("--config", type=str, default="content_sources.json",
                        help="Path to config file (default: content_sources.json)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild indexes after update")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as a daemon that periodically updates content")
    args = parser.parse_args()
    
    updater = ContentUpdater(config_file=args.config)
    
    if args.daemon:
        logger.info("Starting content updater daemon")
        config = updater.load_config()
        update_frequency = config.get("update_frequency_hours", 24)
        
        while True:
            # Run update
            total_updated, _ = updater.run_update()
            
            # Rebuild indexes if content was updated
            if total_updated > 0 and args.rebuild:
                updater.rebuild_indexes()
                
            # Sleep until next update
            next_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Next update scheduled at: {next_update}")
            time.sleep(update_frequency * 3600)  # Convert hours to seconds
    else:
        # Run once
        total_updated, _ = updater.run_update()
        
        if total_updated > 0 and args.rebuild:
            updater.rebuild_indexes()

if __name__ == "__main__":
    main()

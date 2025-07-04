import logging
import os
from typing import List, Dict, Any, Tuple, Optional
import spacy
from py2neo import Graph, Node, Relationship
import networkx as nx
import matplotlib.pyplot as plt
import re

from src.utils.config import Config
from src.utils.data_loader import load_documents_from_directory

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    """Service for creating and querying a knowledge graph"""
    
    def __init__(self):
        """Initialize the knowledge graph service"""
        try:
            # Load spaCy model for NLP tasks
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {str(e)}")
            logger.info("Downloading spaCy model...")
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
            
        # Connect to Neo4j
        self.graph = None
        self.connected = False
        
        # Initialize local graph for visualization
        self.local_graph = nx.DiGraph()
        
    def connect_to_neo4j(self) -> bool:
        """
        Connect to Neo4j database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            uri = Config.NEO4J_URI
            user = Config.NEO4J_USER
            password = Config.NEO4J_PASSWORD
            
            self.graph = Graph(uri, auth=(user, password))
            # Test connection
            self.graph.run("MATCH (n) RETURN count(n) LIMIT 1")
            self.connected = True
            logger.info("Connected to Neo4j database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j database: {str(e)}")
            logger.info("Will use in-memory graph instead")
            self.connected = False
            return False
            
    def _clean_text(self, text: str) -> str:
        """Clean text for entity extraction"""
        # Remove special characters and normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.strip()
        
    def _normalize_entity(self, entity: str) -> str:
        """Normalize entity names"""
        return entity.strip().lower()
        
    def extract_entities_and_relations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities and relationships from text
        
        Args:
            text: Input text
            
        Returns:
            List of dictionaries containing extracted entity relations
        """
        # Process the text with spaCy
        doc = self.nlp(self._clean_text(text))
        
        relations = []
        
        # Extract entities and their relationships based on syntactic dependencies
        for sent in doc.sents:
            # Find the main verb (root) of the sentence
            root = None
            for token in sent:
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    root = token
                    break
                    
            if not root:
                continue
                
            # Find subject and object connected to the root verb
            subject = None
            obj = None
            
            for token in sent:
                # Find subjects
                if token.dep_ in ("nsubj", "nsubjpass") and token.head == root:
                    # Get the complete noun phrase
                    subject = " ".join([t.text for t in token.subtree if not t.dep_ in ("punct", "prep")])
                
                # Find objects
                if token.dep_ in ("dobj", "pobj", "attr") and (token.head == root or token.head.head == root):
                    # Get the complete noun phrase
                    obj = " ".join([t.text for t in token.subtree if not t.dep_ in ("punct", "prep")])
            
            # Create relation if both subject and object are found
            if subject and obj and root:
                relation = {
                    "subject": self._normalize_entity(subject),
                    "predicate": root.lemma_,
                    "object": self._normalize_entity(obj),
                    "sentence": sent.text
                }
                relations.append(relation)
                
        return relations
        
    def build_graph_from_documents(self, documents_dir: str = Config.DATA_DIR) -> bool:
        """
        Build a knowledge graph from documents
        
        Args:
            documents_dir: Directory containing documents
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Load documents
        documents = load_documents_from_directory(documents_dir)
        
        if not documents:
            logger.error(f"No documents found in {documents_dir}")
            return False
            
        # Reset graph
        self.local_graph = nx.DiGraph()
        
        # Try to connect to Neo4j
        neo4j_available = self.connect_to_neo4j()
        
        if neo4j_available:
            # Clear existing graph
            self.graph.run("MATCH (n) DETACH DELETE n")
            
        total_relations = 0
        
        # Process each document
        for document in documents:
            text = document.text
            metadata = document.metadata
            source = metadata.get('source', 'unknown')
            
            logger.info(f"Extracting entities and relations from {source}")
            
            # Extract entities and relations
            relations = self.extract_entities_and_relations(text)
            
            logger.info(f"Extracted {len(relations)} relations from {source}")
            total_relations += len(relations)
            
            # Add to graph
            for relation in relations:
                subject = relation['subject']
                predicate = relation['predicate']
                obj = relation['object']
                sentence = relation['sentence']
                
                # Add to local graph
                if subject not in self.local_graph:
                    self.local_graph.add_node(subject, type='entity')
                if obj not in self.local_graph:
                    self.local_graph.add_node(obj, type='entity')
                    
                self.local_graph.add_edge(subject, obj, relationship=predicate, sentence=sentence, source=source)
                
                # Add to Neo4j if available
                if neo4j_available:
                    query = """
                    MERGE (s:Entity {name: $subject})
                    MERGE (o:Entity {name: $object})
                    MERGE (s)-[r:RELATIONSHIP {type: $predicate}]->(o)
                    SET r.sentence = $sentence, r.source = $source
                    """
                    self.graph.run(query, subject=subject, object=obj, predicate=predicate, sentence=sentence, source=source)
                    
        logger.info(f"Added {total_relations} relations to knowledge graph")
        
        # Save visualization
        if len(self.local_graph.nodes) > 0:
            self._save_graph_visualization()
            
        return True
        
    def _save_graph_visualization(self, filename: str = "knowledge_graph.png"):
        """Save visualization of the graph"""
        try:
            # Create visualization directory if it doesn't exist
            viz_dir = os.path.join(os.getcwd(), "visualizations")
            if not os.path.exists(viz_dir):
                os.makedirs(viz_dir)
                
            filepath = os.path.join(viz_dir, filename)
            
            # Plot the graph
            plt.figure(figsize=(12, 10))
            pos = nx.spring_layout(self.local_graph)
            nx.draw_networkx_nodes(self.local_graph, pos, node_size=500)
            nx.draw_networkx_edges(self.local_graph, pos, width=1, alpha=0.7)
            nx.draw_networkx_labels(self.local_graph, pos, font_size=10)
            
            # Add edge labels
            edge_labels = {(u, v): d['relationship'] for u, v, d in self.local_graph.edges(data=True)}
            nx.draw_networkx_edge_labels(self.local_graph, pos, edge_labels=edge_labels, font_size=8)
            
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Saved graph visualization to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save graph visualization: {str(e)}")
            
    def query_graph(self, query: str) -> Dict[str, Any]:
        """
        Query the knowledge graph
        
        Args:
            query: Natural language query
            
        Returns:
            Dict containing answer and source information
        """
        # Extract entities from the query
        doc = self.nlp(query)
        entities = [ent.text.lower() for ent in doc.ents]
        
        # Also look for noun chunks as potential entities
        noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
        all_entities = set(entities + noun_chunks)
        
        # If no entities found, return empty result
        if not all_entities:
            return {
                "answer": "I couldn't identify specific entities in your question to search in the knowledge graph.",
                "facts": []
            }
            
        # Search the graph for matching entities
        facts = []
        
        if self.connected and self.graph:
            # Search in Neo4j
            for entity in all_entities:
                # Query for relationships where the entity is the subject
                query = """
                MATCH (s:Entity {name: $entity})-[r:RELATIONSHIP]->(o:Entity)
                RETURN s.name as subject, r.type as predicate, o.name as object, r.sentence as sentence, r.source as source
                LIMIT 5
                """
                results = self.graph.run(query, entity=entity).data()
                facts.extend(results)
                
                # Query for relationships where the entity is the object
                query = """
                MATCH (s:Entity)-[r:RELATIONSHIP]->(o:Entity {name: $entity})
                RETURN s.name as subject, r.type as predicate, o.name as object, r.sentence as sentence, r.source as source
                LIMIT 5
                """
                results = self.graph.run(query, entity=entity).data()
                facts.extend(results)
        else:
            # Search in local graph
            for entity in all_entities:
                # Look for entity as subject (outgoing edges)
                if entity in self.local_graph:
                    for _, obj, data in self.local_graph.out_edges(entity, data=True):
                        fact = {
                            "subject": entity,
                            "predicate": data.get('relationship', ''),
                            "object": obj,
                            "sentence": data.get('sentence', ''),
                            "source": data.get('source', 'unknown')
                        }
                        facts.append(fact)
                
                # Look for entity as object (incoming edges)
                for subj, _, data in self.local_graph.in_edges(entity, data=True):
                    fact = {
                        "subject": subj,
                        "predicate": data.get('relationship', ''),
                        "object": entity,
                        "sentence": data.get('sentence', ''),
                        "source": data.get('source', 'unknown')
                    }
                    facts.append(fact)
                    
        # Format the answer
        if facts:
            answer = "Based on the knowledge graph, I found these facts:\n\n"
            for fact in facts:
                answer += f"- {fact['subject']} {fact['predicate']} {fact['object']}\n"
        else:
            answer = "I couldn't find specific information about your query in the knowledge graph."
            
        return {
            "answer": answer,
            "facts": facts
        }

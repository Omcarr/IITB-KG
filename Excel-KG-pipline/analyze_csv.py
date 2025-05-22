import pandas as pd
from neo4j import GraphDatabase
import json
import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging
from GroqNeo4jProcessor import CSVToKnowledgeGraph

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    # Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    NEO4J_URI = os.environ.get("NEO4J_URI")
    NEO4J_USER = os.environ.get("NEO4J_USER")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
    CSV_FILE_PATH = os.environ.get("CSV_FILE_PATH")
    
        # Initialize the converter
    converter = CSVToKnowledgeGraph(
        groq_api_key=GROQ_API_KEY,
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD
    )
    
    try:
        # Process CSV and create knowledge graph
        converter.process_csv_to_knowledge_graph(CSV_FILE_PATH)
        
        # Example queries
        print("\n=== Sample Queries ===")
        
        # Get all nodes
        nodes = converter.query_knowledge_graph("MATCH (n) RETURN count(n) as total_nodes")
        print(f"Total nodes: {nodes[0]['total_nodes']}")
        
        # Get all relationships
        relationships = converter.query_knowledge_graph("MATCH ()-[r]->() RETURN count(r) as total_relationships")
        print(f"Total relationships: {relationships[0]['total_relationships']}")
        
        # Get all entity types
        entity_types = converter.query_knowledge_graph("""
            MATCH (n) 
            RETURN labels(n) as entity_types, count(*) as count 
            ORDER BY count DESC
        """)
        print("\nEntity types:")
        for item in entity_types[:10]:  # Top 10
            print(f"  {item['entity_types']}: {item['count']}")
        
        # Get sample entities and their connections
        sample_entities = converter.query_knowledge_graph("""
            MATCH (n)-[r]->(m) 
            RETURN n.name as source, type(r) as relationship, m.name as target 
            LIMIT 10
        """)
        print("\nSample relationships:")
        for rel in sample_entities:
            print(f"  {rel['source']} --[{rel['relationship']}]--> {rel['target']}")
            
    finally:
        converter.close()


if __name__ == "__main__":
    main()
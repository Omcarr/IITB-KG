import pandas as pd
from neo4j import GraphDatabase
import json
import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging
from GroqNeo4jProcessor import GroqNeo4jProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


#load the csv
# try:
#     df = pd.read_csv(file_path, 
#                      engine='python',
#                      on_bad_lines='skip',
#                      skipinitialspace=True)
#     print(f"CSV loaded successfully! Shape: {df.shape}")
#     print(f"Columns: {list(df.columns)}")
# except Exception as e:
#     print(f"Error reading CSV: {e}")
    
    
#neo4j driver connection
# driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))


def main():
    load_dotenv()

    # Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    NEO4J_URI = os.environ.get("NEO4J_URI")
    NEO4J_USER = os.environ.get("NEO4J_USER")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
    CSV_FILE_PATH = os.environ.get("CSV_FILE_PATH")
    
    # Initialize processor
    processor = GroqNeo4jProcessor(GROQ_API_KEY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # Step 1: Prepare CSV sample
        logger.info("Preparing CSV sample for LLM analysis...")
        csv_sample, df = processor.prepare_csv_sample(CSV_FILE_PATH)
        
        # Step 2: Create prompt
        prompt = processor.create_groq_prompt(csv_sample)
        
        # Step 3: Query LLM
        logger.info("Querying Groq LLM for schema design...")
        schema_response = processor.query_groq_llm(prompt)
        
        # Step 4: Display analysis
        logger.info("LLM Analysis Results:")
        logger.info(f"CSV Structure: {schema_response['analysis']['csv_structure']}")
        logger.info(f"Identified Entities: {schema_response['analysis']['identified_entities']}")
        logger.info(f"Identified Relationships: {schema_response['analysis']['identified_relationships']}")
        
        # Step 5: Create Neo4j database
        logger.info("Creating Neo4j database...")
        processor.create_neo4j_database(schema_response, CSV_FILE_PATH)
        
        # Step 6: Get statistics
        stats = processor.get_database_statistics()
        logger.info("Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Step 7: Run sample queries
        processor.run_sample_queries(schema_response)
        
        logger.info("Process completed successfully!")
        
        # Save schema response for reference
        with open('schema_response.json', 'w') as f:
            json.dump(schema_response, f, indent=2)
        logger.info("Schema response saved to schema_response.json")
        
    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise
    
    finally:
        processor.close()

if __name__ == "__main__":
    main()
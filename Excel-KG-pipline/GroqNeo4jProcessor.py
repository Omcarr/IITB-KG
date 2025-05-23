import pandas as pd
from neo4j import GraphDatabase
import logging, json
from groq import Groq
from typing import Dict, List, Any
import re
import os

LLM = "llama-3.3-70b-versatile"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVToKnowledgeGraph:
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize the CSV to Knowledge Graph converter
        
        Args:
            groq_api_key: Your Groq API key
            neo4j_uri: Neo4j database URI (e.g., "bolt://localhost:7687")
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.groq_client = Groq(api_key=groq_api_key)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def read_csv(self, csv_file_path: str) -> pd.DataFrame:
        """Read CSV file into pandas DataFrame"""
        try:
            df = pd.read_csv(csv_file_path)
            logger.info(f"Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
    
    def extract_entities_relationships(self, text: str) -> Dict[str, Any]:
        """
        Use Groq LLaMA to extract entities and relationships from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing entities and relationships
        """
        prompt = f"""
        Analyze the following industrial equipment maintenance data and extract entities and relationships. 
        This data represents equipment hierarchies, failure modes, maintenance strategies, and monitoring systems.
        
        Return your response as a valid JSON object with the following structure:
        {{
            "entities": [
                {{"name": "entity_name", "type": "entity_type", "properties": {{"key": "value"}}}}
            ],
            "relationships": [
                {{"source": "source_entity", "target": "target_entity", "type": "relationship_type", "properties": {{"key": "value"}}}}
            ]
        }}
        
        Entity types should include:
        - EQUIPMENT: Main equipment (e.g., GasTurbine1)
        - SYSTEM: Sub-systems (e.g., FuelSystem, LubeOilSystem, HPAirSystem)
        - COMPONENT: Individual components (e.g., FuelPump, OilFilter, AirCompressor)
        - FAILURE_MODE: Types of failures (e.g., Seizing, Clogging, Leak)
        - MAINTENANCE_STRATEGY: Maintenance approaches (e.g., Predictive Maintenance, Time-Based Maintenance)
        - DETECTION_METHOD: Monitoring techniques (e.g., Vibration monitoring, Pressure monitoring)
        - SPARE_PART: Replacement parts (e.g., Fuel Pump, Oil Filter)
        - CONDITION_DATA: Monitoring parameters (e.g., Vibration levels, Pressure drop)
        
        Relationship types should include:
        - HAS_ASSEMBLY: Equipment has systems/assemblies
        - HAS_COMPONENT: Systems have components
        - HAS_FAILURE_MODE: Components have failure modes
        - USES_MAINTENANCE_STRATEGY: Failure modes use specific maintenance strategies
        - DETECTED_BY: Failure modes are detected by methods
        - MONITORED_BY: Components are monitored by detection methods
        - REQUIRES_SPARE_PART: Failure modes require specific spare parts for repair
        - HAS_CONDITION_DATA: Failure modes have associated condition monitoring data
        - CAUSES_CONSEQUENCE: Failure modes cause consequences
        - OCCURS_IN: Failure modes occur in specific components
        
        Extract key properties like:
        - severity: Critical, Major, Minor
        - frequency: maintenance intervals
        - rul: Remaining Useful Life in hours
        - consequence: impact of failure
        - threshold: monitoring thresholds
        
        Text to analyze:
        {text}
        
        JSON Response:
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert in knowledge graph extraction. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=LLM , # You can also use "llama-3.1-8b-instant" for faster processing
                temperature=0.1,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                logger.warning(f"No JSON found in response: {response_text}")
                return {"entities": [], "relationships": []}
                
        except Exception as e:
            logger.error(f"Error extracting entities and relationships: {e}")
            return {"entities": [], "relationships": []}
    
    def process_csv_row(self, row: pd.Series) -> Dict[str, Any]:
        """
        Process a single CSV row to extract entities and relationships
        Specifically designed for industrial equipment maintenance data
        
        Args:
            row: Pandas Series representing a CSV row
            
        Returns:
            Dictionary containing extracted entities and relationships
        """
        # Create a structured text representation of the row
        level = row.get('Level', '')
        entity = row.get('Entity', '')
        relationship = row.get('Relationship', '')
        related_entity = row.get('*Related Entity', '')
        failure_mode = row.get('*Failure Mode', '')
        severity = row.get('*Severity', '')
        consequence = row.get('*Consequence', '')
        detection_method = row.get('Detection Method', '')
        maintenance_strategy = row.get('**Maintenance Strategy', '')
        frequency = row.get('***Frequency', '')
        condition_data = row.get('*Condition Monitoring Data', '')
        rul = row.get('RUL', '')
        spare_parts = row.get('Spare Parts', '')
        
        text_content = f"""
        Equipment Level: {level}
        Main Entity: {entity}
        Relationship Type: {relationship}
        Related Entity: {related_entity}
        Failure Mode: {failure_mode}
        Severity Level: {severity}
        Failure Consequence: {consequence}
        Detection Method: {detection_method}
        Maintenance Strategy: {maintenance_strategy}
        Maintenance Frequency: {frequency}
        Condition Monitoring Data: {condition_data}
        Remaining Useful Life: {rul}
        Required Spare Parts for this Failure: {spare_parts}
        
        IMPORTANT CONTEXT: The spare part '{spare_parts}' is specifically required to repair the failure mode '{failure_mode}' 
        when it occurs in component '{related_entity}'. The maintenance strategy '{maintenance_strategy}' is used specifically 
        for managing this failure mode, not just the component in general. The detection method '{detection_method}' is used 
        to detect this specific failure mode.
        """
        
        if not text_content.strip():
            return {"entities": [], "relationships": []}
        
        return self.extract_entities_relationships(text_content)
    
    def create_neo4j_constraints(self):
        """Create constraints and indexes in Neo4j for better performance"""
        with self.driver.session() as session:
            # Create uniqueness constraints for industrial equipment entities
            constraints = [
                "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (n:Entity) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT equipment_name IF NOT EXISTS FOR (n:EQUIPMENT) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT system_name IF NOT EXISTS FOR (n:SYSTEM) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT component_name IF NOT EXISTS FOR (n:COMPONENT) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT failure_mode_name IF NOT EXISTS FOR (n:FAILURE_MODE) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT maintenance_strategy_name IF NOT EXISTS FOR (n:MAINTENANCE_STRATEGY) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT detection_method_name IF NOT EXISTS FOR (n:DETECTION_METHOD) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT spare_part_name IF NOT EXISTS FOR (n:SPARE_PART) REQUIRE n.name IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")
    
    def create_entity_in_neo4j(self, entity: Dict[str, Any]):
        """Create an entity node in Neo4j"""
        with self.driver.session() as session:
            entity_type = entity.get('type', 'Entity').upper()
            entity_name = entity['name']
            properties = entity.get('properties', {})
            
            # Create Cypher query
            cypher = f"""
            MERGE (e:{entity_type} {{name: $name}})
            SET e += $properties
            RETURN e
            """
            
            session.run(cypher, name=entity_name, properties=properties)
    
    def create_relationship_in_neo4j(self, relationship: Dict[str, Any]):
        """Create a relationship in Neo4j"""
        with self.driver.session() as session:
            source = relationship['source']
            target = relationship['target']
            rel_type = relationship['type'].upper().replace(' ', '_')
            properties = relationship.get('properties', {})
            
            # Create Cypher query
            cypher = f"""
            MATCH (a {{name: $source}})
            MATCH (b {{name: $target}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN r
            """
            
            session.run(cypher, source=source, target=target, properties=properties)
    
    def process_csv_to_knowledge_graph(self, csv_file_path: str, batch_size: int = 10):
        """
        Main method to process CSV file and create knowledge graph
        
        Args:
            csv_file_path: Path to the CSV file
            batch_size: Number of rows to process at once
        """
        # Read CSV
        df = self.read_csv(csv_file_path)
        
        # Create Neo4j constraints
        self.create_neo4j_constraints()
        
        # Clear existing data (optional - remove this if you want to append)
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Cleared existing Neo4j data")
        
        # Process CSV rows
        total_entities = 0
        total_relationships = 0
        
        for index, row in df.iterrows():
            logger.info(f"Processing row {index + 1}/{len(df)}")
            
            # Extract entities and relationships
            extracted_data = self.process_csv_row(row)
            
            # Create entities in Neo4j
            for entity in extracted_data.get('entities', []):
                try:
                    self.create_entity_in_neo4j(entity)
                    total_entities += 1
                except Exception as e:
                    logger.error(f"Error creating entity {entity}: {e}")
            
            # Create relationships in Neo4j
            for relationship in extracted_data.get('relationships', []):
                try:
                    self.create_relationship_in_neo4j(relationship)
                    total_relationships += 1
                except Exception as e:
                    logger.error(f"Error creating relationship {relationship}: {e}")
            
            # Process in batches to avoid overwhelming the API
            if (index + 1) % batch_size == 0:
                logger.info(f"Processed {index + 1} rows so far...")
        
        logger.info(f"Knowledge graph creation completed!")
        logger.info(f"Total entities created: {total_entities}")
        logger.info(f"Total relationships created: {total_relationships}")
    
    def query_knowledge_graph(self, cypher_query: str) -> List[Dict]:
        """Execute a Cypher query on the knowledge graph"""
        with self.driver.session() as session:
            result = session.run(cypher_query)
            return [record.data() for record in result]
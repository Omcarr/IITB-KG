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

class GroqNeo4jProcessor:
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize the processor with API credentials"""
        self.groq_client = Groq(api_key=groq_api_key)
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
    def close(self):
        """Close Neo4j connection"""
        self.neo4j_driver.close()
    
    def prepare_csv_sample(self, csv_file_path: str, sample_rows: int = 10) -> str:
        """Prepare CSV sample for the LLM prompt"""
        try:
            df = pd.read_csv(csv_file_path, engine='python', on_bad_lines='skip', skipinitialspace=True)
            logger.info(f"CSV loaded: {df.shape[0]} rows, {df.shape[1]} columns")
            
            # Get sample data
            sample_df = df.head(sample_rows)
            csv_sample = sample_df.to_string(index=False)
            
            return csv_sample, df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def create_groq_prompt(self, csv_sample: str) -> str:
        """Create the standardized prompt for Groq LLM"""
        
        prompt = f"""You are an expert in knowledge graph modeling and Neo4j database design. Your task is to analyze a CSV dataset and provide a comprehensive Neo4j graph schema and Cypher queries.

                **CSV Data Analysis:**
                ```
                {csv_sample}
                ```

                **Instructions:**
                1. Analyze the CSV structure and identify potential entities, relationships, and attributes
                2. Design an optimal Neo4j graph schema with appropriate node labels and relationship types
                3. Provide complete Cypher queries for data import
                4. Ensure the schema follows graph database best practices

                **Required Output Format (JSON):**
                ```json
                {{
                "analysis": {{
                    "csv_structure": "Brief description of the CSV structure",
                    "identified_entities": ["List of main entities"],
                    "identified_relationships": ["List of relationships between entities"],
                    "data_quality_notes": "Any data quality observations"
                }},
                "schema": {{
                    "nodes": [
                    {{
                        "label": "NodeLabel",
                        "properties": ["property1", "property2"],
                        "description": "What this node represents",
                        "unique_property": "property_name_for_uniqueness"
                    }}
                    ],
                    "relationships": [
                    {{
                        "type": "RELATIONSHIP_TYPE",
                        "from": "SourceNodeLabel",
                        "to": "TargetNodeLabel",
                        "properties": ["rel_property1"],
                        "description": "What this relationship represents"
                    }}
                    ]
                }},
                "cypher_queries": {{
                    "constraints": [
                    "CREATE CONSTRAINT constraint_name IF NOT EXISTS FOR (n:NodeLabel) REQUIRE n.property IS UNIQUE"
                    ],
                    "indexes": [
                    "CREATE INDEX index_name IF NOT EXISTS FOR (n:NodeLabel) ON (n.property)"
                    ],
                    "data_import": [
                    "LOAD CSV WITH HEADERS FROM 'file:///data.csv' AS row CREATE (n:NodeLabel {{property: row.column}})"
                    ]
                }},
                "mapping": {{
                    "csv_column_to_graph": {{
                    "csv_column_name": {{
                        "maps_to": "node_property or relationship_property",
                        "node_label": "ApplicableNodeLabel",
                        "data_type": "string/integer/float/boolean/date",
                        "transformation": "any data transformation needed"
                    }}
                    }}
                }},
                "sample_queries": [
                    {{
                    "description": "Find all nodes of specific type",
                    "cypher": "MATCH (n:NodeLabel) RETURN n LIMIT 10"
                    }}
                ]
                }}
                ```

                **Requirements:**
                - Use clear, descriptive node labels and relationship types
                - Ensure each node has a unique identifier property
                - Handle potential data quality issues (missing values, duplicates)
                - Follow Neo4j naming conventions (CamelCase for labels, UPPER_CASE for relationships)
                - Provide both creation and querying examples
                - Consider scalability and performance
                - Handle hierarchical relationships if present
                - Include data validation and error handling

                **Important Notes:**
                - Analyze the data semantically, not just structurally
                - Identify implicit relationships between entities
                - Consider creating intermediate nodes for complex relationships
                - Suggest indexes for frequently queried properties
                - Provide alternative modeling approaches if applicable

                Please provide ONLY the JSON output without additional explanations."""

        return prompt
    
    def query_groq_llm(self, prompt: str) -> Dict[str, Any]:
        """Query Groq LLM and parse the response"""
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model= LLM,
                temperature=0.1,  # Low temperature for consistent output
                max_tokens=4000,
                top_p=0.9
            )
            
            response_text = chat_completion.choices[0].message.content
            logger.info("Received response from Groq LLM")
            
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                else:
                    json_str = response_text
            
            # Parse JSON
            schema_response = json.loads(json_str)
            logger.info("Successfully parsed LLM response")
            return schema_response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise
        except Exception as e:
            logger.error(f"Error querying Groq LLM: {e}")
            raise
    
    def validate_schema_response(self, schema_response: Dict[str, Any]) -> bool:
        """Validate the schema response from LLM"""
        required_keys = ['analysis', 'schema', 'cypher_queries', 'mapping']
        
        for key in required_keys:
            if key not in schema_response:
                logger.error(f"Missing required key: {key}")
                return False
        
        # Validate schema structure
        if 'nodes' not in schema_response['schema'] or 'relationships' not in schema_response['schema']:
            logger.error("Schema missing nodes or relationships")
            return False
        
        # Validate cypher_queries structure
        cypher_keys = ['constraints', 'indexes', 'data_import']
        for key in cypher_keys:
            if key not in schema_response['cypher_queries']:
                logger.warning(f"Missing cypher query type: {key}")
        
        logger.info("Schema response validation passed")
        return True
    
    def create_neo4j_database(self, schema_response: Dict[str, Any], csv_file_path: str) -> None:
        """Create Neo4j database based on LLM schema response"""
        
        if not self.validate_schema_response(schema_response):
            raise ValueError("Invalid schema response")
        
        with self.neo4j_driver.session() as session:
            try:
                # Step 1: Create constraints
                logger.info("Creating constraints...")
                for constraint in schema_response['cypher_queries'].get('constraints', []):
                    try:
                        session.run(constraint)
                        logger.info(f"Created constraint: {constraint}")
                    except Exception as e:
                        logger.warning(f"Constraint creation failed (may already exist): {e}")
                
                # Step 2: Create indexes
                logger.info("Creating indexes...")
                for index in schema_response['cypher_queries'].get('indexes', []):
                    try:
                        session.run(index)
                        logger.info(f"Created index: {index}")
                    except Exception as e:
                        logger.warning(f"Index creation failed (may already exist): {e}")
                
                # Step 3: Import data
                logger.info("Importing data...")
                
                # Copy CSV to Neo4j import directory or use file:// protocol
                neo4j_csv_path = self.prepare_csv_for_neo4j(csv_file_path)
                
                for import_query in schema_response['cypher_queries'].get('data_import', []):
                    # Replace generic file path with actual path
                    modified_query = import_query.replace('file:///data.csv', f'file:///{neo4j_csv_path}')
                    
                    try:
                        result = session.run(modified_query)
                        logger.info(f"Executed import query: {modified_query[:100]}...")
                        
                        # Log summary if available
                        summary = result.consume()
                        if hasattr(summary, 'counters'):
                            logger.info(f"Nodes created: {summary.counters.nodes_created}")
                            logger.info(f"Relationships created: {summary.counters.relationships_created}")
                    
                    except Exception as e:
                        logger.error(f"Import query failed: {e}")
                        logger.error(f"Query: {modified_query}")
                        # Continue with other queries
                
                logger.info("Database creation completed successfully")
                
            except Exception as e:
                logger.error(f"Error creating Neo4j database: {e}")
                raise
    
    def prepare_csv_for_neo4j(self, csv_file_path: str) -> str:
        """Prepare CSV file for Neo4j import"""
        # For simplicity, return the filename
        # In production, you might want to copy the file to Neo4j's import directory
        return os.path.basename(csv_file_path)
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get statistics about the created database"""
        with self.neo4j_driver.session() as session:
            stats = {}
            
            # Get node counts by label
            result = session.run("CALL db.labels() YIELD label RETURN label")
            labels = [record['label'] for record in result]
            
            for label in labels:
                count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                stats[f"{label}_nodes"] = count_result.single()['count']
            
            # Get relationship counts
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total_relationships")
            stats['total_relationships'] = result.single()['total_relationships']
            
            # Get relationship types
            result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
            rel_types = [record['relationshipType'] for record in result]
            stats['relationship_types'] = rel_types
            
            return stats
    
    def run_sample_queries(self, schema_response: Dict[str, Any]) -> None:
        """Run sample queries provided by the LLM"""
        logger.info("Running sample queries...")
        
        with self.neo4j_driver.session() as session:
            for query_info in schema_response.get('sample_queries', []):
                try:
                    description = query_info.get('description', 'No description')
                    cypher = query_info.get('cypher', '')
                    
                    logger.info(f"Running query: {description}")
                    result = session.run(cypher)
                    
                    # Display first few results
                    records = list(result)
                    logger.info(f"Query returned {len(records)} records")
                    
                    for i, record in enumerate(records[:3]):  # Show first 3 results
                        logger.info(f"  Result {i+1}: {dict(record)}")
                
                except Exception as e:
                    logger.error(f"Sample query failed: {e}")
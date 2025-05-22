import pandas as pd
import json
import re
from groq import Groq
from neo4j import GraphDatabase
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
LLM = "llama-3.3-70b-versatile"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chat_Logger")

class MaintenanceKGChatbot:
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize the Maintenance Knowledge Graph Chatbot
        Args:
            groq_api_key: Your Groq API key
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.groq_client = Groq(api_key=groq_api_key)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Define the schema for the chatbot to understand
        self.kg_schema = {
            "entities": {
                "EQUIPMENT": "Main equipment units (e.g., GasTurbine1)",
                "SYSTEM": "Sub-systems within equipment (e.g., FuelSystem, LubeOilSystem)",
                "COMPONENT": "Individual components (e.g., FuelPump, OilFilter)",
                "FAILURE_MODE": "Types of failures (e.g., Seizing, Clogging, Leak)",
                "MAINTENANCE_STRATEGY": "Maintenance approaches (PdM, CBM, TBM)",
                "DETECTION_METHOD": "Monitoring techniques (Vibration monitoring, Pressure monitoring)",
                "SPARE_PART": "Replacement parts needed for repairs",
                "CONDITION_DATA": "Monitoring parameters and thresholds"
            },
            "relationships": {
                "HAS_ASSEMBLY": "Equipment contains systems",
                "HAS_COMPONENT": "Systems contain components", 
                "HAS_FAILURE_MODE": "Components can have failure modes",
                "REQUIRES_SPARE_PART": "Failure modes require specific spare parts",
                "USES_MAINTENANCE_STRATEGY": "Failure modes use maintenance strategies",
                "DETECTED_BY": "Failure modes are detected by methods",
                "CAUSES_CONSEQUENCE": "Failure modes cause consequences"
            }
        }
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def generate_cypher_query(self, user_question: str) -> Dict[str, Any]:
        """
        Generate Cypher query based on user question using Groq LLaMA
        
        Args:
            user_question: Natural language question from user
            
        Returns:
            Dictionary containing cypher query and explanation
        """
        schema_info = f"""
        Knowledge Graph Schema:
        
        Entity Types: {json.dumps(self.kg_schema['entities'], indent=2)}
        
        Relationship Types: {json.dumps(self.kg_schema['relationships'], indent=2)}
        
        Common Properties:
        - severity: "Critical", "Major", "Minor"
        - frequency: maintenance intervals
        - rul: Remaining Useful Life in hours
        - consequence: impact of failure
        - name: entity identifier
        """
        
        prompt = f"""
        You are an expert in Neo4j Cypher queries for industrial equipment maintenance systems.
        Based on the user's question, generate an appropriate Cypher query to retrieve information from the knowledge graph.
        
        {schema_info}
        
        User Question: "{user_question}"
        
        Provide your response as a JSON object with this structure:
        {{
            "cypher_query": "MATCH ... RETURN ...",
            "explanation": "Brief explanation of what the query does",
            "expected_result": "Description of what kind of results to expect"
        }}
        
        Guidelines:
        1. Use MATCH to find patterns
        2. Use WHERE for filtering (severity, names, etc.)
        3. Use RETURN to specify what data to retrieve
        4. Use LIMIT if appropriate to avoid overwhelming results
        5. Consider using COLLECT() for aggregating related items
        6. Handle both specific and general questions
        
        Common query patterns:
        - Equipment breakdown: MATCH (e:EQUIPMENT)-[:HAS_ASSEMBLY]->(s:SYSTEM)-[:HAS_COMPONENT]->(c:COMPONENT)
        - Failure analysis: MATCH (c:COMPONENT)-[:HAS_FAILURE_MODE]->(fm:FAILURE_MODE)
        - Spare parts: MATCH (fm:FAILURE_MODE)-[:REQUIRES_SPARE_PART]->(sp:SPARE_PART)
        - Maintenance: MATCH (fm:FAILURE_MODE)-[:USES_MAINTENANCE_STRATEGY]->(ms:MAINTENANCE_STRATEGY)
        
        JSON Response:
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert in Neo4j Cypher queries for industrial maintenance systems. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=LLM,
                temperature=0.1,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return {
                    "cypher_query": "MATCH (n) RETURN count(n) as total_nodes LIMIT 1",
                    "explanation": "Fallback query to count total nodes",
                    "expected_result": "Total number of nodes in the graph"
                }
                
        except Exception as e:
            logger.error(f"Error generating Cypher query: {e}")
            return {
                "cypher_query": "MATCH (n) RETURN count(n) as total_nodes LIMIT 1",
                "explanation": "Error occurred, showing total nodes as fallback",
                "expected_result": "Total number of nodes"
            }
    
    def execute_cypher_query(self, cypher_query: str) -> List[Dict]:
        """Execute Cypher query on Neo4j"""
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            return [{"error": f"Query execution failed: {str(e)}"}]
    
    def format_results(self, results: List[Dict], query_info: Dict[str, Any], user_question: str) -> str:
        """
        Format query results into natural language response using Groq LLaMA
        
        Args:
            results: Results from Neo4j query
            query_info: Information about the query
            user_question: Original user question
            
        Returns:
            Natural language response
        """
        if not results:
            return "I couldn't find any information matching your question in the knowledge graph."
        
        if "error" in results[0]:
            return f"There was an error processing your question: {results[0]['error']}"
        
        prompt = f"""
        Convert the following database query results into a natural, conversational response for the user.
        
        Original Question: "{user_question}"
        Query Explanation: {query_info.get('explanation', '')}
        
        Query Results: {json.dumps(results, indent=2)}
        
        Instructions:
        1. Provide a clear, informative answer in natural language
        2. Organize the information logically
        3. Use bullet points or numbering when listing multiple items
        4. Include relevant details like severity levels, maintenance frequencies, RUL values
        5. If showing relationships, explain them clearly
        6. Be concise but comprehensive
        
        Response:
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains industrial equipment maintenance data in clear, professional language."},
                    {"role": "user", "content": prompt}
                ],
                model=LLM,
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error formatting results: {e}")
            # Fallback to simple formatting
            return self._simple_format_results(results, user_question)
    
    def _simple_format_results(self, results: List[Dict], user_question: str) -> str:
        """Simple fallback formatting for results"""
        response = f"Here's what I found regarding your question: '{user_question}'\n\n"
        
        for i, result in enumerate(results[:10], 1):  # Limit to first 10 results
            response += f"{i}. "
            for key, value in result.items():
                if value is not None:
                    response += f"{key}: {value}, "
            response = response.rstrip(", ") + "\n"
        
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more results."
            
        logger.info("Unformatted result:", response)
        return response
    
    def ask_question(self, user_question: str) -> str:
        """
        Main method to process user questions and return answers
        
        Args:
            user_question: Natural language question from user
            
        Returns:
            Natural language answer
        """
        logger.info(f"Processing question: {user_question}")
        
        # Generate Cypher query
        query_info = self.generate_cypher_query(user_question)
        logger.info(f"Generated query: {query_info['cypher_query']}")
        
        # Execute query
        results = self.execute_cypher_query(query_info['cypher_query'])
        logger.info(f"Query returned {len(results)} results")
        
        # Format and return response
        response = self.format_results(results, query_info, user_question)
        return response
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick statistics about the knowledge graph"""
        stats_queries = {
            "total_equipment": "MATCH (n:EQUIPMENT) RETURN count(n) as count",
            "total_systems": "MATCH (n:SYSTEM) RETURN count(n) as count",
            "total_components": "MATCH (n:COMPONENT) RETURN count(n) as count",
            "total_failure_modes": "MATCH (n:FAILURE_MODE) RETURN count(n) as count",
            "critical_failures": "MATCH (n:FAILURE_MODE {severity: 'Critical'}) RETURN count(n) as count",
            "total_spare_parts": "MATCH (n:SPARE_PART) RETURN count(n) as count"
        }
        
        stats = {}
        for stat_name, query in stats_queries.items():
            try:
                result = self.execute_cypher_query(query)
                stats[stat_name] = result[0]['count'] if result else 0
            except:
                stats[stat_name] = 0
                
        return stats

def main():
    """Example usage of the chatbot"""
    # Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    NEO4J_URI = "bolt://localhost:7687" #os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
    
    print(GROQ_API_KEY, NEO4J_URI)
    # Initialize chatbot
    chatbot = MaintenanceKGChatbot(
        groq_api_key=GROQ_API_KEY,
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD
    )
    
    try:
        print("=== Industrial Equipment Maintenance Chatbot ===")
        print("Ask me questions about your equipment, failures, maintenance, spare parts, etc.")
        print("Type 'stats' for quick statistics, 'quit' to exit\n")
        
        # Show initial stats
        stats = chatbot.get_quick_stats()
        print("Knowledge Graph Overview:")
        for stat_name, count in stats.items():
            print(f"  {stat_name.replace('_', ' ').title()}: {count}")
        print()
        
        # example_questions = [
        #     "What are the critical failure modes in GasTurbine1?",
        #     "Which spare parts are needed for fuel system failures?",
        #     "What maintenance strategies are used for oil pump failures?",
        #     "Show me all components that use predictive maintenance",
        #     "Which failure modes cause operational downtime?",
        #     "What is the RUL for components with seizing failures?",
        #     "List all detection methods used for monitoring"
        # ]
        
        # Interactive chat loop
        while True:
            user_input = input("Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
            elif user_input.lower() == 'stats':
                stats = chatbot.get_quick_stats()
                print("\nKnowledge Graph Statistics:")
                for stat_name, count in stats.items():
                    print(f"  {stat_name.replace('_', ' ').title()}: {count}")
                print()
                continue
            elif not user_input:
                continue
            
            print(f"\n🤖 Processing your question...")
            response = chatbot.ask_question(user_input)
            print(f"\n📋 Answer:\n{response}\n")
            print("-" * 80)
            
    except KeyboardInterrupt:
        print("\nChatbot stopped.")
    finally:
        chatbot.close()

if __name__ == "__main__":
    main()
# 1. **Knowledge Graph-Based Chatbot With GPT-3 and Neo4j**  
[🔗 Link to article](https://neo4j.com/blog/developer/knowledge-graph-based-chatbot-with-gpt-3-and-neo4j/)

---

### **Key Findings**
- **Diffbot API** can be used for NLP pipeline testing:
  - Offers **100k free credits**.
  - **Not suitable for production** (paid and expensive).
- **Custom NER Pipeline** for testing:
  - [Tutorial on building a custom NER pipeline with spaCy](https://blog.knowledgator.com/extract-any-named-entities-from-pdf-using-custom-spacy-pipeline-9fd0af2c3e13).

---

![System Architecture proposed by this article](image.png)

---

# 2. **A Benchmark to Understand the Role of Knowledge Graphs on Large Language Model’s Accuracy for Question Answering on Enterprise SQL Databases**

---

- **Alignment**: Closely matches our work.
- **Dataset Used**: Enterprise relational database schema in the insurance domain.  
  [🔗 SQL DDL Link](https://www.omg.org/cgi-bin/doc?dtc/13-04-15.ddl)
- **Application**: Useful during OWL and R2RML phase and benchmarking.

---

### **Key Findings**
1. **Text-to-SQL workbenches**: Spider, WikiSQL, KaggleDBQA.
2. **Knowledge Graphs (KGs)** help bridge business context gaps and reduce hallucinations, thereby enhancing LLM accuracy.
3. **GPT-4 Benchmark**:
   - Without KG: 16.7% accuracy.
   - With KG: **54.2% accuracy** (3x improvement).
   - Settings: `max_tokens=2048`, `n=1`, `temp=0.3`, `timeout=60s`.
   - Insight: Combining KGs with NLP/RAGs substantially boosts performance.

---

![Ontology describing relevant parts of the Property and Casualty data model](image-3.png)
![Results](image-4.png)

---

# 3. **Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering**

---

- **Dataset Used**: Customer Service queries related to ticketing services.  
  - KG Types:
    - **Intra-issue Tree**
    - **Inter-issue Graph**  
- **Embeddings**: Generated for nodes using models like **BERT** and **E5**, stored in a **vector database** (e.g., Qdrant).

---

### **Key Findings**
1. KGs improve retrieval accuracy and mitigate the loss of structural information caused by text segmentation.
2. The method **outperforms baseline** by:
   - **77.6%** in **MRR** (Mean Reciprocal Rank).
   - **+0.32** in **BLEU score**.
3. KGs preserve the intrinsic relationships among issues, enhancing retrieval and answer quality.
4. **Real-world Deployment** at LinkedIn:
   - **28.6% reduction** in median issue resolution time.

---

### **Future Scope**
- **Automated Graph Template Extraction**: Eliminate manual template design.
- **Dynamic Graph Updates**: Real-time updates based on user queries.

---

### **Limitations**
1. **Template Dependency**: Manual maintenance required for KG templates.
2. **Static Graph**: KG isn't updated dynamically unless explicitly refreshed.

---





**Intresting Tutorials that closely align with our system:**
1. [GraphRag using Llamma and Neo4j](https://medium.com/@omotolaniosems/building-an-advanced-rag-chatbot-with-knowledge-graphs-using-llamaindex-neo4j-and-llama-3-1e3d3b07ede3)

 ![system arch](image-1.png)

2. [ GraphRAG App Project using Neo4j, Langchain, GPT-4o, and Streamlit ](https://www.youtube.com/watch?v=odtGLUPXqfs)
- this is using openai api for llm work, can be converted to llama based structure.

3. [Knowledge Graph-based ChatBot](https://medium.com/thecyphy/knowledge-graph-based-chatbot-5416a79d7f17)
- interesting idea of using siamese networks for intend classification and identification of existing intends in the Knowledge Graph in case of less data is available and classes are imbalanced.
![KG based chatbot arch ](image-2.png)

4. [GraphRAG: The Marriage of Knowledge Graphs and RAG: Emil Eifrem](https://youtu.be/knDDGYHnnSI?si=Z6FYP-GaOwb4MocX)
- Neo4j's CEO and Co-founder Emil shares his insight on how GraphDB paired with RAGs result in 3x more accurate results. the study that shows it is [link](https://arxiv.org/pdf/2311.07509)

5. [Github repo that collects everything LLM+KG](https://github.com/RManLuo/Awesome-LLM-KG)

6. [Book by Neo4j creaters around KG](https://go.neo4j.com/rs/710-RRC-335/images/developers-guide-how-to-build-knowledge-graph.pdf)


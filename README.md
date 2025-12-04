# Vinted Network Analysis & Reputation Dynamics 🛍️ 🕸️

## 📌 Project Overview
This project transforms the Vinted marketplace into an analyzable social network to study trust, community formation, and reputation diffusion. By modeling user interactions, the project uncovers latent social structures within a C2C e-commerce platform.

## 📂 Project Structure & Execution
The project is divided into two main logical phases: Data Collection (Scraping) and Network Analysis.

### **PHASE 1: Data Scraping**
Located in the `Vinted_env` folder (scripts + CSVs).
To reproduce the dataset creation, execute the scripts in the following strict order:

1.  `scrape_test_FINAL.py`: Initializes the scraping process.
2.  `dataset_construction.py`: Structures the raw data.
3.  `get_recensioni_venditori_FINAL.py`: Retrieves feedback and transaction details.

### **PHASE 2: Social Network Analysis**
Located in the `ASNM_ANALYSIS_RESULTS` folder (script + CSVs).
This phase models the graph and performs the analysis (Community Detection, Influence Maximization).

* **Main Script:** `asnm_analysis.py`

## 📊 Graph Visualization & Exploration
To interactively explore the network topology and verify the "Influential Nodes" (Seeds) found by the algorithms:

1.  **Load the Graph:** Open the file `analized_graph_FINAL.gexf` using [Gephi Lite](https://lite.gephi.org/v1.0.1).
2.  **Identify Influencers:** Navigate to the **"Data"** section (Data Laboratory) and sort the nodes by `Degree` to identify the users with the highest connections.
3.  **Real-World Verification:** Copy the `ID` of a node/user. To inspect their actual Vinted profile, paste the ID into the following URL structure:
    * `https://www.vinted.it/member/[INSERT_ID_HERE]`

*(Note: The graph file is included in the repo or linked in the documentation).*

## 🛠️ Methodology & Activities

* **Data Acquisition & Engineering:** Built a proprietary dataset through reverse engineering of Vinted APIs. Developed a resilient scraping pipeline with anti-bot handling (IP rotation, cookie injection) to reconstruct the social graph from bidirectional transactions and reviews.
* **Semantic Modeling:** Constructed a weighted directed graph and developed a custom "Semantic Tagging" algorithm to automatically classify users into vertical market niches or "Multi-Category" nodes based on their inventory.
* **Community Detection:** Applied the **Louvain algorithm**, identifying 66 thematic communities with a high modularity score (0.94), and implemented "Smart Naming" logic for interpretable cluster labeling.
* **Influence Analysis:** Simulated reputation propagation using the **Independent Cascade (IC)** model and identified influential seed nodes using the **CELF** greedy algorithm.
* **Visualization:** Rendered network topology in **Gephi** using ForceAtlas2 layout to highlight market segregation and Hub-and-Spoke structures.

## 💻 Tech Stack
* **Language:** Python
* **Analysis Libraries:** NetworkX, Pandas, NumPy
* **Algorithms:** Louvain, CELF, Independent Cascade
* **Tools:** Gephi, Vinted-API (Custom Reverse Engineering)

---
*For full details, please refer to the [Project Report PDF](./docs/Vinted_Analysis_Report.pdf).*

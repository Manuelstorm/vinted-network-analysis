# Vinted Network Analysis & Reputation Dynamics 🛍️ 🕸️

## 📌 Project Overview
This project transforms the Vinted marketplace into an analyzable social network to study trust, community formation, and reputation diffusion. By modeling user interactions, the project uncovers latent social structures within a C2C e-commerce platform.

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

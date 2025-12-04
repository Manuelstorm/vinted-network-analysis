import pandas as pd
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
import json
import os
import sys
import time
from typing import Dict, Any, List, Set, Tuple
from collections import Counter


try:
    from community import community_louvain
except ImportError:
    print("ERRORE: Manca 'python-louvain'. Installalo con: pip install python-louvain")
    sys.exit(1)

# =========================================================
# CONFIGURAZIONE
# =========================================================
INPUT_DATASET = "vinted_dataset_FINAL.csv" 
OUTPUT_DIR = "ASNM_ANALYSIS_RESULTS_FINAL"
OUTPUT_GRAPH_FILE = os.path.join(OUTPUT_DIR, "vinted_graph_FINAL.gexf")
SEED = 42

# Parametri Analisi
K_CENTRALITY = 1000 # Approssimazione Betweenness
IC_PROBABILITY = 0.1 # Prob. propagazione
IC_MC_SIMULATIONS = 50 # Monte Carlo sim per CELF 
K_SEEDS_CELF = 5 # Quanti nodi "Influencer" cercare con CELF

# =========================================================
# UTILITY
# =========================================================
def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

# =========================================================
# 1. LOAD E COSTRUZIONE GRAFO
# =========================================================
def build_graph(df: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()
    print("Costruzione del grafo in corso...")

    for _, row in df.iterrows():
        buyer_id = int(row["Acquirente_ID"])
        seller_id = int(row["Venditore_ID"])
        
        # Attributi
        buyer_tags = {
            "main_tag": row.get("Main_Tag_Acquirente", "Sconosciuto"),
            "detailed_tag": row.get("Detailed_Tag_Acquirente", "Sconosciuto")
        }
        seller_tags = {
            "main_tag": row.get("Main_Tag_Venditore", "Sconosciuto"),
            "detailed_tag": row.get("Detailed_Tag_Venditore", "Sconosciuto")
        }
        
        G.add_node(buyer_id, **buyer_tags)
        G.add_node(seller_id, **seller_tags)

        # Arco A -> B
        G.add_edge(
            buyer_id, seller_id, 
            weight=row.get("Numero_Transazioni", 1), 
            rating=row.get("Rating_Acquirente_V", 0)
        )
        
        # Arco B -> A (Se esiste)
        rating_v_a = row.get("Rating_Venditore_A", 0)
        if pd.notna(rating_v_a) and rating_v_a > 0:
            G.add_edge(
                seller_id, buyer_id, 
                weight=rating_v_a
            )

    print(f"Grafo costruito: {G.number_of_nodes()} nodi, {G.number_of_edges()} archi.")
    return G

# =========================================================
# 2. METRICHE STRUTTURALI & SIMILARITY
# =========================================================
def analyze_structure(G: nx.DiGraph):
    print("Calcolo metriche strutturali...")
    reciprocity = nx.reciprocity(G)
    
    G_undir = G.to_undirected()
    density = nx.density(G)
    
    # Clustering (Local & Average)
    print("Calcolo Clustering Coefficient...")
    avg_clustering = nx.average_clustering(G_undir)
    
    # JACCARD SIMILARITY (Link Overlap)
    print("Calcolo Jaccard Similarity (su archi esistenti)...")
    jaccard_coeffs = nx.jaccard_coefficient(G_undir, G_undir.edges())
    jaccard_values = [p for u, v, p in jaccard_coeffs]
    avg_jaccard = np.mean(jaccard_values) if jaccard_values else 0

    stats = {
        "nodi": G.number_of_nodes(),
        "archi": G.number_of_edges(),
        "densita": density,
        "reciprocita": reciprocity,
        "avg_clustering_coefficient": avg_clustering,
        "avg_jaccard_similarity": avg_jaccard
    }
    
    print(f"--- STATS ---")
    print(f"Reciprocità: {reciprocity:.5f}")
    print(f"Clustering: {avg_clustering:.5f}")
    print(f"Jaccard Similarity Media: {avg_jaccard:.5f}")
    
    return stats

# =========================================================
# 3. CENTRALITÀ
# =========================================================
def calculate_centralities(G: nx.DiGraph, k: int, seed: int) -> pd.DataFrame:
    """
    Calcola le metriche di centralità VELOCEMENTE.
    """
    print(f"Calcolo Degree Centrality (In/Out)...")
    in_degree = nx.in_degree_centrality(G)
    out_degree = nx.out_degree_centrality(G)
    
    print(f"Calcolo PageRank...")
    pagerank = nx.pagerank(G, alpha=0.85)
    
    print(f"Calcolo Betweenness Centrality (Approssimata con k={k})...")
    betweenness = nx.betweenness_centrality(G, k=k, seed=seed, normalized=True)

    # Conversione in DataFrame per eseguire l'analisi
    df_nodes = pd.DataFrame(
        list(G.nodes(data=True)), 
        columns=['Node_ID', 'attributes']
    )
    
    # Estrazione degli attributi in colonne separate
    df_nodes = pd.concat([
        df_nodes.drop(['attributes'], axis=1), 
        df_nodes['attributes'].apply(pd.Series)
    ], axis=1)

    # metriche
    df_nodes['in_degree'] = df_nodes['Node_ID'].map(in_degree)
    df_nodes['out_degree'] = df_nodes['Node_ID'].map(out_degree)
    df_nodes['pagerank'] = df_nodes['Node_ID'].map(pagerank)
    df_nodes['betweenness'] = df_nodes['Node_ID'].map(betweenness)
    
    return df_nodes.set_index('Node_ID')

# =========================================================
# 4. COMMUNITY DETECTION
# =========================================================
def run_community_detection(G: nx.DiGraph, seed: int) -> Dict:
    print("Eseguo Community Detection (Louvain)...")
    G_undir = G.to_undirected()
    partition = community_louvain.best_partition(G_undir, random_state=seed)
    modularity = community_louvain.modularity(partition, G_undir)
    print(f"Louvain: Trovate {len(set(partition.values()))} community. Mod: {modularity:.4f}")
    return partition, modularity


# =========================================================
# 5. NAMING DELLE COMMUNITY
# =========================================================
def naming_communities(df_nodes: pd.DataFrame) -> pd.DataFrame:
    print("Processo di Naming delle Communities...")
    
    community_names = {}
    grouped = df_nodes.groupby('Community')
    
    for comm_id, group in grouped:
        counts = group['main_tag'].value_counts()
        total_nodes = len(group)
        
        if not counts.empty:
            # 1. CERCA IL TEMA (Ignora Generalisti)
            top_tag = "Generalista"
            specific_found = False
            
            for tag in counts.index:
                # Ignoriamo tag generici o nulli per trovare l'argomento vero
                if tag not in ["Generalista", "Sconosciuto", "Inattivo"]:
                    top_tag = str(tag)
                    specific_found = True
                    break
            
            if not specific_found:
                top_tag = str(counts.index[0])

            # 2. CALCOLA DOMINANZA
            count_theme = counts[top_tag]
            dominance_perc = (count_theme / total_nodes) * 100
            
            # 3. PULIZIA E MAPPING 
            # Rimuoviamo i prefissi standard
            clean_name = top_tag.replace("Puro_", "").replace("Debole_", "").replace("Generalista_", "")
            
            #  MULTI_CATEGORY (Categoria1 + Categoria2)
            if "Multi_category" in clean_name:
                # Se la community è dominata da venditori misti, analizziamo i Detailed Tags
                detailed_counts = group[group['main_tag'] == top_tag]['detailed_tag'].value_counts()
                
                if not detailed_counts.empty:
                    top_detailed = str(detailed_counts.index[0]) # es. Multi_category_Moda_Lusso_Carte_TCG
                    
                    # Rimpiazziamo i tag lunghi con abbreviazioni per la legenda
                    short_mix = top_detailed.replace("Multi_category_", "").replace("Bridge_", "")
                    short_mix = short_mix.replace("Moda_Lusso", "MODA").replace("Tech_Elettronica", "TECH")
                    short_mix = short_mix.replace("Carte_TCG", "TCG").replace("Fumetti_Manga", "FUMETTI")
                    short_mix = short_mix.replace("Action_Figure", "ACTION").replace("Gaming_Console", "GAMING")
                    short_mix = short_mix.replace("Media_Vinili", "VINILI")
                    
                    short_mix = short_mix.replace("_", " & ")
                    
                    clean_name = f"MIX: {short_mix}"
                else:
                    clean_name = "MULTI-CATEGORY MIX"

            # MAPPING 
            elif "Moda" in clean_name: clean_name = "MODA & LUSSO"
            elif "Carte" in clean_name or "TCG" in clean_name: clean_name = "TRADING CARD GAMES"
            elif "Fumetti" in clean_name or "Manga" in clean_name: clean_name = "FUMETTI & MANGA"
            elif "Action" in clean_name: clean_name = "ACTION FIGURE"
            elif "Gaming" in clean_name: clean_name = "GAMING & CONSOLE"
            elif "Tech" in clean_name: clean_name = "TECH & ELETTRONICA"
            elif "Vinili" in clean_name: clean_name = "VINILI & MEDIA"
            elif "Generalista" in clean_name: clean_name = "GENERALISTA"
            else: clean_name = clean_name.upper()
            
            # 4. SUFFISSO MISTO (Categoria + Generalista)
            # Se la dominanza è bassa (< 30%) e non è già un gruppo MIX
            suffix = ""
            if dominance_perc < 30 and "MIX" not in clean_name: 
                suffix = " (Misto)"
            
            comm_id_str = str(comm_id).zfill(2) 
            label = f"{comm_id_str} - {clean_name}{suffix}"
        else:
            label = f"{comm_id} - Sconosciuto"
            
        community_names[comm_id] = label
        
    # Mapping nomi nel dataframe
    df_nodes['Community_Label'] = df_nodes['Community'].map(community_names)
    
    print("Nomi assegnati. Esempio:")
    print(df_nodes[['Community', 'Community_Label']].drop_duplicates().sort_values('Community').head(10))
    
    return df_nodes
# =========================================================
# 6. CELF ALGORITHM (Influence Maximization)
# =========================================================
def ic_spread_mc(G: nx.DiGraph, seeds: list, prob: float, mc: int) -> float:
    """Monte Carlo simulation per calcolare lo spread di un set di seeds."""
    spread_sum = 0
    for _ in range(mc):
        active = set(seeds)
        newly_active = set(seeds)
        while newly_active:
            next_new = set()
            for node in newly_active:
                for neighbor in G.successors(node):
                    if neighbor not in active:
                        if random.random() <= prob:
                            next_new.add(neighbor)
            newly_active = next_new
            active.update(newly_active)
        spread_sum += len(active)
    return spread_sum / mc

def celf_algorithm(G: nx.DiGraph, k: int, prob: float, mc: int):
   
    print(f"Avvio algoritmo CELF (Target: {k} seeds, Prob: {prob}, MC: {mc})...")
    start_time = time.time()
    
    # 1. Calcola lo spread marginale per ogni nodo
    gains = []
    nodes = list(G.nodes())
    print("CELF: Calcolo spread iniziale per tutti i nodi (può richiedere tempo)...")
    
    # Ottimizzazione: consideriamo solo nodi con out-degree > 0
    candidates = [n for n in nodes if G.out_degree(n) > 0]
    print(f"Candidati validi (out-degree > 0): {len(candidates)}")

    for idx, node in enumerate(candidates):
        if idx % 1000 == 0: print(f"  Analizzati {idx}/{len(candidates)}...")
        spread = ic_spread_mc(G, [node], prob, mc)
        gains.append((spread, node))
    
    gains.sort(reverse=True)
    seeds = [gains[0][1]]
    current_spread = gains[0][0]
    print(f"Seed 1 trovato: {seeds[0]} (Spread: {current_spread:.2f})")
    
    gains = gains[1:]
    
    while len(seeds) < k:
        matched = False
        while not matched and gains:
            current_best_gain, current_best_node = gains[0]
            new_spread = ic_spread_mc(G, seeds + [current_best_node], prob, mc)
            marginal_gain = new_spread - current_spread
            gains.pop(0)
            
            if not gains or marginal_gain >= gains[0][0]:
                seeds.append(current_best_node)
                current_spread = new_spread
                matched = True
                print(f"Seed {len(seeds)} trovato: {current_best_node} (Gain: {marginal_gain:.2f})")
            else:
                gains.append((marginal_gain, current_best_node))
                gains.sort(reverse=True)
    
    end_time = time.time()
    print(f"CELF completato in {end_time - start_time:.2f} secondi.")
    return seeds, current_spread

# =========================================================
# 7. ANALISI INCONGRUENZE
# =========================================================
def run_incongruence_analysis(df_archi: pd.DataFrame, output_dir: str):
    print("Analisi Incongruenze di Rating...")
    df_val = df_archi.copy()
    df_val['Rating_A'] = pd.to_numeric(df_val['Rating_Acquirente_V'], errors='coerce')
    df_val['Rating_V'] = pd.to_numeric(df_val['Rating_Venditore_A'], errors='coerce')
    
    filtro = (df_val['Rating_A'] > 0) & (df_val['Rating_V'] > 0)
    df_validi = df_val[filtro].copy()
    
    if len(df_validi) > 0:
        df_validi['Scarto'] = (df_validi['Rating_A'] - df_validi['Rating_V']).abs()
        df_inc = df_validi[df_validi['Scarto'] >= 2]
        print(f"Trovate {len(df_inc)} incongruenze (scarto >= 2) su {len(df_validi)} coppie valide.")
        df_inc.to_csv(os.path.join(output_dir, "report_incongruenze.csv"), index=False)
    else:
        print("Nessuna coppia di rating valida per l'analisi delle incongruenze.")

# =========================================================
# MAIN
# =========================================================
def main():
    print("="*50)
    print("ASNM FINAL ANALYSIS - VINTED DATASET")
    print("="*50)
    ensure_dir(OUTPUT_DIR)

    # 1. Load
    print(f"Caricamento {INPUT_DATASET}...")
    try:
        df_archi = pd.read_csv(INPUT_DATASET)
    except Exception as e:
        print(e); sys.exit(1)
    G = build_graph(df_archi)

    # 2. Stats & Similarity
    stats = analyze_structure(G)
    with open(os.path.join(OUTPUT_DIR, "report_strutturale.json"), "w") as f:
        json.dump(stats, f, indent=4)

    # 3. Centrality
    df_nodes = calculate_centralities(G, K_CENTRALITY, SEED)
    df_nodes.to_csv(os.path.join(OUTPUT_DIR, "report_centralita.csv"))
    
    # 4. Communities
    partition, mod = run_community_detection(G, SEED)
    df_comm = pd.DataFrame(list(partition.items()), columns=['Node_ID', 'Community'])
    
    # Merge e Naming
    df_nodes = df_nodes.merge(df_comm.set_index('Node_ID'), left_index=True, right_index=True)
    
    df_nodes = naming_communities(df_nodes)
    

    df_comm.to_csv(os.path.join(OUTPUT_DIR, "report_communities.csv"))
    df_nodes.to_csv(os.path.join(OUTPUT_DIR, "report_nodi_completo.csv"))
    print(f"\n Report nodi completo salvato.")


    # 5. Influence Maximization (CELF)
    celf_seeds, celf_spread = celf_algorithm(G, K_SEEDS_CELF, IC_PROBABILITY, IC_MC_SIMULATIONS)
    
    # Confronto Strategie
    print("\nConfronto Strategie IM (Monte Carlo).")
    top_deg = list(df_nodes.nlargest(K_SEEDS_CELF, 'out_degree').index)
    top_pr = list(df_nodes.nlargest(K_SEEDS_CELF, 'pagerank').index)
    
    spread_deg = ic_spread_mc(G, top_deg, IC_PROBABILITY, IC_MC_SIMULATIONS)
    spread_pr = ic_spread_mc(G, top_pr, IC_PROBABILITY, IC_MC_SIMULATIONS)
    
    im_results = [
        {"Strategy": "CELF (Greedy Approx)", "Seeds": celf_seeds, "Spread": celf_spread},
        {"Strategy": "Top Out-Degree (Hubs)", "Seeds": top_deg, "Spread": spread_deg},
        {"Strategy": "Top PageRank (Authority)", "Seeds": top_pr, "Spread": spread_pr}
    ]
    pd.DataFrame(im_results).to_csv(os.path.join(OUTPUT_DIR, "report_influence_maximization.csv"), index=False)
    print(pd.DataFrame(im_results))

    # 6. Incongruenze
    run_incongruence_analysis(df_archi, OUTPUT_DIR)

    # 7. Export GEXF 
    print("\nSalvataggio GEXF...")
    for col in df_nodes.columns:
        if col not in ['main_tag', 'detailed_tag']: # Evitiamo duplicati se già presenti
            nx.set_node_attributes(G, df_nodes[col].to_dict(), name=col)
            
    nx.write_gexf(G, OUTPUT_GRAPH_FILE)

    print("\n" + "="*50)
    print("ANALISI COMPLETATA.")
    print("="*50)

if __name__ == "__main__":
    main()
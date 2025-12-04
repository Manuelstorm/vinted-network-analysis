import pandas as pd
import numpy as np # Ci servirà per la logica dei SEED

# =========================================================
# CONFIG
# =========================================================
TRANSACTIONS_FILE = "vinted_raw_transactions.csv"
TAGS_FILE = "vinted_user_tags.csv"
OUTPUT_DATASET = "vinted_dataset_PULITO.csv" 


SEED_USER_IDS: set[int] = {
    263549027, 51137088, 149109512, 142839912, 270173606, 79807304, 87684939,
    86638253, 90996890, 76860837, 71154112, 51836926, 138224980, 53097946,
    258966455, 123565366, 171025810, 106056510, 90011251, 96521935, 232131254,
    92240514, 72650307, 249994384, 86438122, 58202410, 31726329, 163790130,
    198014289, 162622596, 55075827, 112098349, 55505444, 144825509, 128493984,
    199833914, 48984054, 285214071, 123425585, 112014531, 59225322, 26492910,
    268184008, 118549662, 156897851, 119607451, 70832706, 225927726, 253598187,
    83018858, 268275676, 78144829, 287685180, 52902518, 237920137, 153549920,
    151153734, 276534491, 81014300, 8611252, 50889513, 57313689, 149432253,
    78765681, 116795571, 176647074, 240631879, 50714517, 166404963, 185432581,
    113844804, 242358895, 273563210, 49418268, 49757359, 73811740, 292205078,
    231528986, 128897593, 147025135, 55125380
}

# =========================================================
# LOAD
# =========================================================
print("Caricamento file...")
try:
    df_tx = pd.read_csv(TRANSACTIONS_FILE)
    df_tags = pd.read_csv(TAGS_FILE)
except Exception as e:
    print(f"Errore caricamento file: {e}")
    exit()

print(f"File caricati. Transazioni totali (grezze): {len(df_tx)} | Tag utenti totali: {len(df_tags)}")

# =========================================================
# NORMALIZZAZIONE E PULIZIA ID 
# =========================================================
print("Normalizzazione ID...")
for col in ["Acquirente_ID", "Venditore_ID"]:
    df_tx[col] = pd.to_numeric(df_tx[col], errors="coerce")
df_tags["Node_ID"] = pd.to_numeric(df_tags["Node_ID"], errors="coerce")


df_tx = df_tx.dropna(subset=["Acquirente_ID", "Venditore_ID"])
df_tags = df_tags.dropna(subset=["Node_ID"])

df_tags["Node_ID"] = df_tags["Node_ID"].astype(int)

# =========================================================
# FILTRAGGIO NODI 
# =========================================================
print("Inizio filtraggio nodi (Strategia 'Deadline')...")

# 1. I SEED sono immuni alla rimozione
filtro_seed = df_tags["Node_ID"].isin(SEED_USER_IDS) 

# 2. Drop

# Filtro 1: (Inattivo, Inattivo)
filtro_inattivo = (df_tags["Main_Tag"] == "Inattivo")

# Filtro 2: (Generalista, Generalista_Puro)
filtro_puro = (df_tags["Detailed_Tag"] == "Generalista_Puro")


# Filtro 3: (Generalista, Generalista) 
filtro_vecchio_ambiguo = (
    (df_tags["Main_Tag"] == "Generalista") & 
    (df_tags["Detailed_Tag"] == "Generalista")
)

filtro_drop_totale = (filtro_inattivo | filtro_puro | filtro_vecchio_ambiguo)

# Droppa un nodo se è un tag da droppare e NON è un SEED)
nodi_da_droppare = df_tags[ filtro_drop_totale & (~filtro_seed) ]
nodi_da_tenere_df = df_tags.drop(nodi_da_droppare.index)

# Creiamo un SET degli ID che teniamo. 
nodi_da_tenere_set = set(nodi_da_tenere_df["Node_ID"])

print(f"Filtraggio Nodi completato.")
print(f"Nodi totali: {len(df_tags)}")
print(f"Nodi droppati (Rumore + Inattivi): {len(nodi_da_droppare)}")
print(f"Nodi tenuti (per il grafo): {len(nodi_da_tenere_set)}")


# =========================================================
# FILTRAGGIO TRANSAZIONI 
# =========================================================
print("Filtraggio transazioni (tengo solo quelle tra nodi validi)...")


filtro_acquirente = df_tx["Acquirente_ID"].isin(nodi_da_tenere_set)
filtro_venditore = df_tx["Venditore_ID"].isin(nodi_da_tenere_set)

df_tx_filtrate = df_tx[filtro_acquirente & filtro_venditore].copy() 

print(f"Transazioni filtrate: {len(df_tx_filtrate)} (da {len(df_tx)} iniziali)")

# =========================================================
# MERGE TAG UTENTI 
# =========================================================
print("Eseguo il merge finale...")

# Ora usiamo i DataFrame FILTRATI 
df_tags_buyer = nodi_da_tenere_df.rename(columns={
    "Node_ID": "Acquirente_ID",
    "Main_Tag": "Main_Tag_Acquirente",
    "Detailed_Tag": "Detailed_Tag_Acquirente"
})

df_tags_seller = nodi_da_tenere_df.rename(columns={
    "Node_ID": "Venditore_ID",
    "Main_Tag": "Main_Tag_Venditore",
    "Detailed_Tag": "Detailed_Tag_Venditore"
})

df_merged = (
    df_tx_filtrate
    .merge(df_tags_buyer, on="Acquirente_ID", how="left")
    .merge(df_tags_seller, on="Venditore_ID", how="left")
)

# =========================================================
# METRICHE BASE 
# =========================================================
print("Calcolo metriche base...")
df_merged["Rating_Acquirente_V"] = pd.to_numeric(df_merged["Rating_Acquirente_V"], errors="coerce")
df_merged["Rating_Venditore_A"] = pd.to_numeric(df_merged["Rating_Venditore_A"], errors="coerce")

df_merged["Rating_Medio"] = df_merged[["Rating_Acquirente_V", "Rating_Venditore_A"]].mean(axis=1)

# Conteggio delle transazioni per coppia 
df_counts = (
    df_merged.groupby(["Acquirente_ID", "Venditore_ID"])
    .size()
    .reset_index(name="Numero_Transazioni")
)
df_merged = df_merged.merge(df_counts, on=["Acquirente_ID", "Venditore_ID"], how="left")

# =========================================================
# SALVATAGGIO DATASET 
# =========================================================
df_merged.to_csv(OUTPUT_DATASET, index=False, encoding="utf-8")
print("\n" + "="*50)
print(f"Fatto! Dataset PULITO salvato in: {OUTPUT_DATASET}")
print(f"Righe finali (transazioni nel grafo): {len(df_merged)}")
print(f"Nodi unici nel grafo: {len(nodi_da_tenere_set)}")
print("="*50)
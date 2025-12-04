import time
import json
import re
import random
import os
from typing import Dict, Any, List, Set, Tuple
import sys

HAS_RESTARTED = False  # flag per evitare restart infiniti

# API Vinted 
from vinted import Vinted

# Import modelli 
from vinted.models.users import UserFeedbacksResponse
from vinted.models.items import UserItemsResponse, DetailedItem
from vinted.models.search import SearchResponse

import pandas as pd

# ========================================================================
# CONFIGURAZIONE
# ========================================================================

#Cookie di sessione
RAW_COOKIE_STRING = "Z3NPQ3RhVWlQR250UHdkblUrbGxGWk42QzdvMHc1WFBERkhFbTFNeDdFZGNncVBOYS9zMHRXUWFHd0FYeDZtS3BRaUJoK0h3c0NNVW96VEsrN0FjbUQ5S01DSThDSmJzTzNDUmpuTkovSmdpSXpPdWNCNVJwSXpVYWE2S0FHY2JUQ296Zzh5RExDK2dhRkFzTkRzZG5MYmFwTjRTeHpYYU82WFNVeWVGL0hDVm5SZGVBQTJveTJQVmdkTDhKZFRycEZaZm0vS3BnNmRzY3pyTXdSQzVxaUkrTm1xMzZFUHpTNnBBTUxsTkJLWldKMG02MEo3TnZGN2JubHYxZHJNZC0tU29ndmxIaXNsOVFnbWxLWkp3WGlLdz09--524cb072dbb53d99ba5df62d1da8d6d5b3616a20; banners_ui_state=SUCCESS; _ga_KVH0QH2Q98=GS2.1.s1762257510$o3$g1$t1762257544$j26$l0$h0; _ga_ZJHK1N3D75=GS2.1.s1762257510$o3$g1$t1762257544$j26$l0$h0;"

SEED_MIN_SLEEP = 8
SEED_MAX_SLEEP = 16
TAG_MIN_SLEEP = 7
TAG_MAX_SLEEP = 12

SEED_USER_IDS: List[int] = [263549027, 51137088,149109512, 142839912, 270173606,
                            79807304, 87684939, 86638253, 90996890, 76860837,
                            71154112,51836926, 138224980, 53097946, 258966455,
                            123565366, 171025810, 106056510, 90011251, 96521935,
                            232131254,92240514,72650307, 249994384, 86438122,
                            58202410, 31726329,163790130, 198014289, 162622596,
                            55075827,112098349, 55505444, 144825509, 128493984,
                            199833914, 48984054, 285214071,  123425585,  112014531,
                            59225322, 26492910, 268184008,118549662,
                            156897851, 119607451, 70832706, 225927726,253598187,
                            83018858, 268275676, 78144829, 287685180,  52902518,
                            237920137, 153549920, 151153734, 276534491, 81014300,
                            8611252, 50889513, 57313689, 149432253, 78765681,
                            116795571, 176647074, 240631879, 50714517, 166404963,
                            185432581, 113844804, 242358895, 273563210, 49418268,
                            49757359, 73811740,292205078, 231528986, 128897593, 147025135, 55125380]

FILE_NAME = "vinted_raw_transactions.csv"
TAGS_FILE_NAME = "vinted_user_tags.csv"

# ========================================================================
# UTILITY
# ========================================================================

def convert_cookie_string_to_dict(cookie_string: str) -> Dict[str, str]:

    cookies_dict: Dict[str, str] = {}
    if not cookie_string:
        return cookies_dict
    # rimuovi eventuale ; finale
    cookie_string = cookie_string.strip().rstrip(';')
    pairs = cookie_string.split(';')
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        if '=' in pair:
            key, value = pair.split('=', 1)
            cookies_dict[key.strip()] = value.strip()
    return cookies_dict

# ========================================================================
# FUNZIONE DI TAGGING 
# ========================================================================

def assign_community_tag(item_titles_list: List[str]) -> Tuple[str, str]:

    
    MIN_ABS_FOR_DOMINANT = 3
    MULTICATEGORY_RATIO = 0.4
    MULTICATEGORY_MIN_ABS = 2
    MIN_TOTAL_MATCHES = 4

    if not item_titles_list:
        return "Inattivo", "Inattivo"

    # --- Inizializzo conteggi ---
    counts = {
        "Carte_TCG": 0, "Fumetti_Manga": 0, "Action_Figure": 0, "Gaming_Console": 0,
        "Tech_Elettronica": 0, "Moda_Lusso": 0, "Media_Vinili": 0,
        "Generalista": 0, "Abbigliamento/Generico": 0
    }

    keyword_map = {
        # Carte e TCG
        "pokemon": "Carte_TCG", "lorcana": "Carte_TCG", "tcg": "Carte_TCG", "yu gi oh": "Carte_TCG",
        # Fumetti / Manga
        "fumetto": "Fumetti_Manga", "topolino": "Fumetti_Manga", "manga": "Fumetti_Manga",
        "onepiece": "Fumetti_Manga", "dragon ball": "Fumetti_Manga",
        # Action Figure / Pop Culture
        "funko": "Action_Figure", "pop": "Action_Figure", "action figure": "Action_Figure",
        "star wars": "Action_Figure", "harry potter": "Action_Figure", "lego": "Action_Figure",
         "giochi da tavolo": "Action_Figure", "disney": "Action_Figure",
        # Gaming / Console
        "playstation": "Gaming_Console", "nintendo": "Gaming_Console", "switch": "Gaming_Console",
        "xbox": "Gaming_Console", "game boy": "Gaming_Console", "ds": "Gaming_Console",
        # Tech / Elettronica
        "apple": "Tech_Elettronica", "samsung": "Tech_Elettronica", "xiaomi": "Tech_Elettronica",
        "huawei": "Tech_Elettronica", "microsoft": "Tech_Elettronica",
        # Moda / Lusso
        "gucci": "Moda_Lusso", "prada": "Moda_Lusso", "dior": "Moda_Lusso", "fendi": "Moda_Lusso",
        "chanel": "Moda_Lusso", "cartier": "Moda_Lusso", "nike": "Moda_Lusso", "adidas": "Moda_Lusso",
        # Media
        "vinile": "Media_Vinili", "cd": "Media_Vinili",
        # Generico
        "profumo": "Generalista", "ikea": "Generalista", "thun": "Generalista", "sport": "Generalista",
    }

    total_items_tagged = 0

    for title in item_titles_list:
        if not isinstance(title, str) or not title.strip():
            continue

        title_low = title.lower()
        title_clean = re.sub(r"[^a-z0-9\sàèéìíòóùúäëïöüçñ-]", " ", title_low)
        title_clean = re.sub(r"\s+", " ", title_clean).strip()

        tag_found = False
        for keyword, tag in keyword_map.items():
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, title_clean):
                counts[tag] += 1
                tag_found = True
                break
        if not tag_found:
            counts["Abbigliamento/Generico"] += 1

        total_items_tagged += 1

    if total_items_tagged == 0:
        return "Inattivo", "Inattivo"

    # --- Analisi dei conteggi reali ---
    interesting_counts = {
        k: v for k, v in counts.items()
        if k not in ["Abbigliamento/Generico", "Generalista"] and v > 0
    }

    # 1. GENERALISTA PURO
    # Se non c'è NULLA di interessante (zero keyword di nicchia)
    # O se ha venduto troppo poco in totale (es. < 4 item)
    if not interesting_counts or total_items_tagged < MIN_TOTAL_MATCHES:
        return "Generalista", "Generalista_Puro"

    # Se c'è qualcosa di interessante, ordiniamo
    sorted_counts = sorted(interesting_counts.items(), key=lambda item: item[1], reverse=True)
    dominant_tag, dominant_count = sorted_counts[0]
    second_dominant_tag, second_dominant_count = (sorted_counts[1] if len(sorted_counts) > 1 else ("Nessuno", 0))

    # 2. GENERALISTA SOTTOSOGLIA 
    # Ha keyword di nicchia, ma troppo poche (es. 1-2 Funko)
    if dominant_count < MIN_ABS_FOR_DOMINANT:
        # Lo tagghiamo come Generalista, ma specificando la sua nicchia debole
        return "Generalista", f"Debole_{dominant_tag}"

    # 3. NICCHIA VERA 
    # Regola Multi Category
    if second_dominant_count >= MULTICATEGORY_MIN_ABS and (second_dominant_count / dominant_count) >= MULTICATEGORY_RATIO:
        return "Multi_category", f"Multi_category_{dominant_tag}_{second_dominant_tag}"
    else:
        return dominant_tag, f"Puro_{dominant_tag}"

# ========================================================================
# FUNZIONE DI RICERCA SEED 
# ========================================================================

INTEREST_QUERIES = [
    "Funko Pop", "Pokémon", "Pokémon TCG", "Fumetti Topolino", "Manga", "OnePiece",
    "Dragon Ball",  "Giochi da tavolo", "Lorcana TCG", "Lego",
    "Action figure", "Vinile", "Disney", "Yu-Gi-Oh!", "Star Wars", "Harry Potter",
    "Playstation", "Nintendo Switch", "Nintendo DS", "Game Boy", "Xbox", "Apple",
    "Samsung", "Xiaomi", "Huawei", "Microsoft", "Nike", "Adidas", "Cartier",
    "Gucci", "Prada", "Dior", "Fendi", "Chanel", "Thun", "Profumi", "Ikea", "Sport",
]

def find_ids_from_raw_json(query_text: str) -> List[int]:
 
    CUSTOM_COOKIES_DICT = convert_cookie_string_to_dict(RAW_COOKIE_STRING)
    vinted = Vinted(domain="it")
    try:
        vinted.update_cookies(CUSTOM_COOKIES_DICT)
    except Exception:
        try:
            vinted.cookies = CUSTOM_COOKIES_DICT
        except Exception:
            pass

    url = f"https://www.vinted.it/api/v2/catalog/items?page=1&per_page=5&search_text={query_text.replace(' ', '+')}"
    print(f"Cerco PRODOTTI (via URL grezzo) per query: '{query_text}'...")

    try:
        response = vinted.scraper.get(url, headers=getattr(vinted, "headers", {}), cookies=getattr(vinted, "cookies", {}), proxies=getattr(vinted, "proxy", None))
        response.raise_for_status()
        raw_json_data = response.json()

        real_seed_ids = []
        if 'items' in raw_json_data and raw_json_data['items']:
            print(f"Trovati {len(raw_json_data['items'])} prodotti. ID Venditori:")
            for item in raw_json_data['items']:
                user = item.get('user') or {}
                vendor_id = user.get('id')
                vendor_login = user.get('login', '<no-login>')
                if vendor_id and vendor_id not in real_seed_ids:
                    print(f"  - Login: {vendor_login}, ID: {vendor_id}")
                    real_seed_ids.append(vendor_id)
            return real_seed_ids
        else:
            print("Nessun prodotto trovato nel JSON grezzo.")
            return []

    except Exception as e:
        print(f"ERRORE GRAVE nella ricerca grezza: {e}")
        return []

# ========================================================================
# SALVATAGGIO INCREMENTALE
# ========================================================================

def save_progress(feedback_list: List[Dict[str, Any]], main_tags_dict: Dict[int, str], detailed_tags_dict: Dict[int, str]):
    """
    Salva i dati raccolti (archi e proprietà dei nodi) in file CSV.
    Protegge contro DataFrame vuoti, tipi non numerici, duplicati.
    """
    try:
        if not feedback_list:
            print("AVVISO: Nessun dato di feedback da salvare.")
            return

        print(f"\n--- SALVATAGGIO INCREMENTALE IN CORSO ({len(feedback_list)} transazioni) ---")

        # --- 1. Salvataggio Transazioni (Archi) ---
        df_transactions = pd.DataFrame(feedback_list)

        if 'Acquirente_ID' in df_transactions.columns:
            df_transactions['Acquirente_ID'] = pd.to_numeric(df_transactions['Acquirente_ID'], errors='coerce')
        if 'Venditore_ID' in df_transactions.columns:
            df_transactions['Venditore_ID'] = pd.to_numeric(df_transactions['Venditore_ID'], errors='coerce')

        # Mappatura dei tag ai dati di transazione (basata sui tag raccolti finora)
        if 'Acquirente_ID' in df_transactions.columns:
            df_transactions['Acquirente_Community'] = df_transactions['Acquirente_ID'].map(main_tags_dict).fillna('Sconosciuto')
        if 'Venditore_ID' in df_transactions.columns:
            df_transactions['Venditore_Community'] = df_transactions['Venditore_ID'].map(main_tags_dict).fillna('Sconosciuto')

        # Rimuovo duplicati 
        if {'Acquirente_ID', 'Venditore_ID', 'Item_ID'}.issubset(df_transactions.columns):
            df_transactions.drop_duplicates(subset=['Acquirente_ID', 'Venditore_ID', 'Item_ID'], inplace=True, keep='last')

        df_transactions.to_csv(FILE_NAME, index=False, encoding='utf-8')
        print(f" Dati transazioni salvati in: {FILE_NAME} ({len(df_transactions)} righe)")

        # --- 2. Salvataggio Tag (Proprietà Nodi) ---
        df_main_tags = pd.DataFrame(list(main_tags_dict.items()), columns=['Node_ID', 'Main_Tag'])
        df_detailed_tags = pd.DataFrame(list(detailed_tags_dict.items()), columns=['Node_ID', 'Detailed_Tag'])

        df_tags = pd.merge(df_main_tags, df_detailed_tags, on='Node_ID', how='outer')

        df_tags.to_csv(TAGS_FILE_NAME, index=False, encoding='utf-8')
        print(f" Dati tag salvati in: {TAGS_FILE_NAME} ({len(df_tags)} utenti)")

    except Exception as e:
        print(f"ERRORE durante il salvataggio incrementale: {e}")

# ========================================================================
# FUNZIONE DI SCRAPING
# ========================================================================

def scrape_data():

    global HAS_RESTARTED
    CUSTOM_COOKIES_DICT = convert_cookie_string_to_dict(RAW_COOKIE_STRING)
    vinted = Vinted(domain="it")
    try:
        vinted.update_cookies(CUSTOM_COOKIES_DICT)
    except Exception:
        try:
            vinted.cookies = CUSTOM_COOKIES_DICT
        except Exception:
            pass

    print("Autenticazione impostata (controlla il cookie). Inizio Crawling...")

    seed_users_list = SEED_USER_IDS.copy()
    all_users_in_network: Set[int] = set(seed_users_list)
    all_feedback_data: List[Dict[str, Any]] = []

    # Dizionari per i tag 
    user_main_tags: Dict[int, str] = {}
    user_detailed_tags: Dict[int, str] = {}

    # FASE 1: CARICAMENTO DATI VECCHI PER RESTART
    if os.path.exists(FILE_NAME):
        print("--- CARICAMENTO DATI PRECEDENTI ---")
        try:
            df_old = pd.read_csv(FILE_NAME)
            all_feedback_data = df_old.to_dict('records')
            if 'Acquirente_ID' in df_old.columns:
                all_users_in_network.update(pd.to_numeric(df_old['Acquirente_ID'], errors='coerce').dropna().astype(int).unique())
            if 'Venditore_ID' in df_old.columns:
                all_users_in_network.update(pd.to_numeric(df_old['Venditore_ID'], errors='coerce').dropna().astype(int).unique())
            print(f"Caricate {len(all_feedback_data)} transazioni e {len(all_users_in_network)} utenti totali.")
        except Exception as e:
            print(f"Errore caricamento {FILE_NAME}: {e}. Inizio da zero.")
            all_feedback_data = []

    if os.path.exists(TAGS_FILE_NAME):
        try:
            df_tags_old = pd.read_csv(TAGS_FILE_NAME)
            if 'Node_ID' in df_tags_old.columns and 'Main_Tag' in df_tags_old.columns:
                user_main_tags = dict(zip(pd.to_numeric(df_tags_old['Node_ID'], errors='coerce').dropna().astype(int), df_tags_old['Main_Tag']))
            if 'Node_ID' in df_tags_old.columns and 'Detailed_Tag' in df_tags_old.columns:
                user_detailed_tags = dict(zip(pd.to_numeric(df_tags_old['Node_ID'], errors='coerce').dropna().astype(int), df_tags_old['Detailed_Tag']))
            print(f"Caricati {len(user_main_tags)} tag utente.")
        except Exception as e:
            print(f"Errore caricamento {TAGS_FILE_NAME}: {e}. Inizio da zero.")
            user_main_tags = {}
            user_detailed_tags = {}

    print("-----------------------------------")

    try:
        # =============================================================
        # FASE 2: ACQUISIZIONE ARCHI (Solo dai SEED)
        # =============================================================
        print(f"Inizio Fase 2: Acquisizione Archi da {len(seed_users_list)} SEED...")

        for current_user_id in seed_users_list:
            '''
            if current_user_id in user_main_tags:  # Usiamo i tag come proxy per "già processato"
                print(f"\nUtente SEED {current_user_id} già processato. Salto.")
                continue
            '''
            if current_user_id in user_main_tags:
                # Se era taggato come 'Inattivo', forziamo il retagging
                if user_main_tags[current_user_id] == "Inattivo":
                    print(f"\nUtente SEED {current_user_id} era Inattivo: forzo retagging.")
                else:
                    print(f"\nUtente SEED {current_user_id} già processato ({user_main_tags[current_user_id]}). Salto.")
                continue

            print(f"\nAnalizzo SEED ID: {current_user_id}")
            item_titles_for_tagging: List[str] = []

            try:
                page = 1
                while True:
                    url_feedback = f"{vinted.api_url}/user_feedbacks?user_id={current_user_id}&page={page}&per_page=20&by=all"
                    response = vinted.scraper.get(url_feedback,
                                                  headers=getattr(vinted, "headers", {}),
                                                  cookies=getattr(vinted, "cookies", {}),
                                                  proxies=getattr(vinted, "proxy", None))
                    response.raise_for_status()
                    raw_json_data = response.json()

                    if 'user_feedbacks' not in raw_json_data or not raw_json_data['user_feedbacks']:
                        print(f" -> Nessun feedback trovato per {current_user_id} a pagina {page}. Interrompo.")
                        break

                    for feedback in raw_json_data['user_feedbacks']:
                        item_title = feedback.get('item_title') or ""
                        item_titles_for_tagging.append(item_title)

                        data_row = {
                            "Acquirente_ID": feedback.get('feedback_user_id'),
                            "Venditore_ID": feedback.get('user_id'),
                            "Rating_Acquirente_V": feedback.get('rating'),
                            "Rating_Venditore_A": None,
                            "Item_ID": feedback.get('item_id'),
                        }
                        all_feedback_data.append(data_row)

                        # Aggiorno il set degli utenti 
                        try:
                            if data_row["Acquirente_ID"] is not None:
                                all_users_in_network.add(int(data_row["Acquirente_ID"]))
                        except Exception:
                            pass
                        try:
                            if data_row["Venditore_ID"] is not None:
                                all_users_in_network.add(int(data_row["Venditore_ID"]))
                        except Exception:
                            pass

                    pagination = raw_json_data.get('pagination')
                    if not pagination or pagination.get('current_page', page) >= pagination.get('total_pages', page):
                        break

                    page += 1
                    sleep_duration = random.randint(SEED_MIN_SLEEP, SEED_MAX_SLEEP)
                    print(f" -> Pausa di {sleep_duration}s tra le pagine di feedback (fase SEED)...")
                    time.sleep(sleep_duration)


                # Assegniamo i 2 tag al SEED 
                main_tag, detailed_tag = assign_community_tag(item_titles_for_tagging)
                user_main_tags[current_user_id] = main_tag
                user_detailed_tags[current_user_id] = detailed_tag
                print(f" -> Tag Assegnati al SEED: Main='{main_tag}', Detailed='{detailed_tag}'")

            except Exception as e:
                print(f"ERRORE durante lo scraping di {current_user_id}: {e}")
                if "403" in str(e):
                    print("!!! BLOCCO 403 RILEVATO. SALVATAGGIO IN CORSO... !!!")
                    save_progress(all_feedback_data, user_main_tags, user_detailed_tags)
                    break

            # Salvataggio incrementale (dopo ogni SEED)
            save_progress(all_feedback_data, user_main_tags, user_detailed_tags)

            sleep_duration = random.randint(SEED_MIN_SLEEP, SEED_MAX_SLEEP)
            print(f"PAUSA di {sleep_duration}s tra i SEED (fase SEED)...")
            time.sleep(sleep_duration)
        # =============================================================
        # FASE 3: ACQUISIZIONE TAGGING 
        # =============================================================
        print(f"\n--- Inizio Fase 3: Tagging di {len(all_users_in_network)} nodi totali ---")

        # --- SISTEMA DI RESUME ---
        TAG_SAVE_EVERY = 10
        FORZA_RETAGGING = False  

        # Carica i tag già esistenti
        done_tags = {}
        if os.path.exists(TAGS_FILE_NAME):
            try:
                with open(TAGS_FILE_NAME, "r", encoding="utf-8") as f:
                    next(f)
                    for line in f:
                        try:
                            node_id, main_tag, detailed_tag = line.strip().split(",")
                            done_tags[int(node_id)] = (main_tag, detailed_tag)
                        except:
                            continue
                print(f" Resume attivo: trovati {len(done_tags)} utenti già taggati.")
            except Exception as e:
                print(f" Errore lettura file tag per resume: {e}")
        else:
            print(" Nessun file tag precedente trovato. Parto da zero.")

        # Costruisci la lista dei nodi da taggare
        nodes_to_tag = []
        for uid in all_users_in_network:
            if uid is None:
                continue
            if not FORZA_RETAGGING and uid in done_tags:
                continue
            nodes_to_tag.append(uid)

        print(f" Totale utenti da taggare in questo run: {len(nodes_to_tag)}")
      
 
        # FASE DI RECUPERO: se esistono utenti Inattivi, ritaggiamo solo quelli

        retry_inactive_only = False  # imposta False se vuoi rifare tutto
        if retry_inactive_only:
            try:
                df_tags = pd.read_csv(TAGS_FILE_NAME)
                if 'Node_ID' in df_tags.columns and 'Main_Tag' in df_tags.columns:
                    inactive_users = (
                        df_tags[df_tags['Main_Tag'].astype(str).str.strip().str.lower() == "inattivo"]
                        ['Node_ID']
                        .dropna()
                        .astype(int)
                        .tolist()
                    )
                    if inactive_users:
                        print(f" Modalità RECUPERO ATTIVA → {len(inactive_users)} utenti 'Inattivo' verranno ritaggati.")
                        nodes_to_tag = inactive_users  # sovrascrive la lista da processare
                    else:
                        print(" Nessun utente 'Inattivo' trovato. Procedo normalmente.")
                else:
                    print(" File tag privo di colonne attese ('Node_ID', 'Main_Tag'). Procedo normalmente.")
            except Exception as e:
                print(f"Errore durante il caricamento utenti inattivi: {e}")

        # --- CICLO DI TAGGING ---
        
        print(f"Nodi già taggati: {len(user_main_tags)}. Nodi da taggare: {len(nodes_to_tag)}")

        save_counter_fase3 = 0  # Contatore per salvataggio incrementale Fase 3

        for i, user_id in enumerate(nodes_to_tag):
            print(f"\nTagging Utente {i+1}/{len(nodes_to_tag)} (ID: {user_id})")

            item_titles_for_tagging: List[str] = []

            try:
                # USIAMO I FEEDBACK PER IL TAGGING 
                page = 1
                while True:
                    url_feedback = f"{vinted.api_url}/user_feedbacks?user_id={user_id}&page={page}&per_page=20&by=all"
                    response = vinted.scraper.get(url_feedback,
                                                  headers=getattr(vinted, "headers", {}),
                                                  cookies=getattr(vinted, "cookies", {}),
                                                  proxies=getattr(vinted, "proxy", None))
                    response.raise_for_status()
                    raw_json_data = response.json()

                    if 'user_feedbacks' not in raw_json_data or not raw_json_data['user_feedbacks']:
                        break  # Nessun feedback trovato

                    for feedback in raw_json_data['user_feedbacks']:
                        item_title = feedback.get('item_title') or ""
                        item_titles_for_tagging.append(item_title)

                    pagination = raw_json_data.get('pagination')

                    # Limitiamo il tagging alle prime 3 pagine (60 feedback) per velocità
                    if not pagination or pagination.get('current_page', page) >= pagination.get('total_pages', page) or page >= 3:
                        break

                    page += 1
                    time.sleep(random.randint(5, 10))  # Pausa breve tra le pagine

                # Assegniamo i tag
                main_tag, detailed_tag = assign_community_tag(item_titles_for_tagging)
                user_main_tags[user_id] = main_tag
                user_detailed_tags[user_id] = detailed_tag
                print(f" -> Tag Assegnati: Main='{main_tag}', Detailed='{detailed_tag}'")

            except Exception as e:
                err_str = str(e)
                print(f"Errore durante il tagging di {user_id}: {err_str}")

                # Se troviamo un 401, proviamo un riavvio controllato UNA SOLA VOLTA
                if ("401" in err_str or "Unauthorized" in err_str) and not HAS_RESTARTED:
                    print("Errore 401 rilevato — probabile cookie scaduto o sessione invalidata.")
                    print("Riavvio automatico del programma tra 10 secondi...")

                    # Segna che ci siamo già riavviati una volta
                    HAS_RESTARTED = True

                    # Salva lo stato parziale prima di riavviare
                    save_progress(all_feedback_data, user_main_tags, user_detailed_tags)
                    time.sleep(10)

                    # Riavvia lo script con gli stessi argomenti
                    os.execv(sys.executable, [sys.executable] + sys.argv)

                else:
                    # Tutti gli altri errori o 401 successivi → marcare come Inattivo
                    user_main_tags[user_id] = "Inattivo"
                    user_detailed_tags[user_id] = "Inattivo"
                    print(f" Errore gestito su {user_id}: marcato come 'Inattivo'.")


            save_counter_fase3 += 1
            # Salvataggio incrementale dei TAG 
            if save_counter_fase3 % 10 == 0:
                save_progress(all_feedback_data, user_main_tags, user_detailed_tags)

            sleep_duration = random.randint(TAG_MIN_SLEEP, TAG_MAX_SLEEP)
            print(f"PAUSA di {sleep_duration}s tra il tagging (fase TAG)...")
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        print("\nInterruzione manuale rilevata (Ctrl+C). Salvataggio...")

    finally:
        # BLOCCO SALVATAGGIO (FINALE)
        save_progress(all_feedback_data, user_main_tags, user_detailed_tags)
        print("Salvataggio finale completato.")
    # ===========================================================
    # SALVATAGGIO FINALE DOPO RITAGGING INATTIVI
    # ===========================================================
    try:
        print("\n Salvataggio finale dopo ritagging inattivi...")
        save_progress(all_feedback_data, user_main_tags, user_detailed_tags)
        print(f" Dati tag aggiornati: {len(user_main_tags)} utenti totali salvati.")
    except Exception as e:
        print(f" Errore durante il salvataggio finale dei tag aggiornati: {e}")

# ==============================================================================
# SEZIONE DI ESECUZIONE
# ==============================================================================
if __name__ == "__main__":
    '''
    #  RACCOLTA AUTOMATICA SEED 
    # ---------------------------------------------------------------
    # Questa porzione di codice viene usata per generare automaticamente una lista di
    # seed user ID cercando per query (es. "Funko Pop", "Pokémon", ecc.)
    #
    #
    found_ids = []
    for query in INTEREST_QUERIES:
        ids = find_ids_from_raw_json(query)  # <--- Usa la funzione per cercare ID venditori
        found_ids.extend(ids)
        time.sleep(1)
    
    print("\n" + "="*50)
    print(f"ID UTENTI RACCOLTI TOTALI (da usare come SEED): {found_ids}")
    # Gli ID stamapti a schermo vengono usati per popolare la variabile SEED_USER_IDS, ma vanno controllati manualmente.
    '''

    # ESECUZIONE DELLO SCRAPING PRINCIPALE
    # ---------------------------------------------------------------
    # Dopo aver aggiornato SEED_USER_IDS manualmente con gli ID scelti,
    # possiamo lanciare lo scraping per raccogliere dati e tag.
    scrape_data()

import time
import json
import re
import random
import os
from typing import Dict, Any, List, Set, Tuple
import sys
import pandas as pd
import numpy as np
from vinted import Vinted

# ========================================================================
# CONFIGURAZIONE
# ========================================================================


RAW_COOKIE_STRING = "Z3NPQ3RhVWlQR250UHdkblUrbGxGWk42QzdvMHc1WFBERkhFbTFNeDdFZGNncVBOYS9zMHRXUWFHd0FYeDZtS3BRaUJoK0h3c0NNVW96VEsrN0FjbUQ5S01DSThDSmJzTzNDUmpuTkovSmdpSXpPdWNCNVJwSXpVYWE2S0FHY2JUQ296Zzh5RExDK2dhRkFzTkRzZG5MYmFwTjRTeHpYYU82WFNVeWVGL0hDVm5SZGVBQTJveTJQVmdkTDhKZFRycEZaZm0vS3BnNmRzY3pyTXdSQzVxaUkrTm1xMzZFUHpTNnBBTUxsTkJLWldKMG02MEo3TnZGN2JubHYxZHJNZC0tU29ndmxIaXNsOVFnbWxLWkp3WGlLdz09--524cb072dbb53d99ba5df62d1da8d6d5b3616a20; banners_ui_state=SUCCESS; _ga_KVH0QH2Q98=GS2.1.s1762257510$o3$g1$t1762257544$j26$l0$h0; _ga_ZJHK1N3D75=GS2.1.s1762257510$o3$g1$t1762257544$j26$l0$h0;"


INPUT_DATASET = "vinted_dataset_PULITO.csv"
OUTPUT_DATASET = "vinted_dataset_FINAL.csv"

MIN_SLEEP = 3
MAX_SLEEP = 6
SAVE_EVERY = 10 
HAS_RESTARTED = False 

# ========================================================================
# UTILITY 
# ========================================================================

def convert_cookie_string_to_dict(cookie_string: str) -> Dict[str, str]:
    cookies_dict: Dict[str, str] = {}
    if not cookie_string:
        return cookies_dict
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
# FUNZIONE PER COUNTER REVIEW
# ========================================================================

def find_counter_review(vinted_client: Vinted, buyer_id: int, seller_id: int) -> int | None:
    
    page = 1
    
    while True:
        try: 
            url_feedback = f"{vinted_client.api_url}/user_feedbacks?user_id={buyer_id}&page={page}&per_page=20&by=all"
            
            response = vinted_client.scraper.get(url_feedback,
                                          headers=getattr(vinted_client, "headers", {}),
                                          cookies=getattr(vinted_client, "cookies", {}),
                                          proxies=getattr(vinted_client, "proxy", None))
            response.raise_for_status() # Errore 503
            raw_json_data = response.json()

            if 'user_feedbacks' not in raw_json_data or not raw_json_data['user_feedbacks']:
                return None 

            for feedback in raw_json_data['user_feedbacks']:
                # 'feedback_user_id' è la persona CHE HA LASCIATO il feedback
                feedback_author_id = feedback.get('feedback_user_id')
                
                if feedback_author_id == seller_id:
                    return feedback.get('rating')

            
            pagination = raw_json_data.get('pagination')
            if not pagination or pagination.get('current_page', page) >= pagination.get('total_pages', page):
                return None
            
            page += 1
            
            time.sleep(random.randint(2, 5))

        except Exception as e:
           
            raise e
    
    return None 

# ========================================================================
# NUOVO SCRAPER
# ========================================================================

def main():
    global HAS_RESTARTED
    
   
    CUSTOM_COOKIES_DICT = convert_cookie_string_to_dict(RAW_COOKIE_STRING)
    vinted = Vinted(domain="it")
    try:
        vinted.update_cookies(CUSTOM_COOKIES_DICT)
    except Exception:
        vinted.cookies = CUSTOM_COOKIES_DICT
    print("Autenticazione impostata.")

    
    if os.path.exists(OUTPUT_DATASET):
        print(f"File di output trovato. Carico '{OUTPUT_DATASET}' per riprendere...")
        df = pd.read_csv(OUTPUT_DATASET)
    else:
        print(f"Carico input file: '{INPUT_DATASET}'...")
        df = pd.read_csv(INPUT_DATASET)
        df['Rating_Venditore_A'] = np.nan 
        
    print(f"Dataset caricato. Totale transazioni: {len(df)}")

    
    print("Inizio scraping contro-recensioni ")
    
    
    processed_count = df['Rating_Venditore_A'].notna().sum()
    total_count = len(df)
    print(f"Progresso: {processed_count} / {total_count} già processati.")
    
    try:
        for index, row in df.iterrows():
            
            #  Logica di Resume 
            # Se il rating NON è NaN, significa che l'abbiamo già processato (o trovato 1-5, o messo 0)
            if pd.notna(row['Rating_Venditore_A']):
                continue 

            
            try:
                buyer_id = int(row['Acquirente_ID'])
                seller_id = int(row['Venditore_ID'])
            except Exception:
                print(f"Riga {index} saltata (ID non validi).")
                continue 

            print(f"\nProcesso riga {index+1}/{total_count} (Acquirente: {buyer_id}, Venditore: {seller_id})...")

            try:
                #  Chiamata API 
                rating = find_counter_review(vinted, buyer_id, seller_id)
                

                if rating:
                    print(f"  -> TROVATO! Rating: {rating}")
                    df.at[index, 'Rating_Venditore_A'] = rating
                else:
                    print(f"  ->  Non trovato.")
                    df.at[index, 'Rating_Venditore_A'] = 0 
                
                sleep_duration = random.randint(MIN_SLEEP, MAX_SLEEP)
                print(f"  -> Pausa di {sleep_duration}s...")
                time.sleep(sleep_duration)

            # GESTIONE ERRORI  
            except Exception as e:
                err_str = str(e)
                print(f"Errore during scraping della riga {index}: {err_str}")

                is_401_error = "401" in err_str or "Unauthorized" in err_str
                is_connection_error = "Connection aborted" in err_str or "RemoteDisconnected" in err_str
                is_server_error = "500" in err_str or "503" in err_str 
                
                if (is_401_error or is_connection_error or is_server_error) and not HAS_RESTARTED:
                    print(f"🚨 Errore Riavviabile Rilevato: ({err_str[:50]}...)")
                    print("🔁 Riavvio automatico del programma tra 10 secondi...")
                

                    HAS_RESTARTED = True
                    df.to_csv(OUTPUT_DATASET, index=False, encoding='utf-8')
                    print("Salvataggio progressi completato.")
                    time.sleep(10)
                    
                    os.execv(sys.executable, [sys.executable] + sys.argv)

                else:
                    
                    print("ERRORE NON GESTIBILE (403, 429, o errore ripetuto).")
                    
                   
                    if not (is_401_error or is_connection_error or is_server_error):
                         print("Questo è probabilmente un BAN IP. Riprova tra 24 ore.")
                    else:
                         print("L'errore riavviabile persiste dopo il riavvio. Fermo lo script.")
                    
                    raise e 

            # Salvataggio Incrementale 
            if (index + 1) % SAVE_EVERY == 0:
                print(f"\n SALVATAGGIO INCREMENTALE (riga {index+1}) ")
                df.to_csv(OUTPUT_DATASET, index=False, encoding='utf-8')
                print(" Salvataggio completato. ")

    except KeyboardInterrupt:
        print("\nInterruzione manuale rilevata (Ctrl+C). Salvataggio...")
    
    except Exception as e:
        print(f"\nERRORE FATALE: {e}. Salvataggio d'emergenza...")

    finally:
        # BLOCCO SALVATAGGIO (FINALE)
        print("\n SALVATAGGIO FINALE ")
        df.to_csv(OUTPUT_DATASET, index=False, encoding='utf-8')
        print(f" Dati salvati in: {OUTPUT_DATASET}")

# ========================================================================
# ESECUZIONE
# ========================================================================
if __name__ == "__main__":
    main()
import os
import requests
import re
import json
from datetime import datetime

def analizza_strumenti():
    try:
        # Verifica se il file index.html esiste
        if not os.path.exists('index.html'):
            return "❌ Errore: Il file index.html non è stato ancora generato."
            
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Estrae i dati JSON dalla Dashboard
        json_match = re.search(r'const data\s*=\s*({.*?});', content, re.DOTALL)
        if not json_match:
            return "❌ Errore: Non riesco a leggere i dati JSON nella Dashboard."
            
        data = json.loads(json_match.group(1))
        indices = data.get('indices', {})
        live_info = data.get('live', {})
        
        # --- CONFIGURAZIONE (Personalizzala qui) ---
        SOGLIA = 0.30  
        # Sostituisci NOME-REPO con il nome del tuo nuovo repository
        DASHBOARD_URL = "https://tobiatidesca-art.github.io/dashboard-beta/" 
        
        moltiplicatori = {"SX50E": 10, "DAX": 25, "FTSEMIB": 5, "CAC": 10, "IBEX": 10}
        nomi_strumenti = {"SX50E": "EUROSTOXX 50", "DAX": "DAX 40", "FTSEMIB": "FTSE MIB 🇮🇹"}

        report = f"🌐 *DASHBOARD LIVE:* [ACCEDI QUI]({DASHBOARD_URL})\n"
        report += "🏛 *QUANT-PRO STRATEGY REPORT*\n"
        
        momentum_medio = (live_info.get('sp_chg',0) + live_info.get('nk_chg',0) + live_info.get('fut_chg',0)) / 3
        report += f"📊 Momentum Medio: *{momentum_medio:.2f}%*\n"
        report += "───────────────────\n"
        
        for key, info in indices.items():
            if key not in nomi_strumenti: continue # Analizziamo solo gli indici principali
            
            history = info.get('history', [])
            if not history: continue
            
            mult = moltiplicatori.get(key, 1)
            ultima_op = history[-1]
            m_val = ultima_op['m'] * 100
            vix = live_info.get('vix', 0)
            
            # Calcolo Segnale
            if m_val > SOGLIA and vix < 25: 
                segnale = "LONG 🟢"
            elif m_val < -SOGLIA and vix < 32: 
                segnale = "SHORT 🔴"
            else: 
                segnale = "FLAT ⚪"
            
            report += f"*{nomi_strumenti.get(key, key)}*\n"
            report += f"🎯 Segnale: {segnale}\n"
            report += f"📍 Entry: *{info.get('entry', 0):,.1f}*\n\n"
            
            # Ultime 2 Operazioni Chiuse
            trade_reali = []
            for h in reversed(history[:-1]): 
                m_h = h['m'] * 100
                if abs(m_h) > SOGLIA:
                    tipo = "LONG" if m_h > SOGLIA else "SHORT"
                    punti = (h['out'] - h['in']) if tipo == "LONG" else (h['in'] - h['out'])
                    pnl = (punti - 2) * mult 
                    trade_reali.append(f"• {h['d']} ({tipo}): *{pnl:,.0f}€*")
                if len(trade_reali) == 2: break
            
            if trade_reali:
                report += "📊 *Ultime Operazioni:*\n" + "\n".join(trade_reali) + "\n\n"

        report += "───────────────────\n"
        return report
        
    except Exception as e:
        return f"❌ Errore interno al bot: {str(e)}"

def invia_telegram():
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ ERRORE: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID non configurati nei Secrets.")
        return

    testo = analizza_strumenti()
    
    # Debug nei log di GitHub
    print(f"Tentativo di invio a Chat ID: {chat_id}")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": testo, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload)
        # Questo print è fondamentale per vedere l'errore nei log di GitHub
        print(f"Risposta Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Errore durante la chiamata API: {e}")

if __name__ == "__main__":
    invia_telegram()

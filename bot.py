import os
import requests
import re
import json
from datetime import datetime

def analizza_strumenti():
    try:
        if not os.path.exists('index.html'):
            return "❌ File index.html non trovato."
            
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        json_match = re.search(r'const data\s*=\s*({.*?});', content, re.DOTALL)
        if not json_match:
            return "❌ Dati JSON non trovati nel file HTML."
            
        data = json.loads(json_match.group(1))
        indices = data.get('indices', {})
        live_info = data.get('live', {})
        
        # --- CONFIGURAZIONE ALLINEATA V8.4.8 ---
        SOGLIA = 0.70  # Allineata al valore di default della Dashboard
        DASHBOARD_URL = "https://tobiatidesca-art.github.io/dashboard-beta/" # <-- CAMBIA CON IL TUO NUOVO URL
        moltiplicatori = {"SX50E": 10, "DAX": 25, "FTSEMIB": 5, "CAC": 10, "IBEX": 10}
        nomi_strumenti = {"SX50E": "EUROSTOXX 50", "DAX": "DAX 40", "FTSEMIB": "FTSE MIB 🇮🇹", "CAC": "CAC 40", "IBEX": "IBEX 35"}

        report = f"🌐 *DASHBOARD LIVE:* [ACCEDI QUI]({DASHBOARD_URL})\n"
        report += "🏛 *QUANT-PRO STRATEGY REPORT*\n"
        report += f"📊 Momentum: *{((live_info.get('sp_chg',0)+live_info.get('nk_chg',0)+live_info.get('fut_chg',0))/3):.2f}%*\n"
        report += "───────────────────\n"
        
        for key, info in indices.items():
            history = info.get('history', [])
            if not history: continue
            
            mult = moltiplicatori.get(key, 1)
            ultima_op = history[-1]
            m_val = ultima_op['m'] * 100
            
            if m_val > SOGLIA and live_info.get('vix', 0) < 25: segnale = "LONG 🟢"
            elif m_val < -SOGLIA and live_info.get('vix', 0) < 32: segnale = "SHORT 🔴"
            else: segnale = "FLAT ⚪"
            
            report += f"*{nomi_strumenti.get(key, key)}*\n"
            report += f"🎯 Segnale: {segnale}\n"
            report += f"📍 Entry: *{info.get('entry', 0):,.1f}*\n\n"
            
            # Ultime 2 Operazioni
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

            # Performance Storica
            pnl_per_anno = {}
            for h in history:
                m_h = h['m'] * 100
                if abs(m_h) > SOGLIA:
                    anno = h['d'][:4] 
                    punti = (h['out'] - h['in']) if m_h > SOGLIA else (h['in'] - h['out'])
                    pnl = (punti - 2) * mult
                    pnl_per_anno[anno] = pnl_per_anno.get(anno, 0) + pnl

            report += "📈 *PERFORMANCE STORICA:*\n"
            anni_ordinati = sorted(pnl_per_anno.keys(), reverse=True)
            def fmt(v): return "{:+,.0f}".format(v).replace(",", ".")

            for i in range(0, len(anni_ordinati), 2):
                a1 = anni_ordinati[i]
                v1 = pnl_per_anno[a1]
                e1 = "✅" if v1 >= 0 else "🔻"
                riga = f"`{a1}:{fmt(v1)}€{e1}`"
                if i + 1 < len(anni_ordinati):
                    a2 = anni_ordinati[i+1]
                    v2 = pnl_per_anno[a2]
                    e2 = "✅" if v2 >= 0 else "🔻"
                    riga += f" | `{a2}:{fmt(v2)}€{e2}`"
                report += riga + "\n"
            report += "───────────────────\n"
            
        return report
    except Exception as e:
        return f"❌ Errore analisi: {str(e)}"

def invia_telegram():
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("❌ Errore: Credenziali Telegram mancanti.")
        return
    testo = analizza_strumenti()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": testo, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    invia_telegram()

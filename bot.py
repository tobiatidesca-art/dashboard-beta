import os
import requests
import re
import json
from datetime import datetime

def analizza_strumenti():
    try:
        if not os.path.exists('index.html'):
            return "❌ Errore: File index.html non trovato."
            
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        json_match = re.search(r'const data\s*=\s*({.*?});', content, re.DOTALL)
        if not json_match:
            return "❌ Errore: Dati JSON non trovati."
            
        data = json.loads(json_match.group(1))
        indices = data.get('indices', {})
        live_info = data.get('live', {})
        
        SOGLIA = 0.30  
        DASHBOARD_URL = "https://tobiatidesca-art.github.io/dashboard-beta/" 
        moltiplicatori = {"SX50E": 10, "DAX": 25, "FTSEMIB": 5}
        nomi_strumenti = {"SX50E": "EUROSTOXX 50", "DAX": "DAX 40", "FTSEMIB": "FTSE MIB 🇮🇹"}

        data_oggi = datetime.now().strftime('%d/%m/%Y')
        report = f"🌐 *DASHBOARD:* [ACCEDI QUI]({DASHBOARD_URL})\n"
        report += f"📅 *REPORT DEL:* {data_oggi}\n"
        report += "───────────────────\n"
        
        for key, info in indices.items():
            if key not in nomi_strumenti: continue
            
            history = info.get('history', [])
            if not history: continue
            
            mult = moltiplicatori.get(key, 1)
            # --- SEGNALE DI OGGI ---
            ultima_op = history[-1]
            m_val = ultima_op['m'] * 100
            vix = live_info.get('vix', 0)
            
            if m_val > SOGLIA and vix < 25: segnale = "LONG 🟢"
            elif m_val < -SOGLIA and vix < 32: segnale = "SHORT 🔴"
            else: segnale = "FLAT ⚪"
            
            report += f"*{nomi_strumenti[key]}*\n"
            report += f"🎯 Segnale: {segnale}\n"
            report += f"📍 Entry: *{info.get('entry', 0):,.1f}*\n\n"
            
            # --- ULTIME 2 OPERAZIONI CHIUSE ---
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

            # --- STATISTICHE ANNUALI (Corrente + 2 Precedenti) ---
            stats_anni = {}
            current_year = datetime.now().year
            anni_target = [str(current_year), str(current_year-1), str(current_year-2)]
            
            for h in history:
                anno = h['d'][:4]
                if anno in anni_target:
                    if anno not in stats_anni:
                        stats_anni[anno] = {'pnl':0, 'wins':[], 'loss':[]}
                    
                    m_h = h['m'] * 100
                    if abs(m_h) > SOGLIA:
                        punti = (h['out'] - h['in']) if m_h > SOGLIA else (h['in'] - h['out'])
                        pnl = (punti - 2) * mult
                        stats_anni[anno]['pnl'] += pnl
                        if pnl > 0: stats_anni[anno]['wins'].append(pnl)
                        else: stats_anni[anno]['loss'].append(abs(pnl))

            report += "📈 *DETTAGLIO PERFORMANCE:*\n"
            for anno in anni_target:
                if anno in stats_anni:
                    s = stats_anni[anno]
                    tot_pnl = s['pnl']
                    w_list = s['wins']
                    l_list = s['loss']
                    
                    gross_profit = sum(w_list)
                    gross_loss = sum(l_list)
                    pf = gross_profit / gross_loss if gross_loss > 0 else gross_profit
                    avg_w = sum(w_list)/len(w_list) if w_list else 0
                    avg_l = sum(l_list)/len(l_list) if l_list else 0
                    
                    emoji = "✅" if tot_pnl >= 0 else "🔻"
                    report += f"*{anno}*: {tot_pnl:+,.0f}€ {emoji}\n"
                    report += f"└ PF: `{pf:.2f}` | W: `{len(w_list)}` - L: `{len(l_list)}`\n"
                    report += f"└ Avg W: `{avg_w:,.0f}€` | Avg L: `{avg_l:,.0f}€`\n"
            
            report += "───────────────────\n"
            
        return report
    except Exception as e:
        return f"❌ Errore: {str(e)}"

def invia_telegram():
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    testo = analizza_strumenti()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": testo, "parse_mode": "Markdown"})

if __name__ == "__main__":
    invia_telegram()

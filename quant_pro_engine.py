import yfinance as yf
import pandas as pd
import json
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

def get_market_data_engine():
    targets = {'SX50E': '^STOXX50E', 'DAX': '^GDAXI', 'CAC': '^FCHI', 'IBEX': '^IBEX', 'FTSEMIB': 'FTSEMIB.MI'}
    predictors = ['^GSPC', '^N225', '^VIX', 'ES=F']
    all_tks = list(targets.values()) + predictors
    df = yf.download(all_tks, period="max", progress=False)['Close'].ffill()
    df_open = yf.download(all_tks, period="max", progress=False)['Open'].ffill()

    now = datetime.now()
    if (now.hour < 15) or (now.hour == 15 and now.minute < 30):
        sp_status = "CLOSE: " + df['^GSPC'].index[-2].strftime('%d %b')
    else:
        sp_status = "LIVE: " + df['^GSPC'].index[-1].strftime('%d %b')
    
    if now.hour >= 8:
        nk_status = "CLOSE: " + df['^N225'].index[-1].strftime('%d %b')
    else:
        nk_status = "LIVE: " + df['^N225'].index[-1].strftime('%d %b')

    fut_h = yf.download('ES=F', period="5d", interval="1h", progress=False)
    if isinstance(fut_h.columns, pd.MultiIndex): fut_h.columns = fut_h.columns.get_level_values(0)
    try:
        f_o = fut_h.between_time('00:00', '00:00')['Open'].iloc[-1]
        f_c = fut_h.between_time('08:00', '08:00')['Close'].iloc[-1]
        fut_chg = ((f_c / f_o) - 1) * 100
    except: fut_chg = 0.0

    db = {'indices': {}, 'live': {
        'sp_val': float(df['^GSPC'].iloc[-1]), 'sp_dt': sp_status, 
        'sp_chg': float(df['^GSPC'].pct_change().iloc[-1]*100),
        'nk_val': float(df['^N225'].iloc[-1]), 'nk_dt': nk_status, 
        'nk_chg': float(df['^N225'].pct_change().iloc[-1]*100),
        'fut_chg': float(fut_chg), 'vix': float(df['^VIX'].iloc[-1])
    }}

    for name, ticker in targets.items():
        temp = pd.DataFrame({
            'in': df_open[ticker], 'out': df[ticker],
            'm1': df['^GSPC'].pct_change().shift(1), 'm2': df['^N225'].pct_change(),
            'm3': df['ES=F'].pct_change(), 'v': df['^VIX']
        }).dropna()
        temp['MOM'] = (temp['m1'] + temp['m2'] + temp['m3']) / 3
        history = []
        for d, r in temp.iterrows():
            history.append({'d': d.strftime('%Y-%m-%d'), 'm': r['MOM'], 'v': r['v'], 'in': r['in'], 'out': r['out']})
        db['indices'][name] = {'history': history, 'entry': float(df_open[ticker].iloc[-1])}
    return db

data = get_market_data_engine()

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ background: #05080a; color: #e6edf3; font-family: 'Inter', sans-serif; padding: 20px; }}
        .header-main {{ background: #0d1117; border-bottom: 3px solid #238636; padding: 25px; border-radius: 15px; margin-bottom: 25px; }}
        .val-big-label {{ font-size: 0.8rem; color: #58a6ff; font-weight: 700; text-transform: uppercase; }}
        .val-big-number {{ display: block; font-size: 2.6rem; font-family: 'Roboto Mono', monospace; color: white; font-weight: 700; line-height: 1; }}
        .ts-label {{ font-size: 1.1rem; color: #8b949e; font-family: 'Roboto Mono'; text-transform: uppercase; margin-top: 8px; font-weight: 700; }}
        .server-time {{ color: #f1c40f; font-weight: 700; font-size: 1.5rem; font-family: 'Roboto Mono'; }}
        .card-custom {{ background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }}
        @keyframes blink {{ 0% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.4; transform: scale(0.98); }} 100% {{ opacity: 1; transform: scale(1); }} }}
        .blink-active {{ animation: blink 1.2s infinite ease-in-out; display: inline-block; }}
        .signal-badge {{ font-size: 3.2rem; font-weight: 900; }}
        .pf-box {{ border: 2px solid #f1c40f; border-radius: 8px; padding: 10px; text-align: center; margin-top: 15px; }}
        .zoom-btn {{ background: #21262d; border: 1px solid #30363d; color: #8b949e; padding: 5px 12px; border-radius: 6px; }}
        .zoom-btn.active {{ background: #238636; color: white; }}
    </style>
</head>
<body>
    <div class="header-main">
        <div class="row align-items-center text-center">
            <div class="col-md-2 text-start">
                <select id="assetS" onchange="run()" class="form-select bg-primary text-white border-0 fw-bold mb-2">
                    <option value="SX50E">EUROSTOXX 50</option>
                    <option value="DAX">DAX 40</option>
                    <option value="FTSEMIB">FTSE MIB</option>
                </select>
                <select id="langS" onchange="run()" class="form-select bg-dark text-white border-secondary">
                    <option value="it">Italiano 🇮🇹</option>
                    <option value="en">English 🇬🇧</option>
                    <option value="es">Español 🇪🇸</option>
                    <option value="fr">Français 🇫🇷</option>
                    <option value="de">Deutsch 🇩🇪</option>
                    <option value="zh">中文 🇨🇳</option>
                    <option value="ja">日本語 🇯🇵</option>
                </select>
            </div>
            <div class="col-md-2 border-end border-secondary">
                <span class="val-big-label">S&P 500</span>
                <span class="val-big-number">{data['live']['sp_val']:.0f}</span>
                <div class="ts-label">{data['live']['sp_dt']}</div>
            </div>
            <div class="col-md-2 border-end border-secondary">
                <span class="val-big-label">NIKKEI 225</span>
                <span class="val-big-number">{data['live']['nk_val']:.0f}</span>
                <div class="ts-label">{data['live']['nk_dt']}</div>
            </div>
            <div class="col-md-2 border-end border-secondary">
                <span class="val-big-label">MOMENTUM</span>
                <span id="mom-val" class="val-big-number" style="color:#f1c40f">--</span>
                <div class="ts-label">WIN: 00-08 CET</div>
            </div>
            <div class="col-md-2 border-end border-secondary">
                <span class="val-big-label">SERVER TIME</span>
                <div id="clock" class="server-time">--:--:--</div>
                <div class="ts-label">ROME / BERLIN</div>
            </div>
            <div class="col-md-2">
                <div id="entry-val" class="fw-bold text-white small">--</div>
                <div id="sig-val" class="signal-badge">---</div>
            </div>
        </div>
    </div>
    <div class="row g-4 px-3">
        <div class="col-xl-3">
            <div class="card-custom">
                <h6 class="val-big-label mb-3">PARAMETRI</h6>
                <input type="number" id="thr" class="form-control bg-dark text-white border-warning mb-3" value="0.70" step="0.05" oninput="run()">
                <div id="kpi-grid" class="row g-2"></div>
                <div class="pf-box"><div class="val-big-label" style="color:#f1c40f">PROFIT FACTOR</div><div id="pf-val" class="h4 fw-bold mb-0" style="color:#f1c40f">--</div></div>
            </div>
        </div>
        <div class="col-xl-9">
            <div class="card-custom">
                <div class="d-flex justify-content-between mb-2">
                    <span class="badge bg-success">EQUITY VS INDEX</span>
                    <div class="btn-group">
                        <button class="zoom-btn" onclick="setZoom(this, 22)">1M</button>
                        <button class="zoom-btn" onclick="setZoom(this, 66)">3M</button>
                        <button class="zoom-btn active" onclick="setZoom(this, 0)">MAX</button>
                    </div>
                </div>
                <div style="height: 400px;"><canvas id="chart"></canvas></div>
            </div>
        </div>
    </div>
    <div class="card-custom mt-4 mx-3">
        <h6 class="val-big-label mb-3">JOURNAL (REPAIRED HISTORY)</h6>
        <div class="table-responsive" style="max-height: 400px;"><table class="table table-dark table-hover m-0"><thead><tr id="t-head"></tr></thead><tbody id="auditBody"></tbody></table></div>
    </div>
    <script>
        const data = {json.dumps(data)};
        let myChart = null; let currentZoom = 0;
        const i18n = {{
            it: {{ kpi:["Profitto","Win Rate"], sig:["FLAT","LONG","SHORT"], cols:["DATA","TIPO","IN","OUT","PTI","PNL"] }},
            en: {{ kpi:["Profit","Win Rate"], sig:["FLAT","LONG","SHORT"], cols:["DATE","TYPE","IN","OUT","PTS","PNL"] }},
            es: {{ kpi:["Beneficio","Win Rate"], sig:["FLAT","LONG","SHORT"], cols:["FECHA","TIPO","IN","OUT","PTS","PNL"] }},
            fr: {{ kpi:["Profit","Win Rate"], sig:["FLAT","LONG","SHORT"], cols:["DATE","TYPE","IN","OUT","PTS","PNL"] }},
            de: {{ kpi:["Gewinn","Win Rate"], sig:["FLAT","LONG","SHORT"], cols:["DATUM","TYP","IN","OUT","PKT","PNL"] }},
            zh: {{ kpi:["利润","胜率"], sig:["平仓","做多","做空"], cols:["日期","类型","入场","出场","点数","盈亏"] }},
            ja: {{ kpi:["利益","勝率"], sig:["フラット","ロング","ショート"], cols:["日付","タイプ","入","出","ポイント","損益"] }}
        }};
        function setZoom(btn, days) {{ currentZoom = days; document.querySelectorAll('.zoom-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); run(); }}
        function run() {{
            const asset = document.getElementById('assetS').value; const lang = document.getElementById('langS').value; const t = i18n[lang]; const thr = parseFloat(document.getElementById('thr').value) / 100; const assetData = data.indices[asset]; const live = data.live;
            document.getElementById('t-head').innerHTML = t.cols.map(c => `<th>${{c}}</th>`).join('');
            const m = (live.sp_chg + live.nk_chg + live.fut_chg) / 300;
            document.getElementById('mom-val').innerText = (m*100).toFixed(2) + "%";
            document.getElementById('entry-val').innerText = "ENTRY: " + assetData.entry.toFixed(1);
            let s = t.sig[0]; let c = "#8b949e"; let blink = false;
            if (m > thr && live.vix < 25) {{ s = t.sig[1] + " 🟢"; c = "#238636"; blink = true; }} else if (m < -thr && live.vix < 32) {{ s = t.sig[2] + " 🔴"; c = "#da3633"; blink = true; }}
            const sigEl = document.getElementById('sig-val'); sigEl.innerText = s; sigEl.style.color = c;
            if(blink) sigEl.classList.add('blink-active'); else sigEl.classList.remove('blink-active');
            let cap = 20000, wins = 0, total = 0, gP = 0, gL = 0; let mult = asset==='DAX'?25:(asset==='FTSEMIB'?5:10);
            let hist = currentZoom > 0 ? assetData.history.slice(-currentZoom) : assetData.history;
            let eqD = [], idxD = [], lbl = [], rows = [];
            hist.forEach(h => {{
                let p = 0; if (h.m > thr && h.v < 25) p = 1; else if (h.m < -thr && h.v < 32) p = -1;
                if (p !== 0) {{ total++; let pts = p === 1 ? (h.out - h.in - 2) : (h.in - h.out - 2); let pnl = pts * mult; cap += pnl; if (pnl > 0) {{ wins++; gP += pnl; }} else {{ gL += Math.abs(pnl); }}
                    rows.push(`<tr><td>${{h.d}}</td><td>${{p==1?t.sig[1]:t.sig[2]}}</td><td>${{h.in.toFixed(1)}}</td><td>${{h.out.toFixed(1)}}</td><td class="${{pts>=0?'text-success':'text-danger'}}">${{pts.toFixed(1)}}</td><td>${{Math.round(pnl)}}€</td></tr>`); }}
                eqD.push(cap); idxD.push(h.out); lbl.push(h.d);
            }});
            document.getElementById('kpi-grid').innerHTML = `<div class="col-6"><div class="p-2 border border-secondary rounded text-center"><div class="val-big-label">${{t.kpi[0]}}</div><div class="text-success fw-bold">${{(cap-20000).toLocaleString()}}€</div></div></div><div class="col-6"><div class="p-2 border border-secondary rounded text-center"><div class="val-big-label">${{t.kpi[1]}}</div><div class="text-info fw-bold">${{total?((wins/total)*100).toFixed(1):0}}%</div></div></div>`;
            document.getElementById('pf-val').innerText = gL === 0 ? gP.toFixed(2) : (gP/gL).toFixed(2);
            document.getElementById('auditBody').innerHTML = rows.reverse().join('');
            if (myChart) myChart.destroy();
            myChart = new Chart(document.getElementById('chart'), {{ data: {{ labels: lbl, datasets: [{{ type:'line', label:'Equity', data:eqD, borderColor:'#238636', yAxisID:'y', pointRadius:0, borderWidth:2.5, fill:true, backgroundColor:'rgba(35,134,54,0.05)' }},{{ type:'line', label:asset, data:idxD, borderColor:'rgba(241,196,15,0.4)', yAxisID:'y1', pointRadius:0, borderWidth:1.2 }}]}}, options: {{ responsive:true, maintainAspectRatio:false, scales:{{ y:{{ grid:{{color:'#161b22'}} }}, y1:{{ position:'right', grid:{{display:false}} }} }} }} }});
        }}
        function clock() {{ document.getElementById('clock').innerText = new Date().toLocaleTimeString('it-IT', {{timeZone:'Europe/Berlin'}}) + " CET"; }}
        setInterval(clock, 1000); window.onload = run;
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURATION & UX/UI STYLING
# ==========================================
st.set_page_config(page_title="Goossens Finance", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# Modernes, Mobile-First CSS (Soft Shadows, abgerundete Ecken, Apple-like Design)
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    
    /* Metrics & Cards */
    div[data-testid="stMetric"] { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 16px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.04); 
        text-align: center;
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700; color: #1e293b; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Expander Styling */
    div[data-testid="stExpander"] { 
        background-color: #ffffff; 
        border-radius: 16px; 
        border: none; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.03); 
        margin-bottom: 10px;
    }
    
    /* Sprint Phase Colors */
    .phase-felix div[data-testid="stMetric"] { border-bottom: 4px solid #10b981; }
    .phase-janina div[data-testid="stMetric"] { border-bottom: 4px solid #f43f5e; }
    
    /* Tabs Styling */
    button[data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; }
    
    /* Hide index in DataFrames for cleaner mobile look */
    thead tr th:first-child {display:none}
    tbody th {display:none}
    </style>
    """, unsafe_allow_html=True)

# --- FINANZ-PARAMETER ---
LIMIT_LIFESTYLE_PHASE = 600.00 
TARGET_GROWTH = 233.00

CATEGORIES = {
    '00. Einnahmen (Gehalt & Co)': ['educura', 'walbusch', 'bundesagentur für arbeit', 'kindergeld', 'gehalt', 'lohn', 'bezüge', 'wp-abrechnung', 'zins', 'dividende', 'finanzamt'],
    '01. Einmalige Anschaffungen': ['hoppe', 'olavson', 'küchenstudio', 'werkzeugstore', 'tonies', 'wunsch-stern', 'monoki', 'kueche finale rate', 'vorwerk', 'thermomix'],
    '02. Fix: Lebensmittel': ['aldi', 'edeka', 'rewe', 'lidl', 'penny', 'dm-drogerie', 'rossmann', 'eismann', 'pegels', 'apotheke', 'flaschenpost', 'e-center', 'fressnapf', 'bäcker', 'backstube', 'baeckerei', 'buesch', 'kamps', 'hoenen'],
    '03. Fix: Tiere (Flash, Gizmo, Ruby, Smokey)': ['renee faatz', 'stallmiete', 'horze', 'reitsport', 'tierarzt', 'tierklinik', 'fressnapf', 'zooplus'],
    '04. Fix: Sprit & Auto': ['shell', 'aral', 'markant', 'tankstelle', 'bundeskasse', 'kfz-steuer'],
    '05. Fix: Versicherungen': ['vhv', 'itzehoer', 'landeskrankenhilfe', 'arag', 'huk', 'allianz'],
    '06. Fix: Wohnkosten': ['ing-diba', 'r+v', 'darlehen', 'mormels', 'new niederrhein', 'grundbesitzabgaben', 'stadt kempen', 'stadt moenchengladbach', 'rundfunk', 'eigentümergemeinschaft'],
    '07. Sparen & Vermögen': ['sparen', 'sparrate', 'bauspar', 'deka', 'tierkonto', 'wuenschekonto', 'vermoegenskonto', 'wp-abrechnung', 'vanguard', 'trade republic', 'scalable'],
    '08. Spaß: Abos (fix)': ['spotify', 'netflix', 'wow tv', 'disney', 'google', 'apple', 'fitx', 'waipu', 'exaring', 'e-plus', 'audible', 'vodafone'],
    '09. Spaß: Amazon': ['amazon', 'amzn'],
    '10. Spaß: Gastro & Essen': ['lieferando', 'ubereats', 'pizza', 'sushi', 'restaurant', 'takeaway', 'paypal', 'venga', 'mcdonalds'],
    '11. Spaß: Klarna (Einkauf)': ['klarna'],
    '12. Spaß: Mode & Shopping': ['riverty', 'bestsecret', 'best secret', 'zalando', 'otto payments', 'fashion'],
    '13. Spaß: Wetten & Lotto': ['tipico', 'lotto', 'westlotto', 'westdeutsche lotterie'],
    '14. Sonstiges': ['cafe', 'q-park', 'sparkasse', 'parken', 'bargeldauszahlung']
}

SEARCH_ORDER = ['13. Spaß: Wetten & Lotto', '09. Spaß: Amazon', '11. Spaß: Klarna (Einkauf)', '12. Spaß: Mode & Shopping', '10. Spaß: Gastro & Essen'] + sorted(list(CATEGORIES.keys()))

def euro(x): return f"{x:,.2f} €".replace(".", "X").replace(",", ".").replace("X", ",")

def get_clean_name(row):
    empf, zweck = str(row['Empfaenger']).strip(), str(row['Verwendungszweck']).upper()
    if any(p in empf.upper() for p in ['PAYPAL', 'KLARNA', 'RIVERTY', 'AMAZON', 'VISA']):
        clean = re.sub(r'[^A-Z\s]', ' ', re.sub(r'\d{5,}', '', zweck.replace('PP.', '').replace('KAUFUMSATZ', ''))).strip()
        parts = clean.split()
        if parts: return f"{empf.split()[0]} ({' '.join(parts[:2]).title()})"
    return empf[:30]

# ==========================================
# 2. DATENVERARBEITUNG & SPRINT-LOGIK
# ==========================================
@st.cache_data
def process_csv(file):
    df = pd.read_csv(file, sep=';', encoding='latin1')
    if df['Betrag'].dtype == 'O':
        df['Betrag'] = df['Betrag'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    df['Buchungsdatum'] = pd.to_datetime(df['Buchungsdatum'], format='%d.%m.%Y')
    
    # Filter interne Umbuchungen
    df = df[~((df['Empfaenger'].str.contains('Felix Goossens', na=False)) & (df['Betrag'].abs() > 1000))]
    
    def categorize(row):
        text = (str(row['Empfaenger']) + " " + str(row['Verwendungszweck'])).lower()
        for cat in SEARCH_ORDER:
            if any(kw.lower() in text for kw in CATEGORIES[cat]): return cat
        return '14. Sonstiges'

    df['Kategorie'] = df.apply(categorize, axis=1)
    return df

def get_current_sprint(latest_date):
    """Berechnet die exakten Start- und Enddaten des aktuellen Sprints"""
    if pd.isna(latest_date): return None, None, "Unbekannt"
    
    if latest_date.day >= 27:
        start = latest_date.replace(day=27)
        end = (latest_date.replace(day=1) + timedelta(days=32)).replace(day=11)
        name = "Felix-Phase (27. - 11.)"
    elif latest_date.day <= 11:
        end = latest_date.replace(day=11)
        start = (latest_date.replace(day=1) - timedelta(days=1)).replace(day=27)
        name = "Felix-Phase (27. - 11.)"
    else:
        start = latest_date.replace(day=12)
        end = latest_date.replace(day=26)
        name = "Janina-Phase (12. - 26.)"
        
    return start, end, name

# ==========================================
# 3. APP UI (MOBILE FIRST)
# ==========================================
with st.expander("⚙️ Daten-Upload & Kontostand", expanded=True):
    uploaded_file = st.file_uploader("Buchungsliste (CSV) hochladen", type="csv")
    bal = st.number_input("Aktueller Saldo Girokonto (€)", value=0.0, step=10.0)

if uploaded_file:
    df_all = process_csv(uploaded_file)
    latest_date = df_all['Buchungsdatum'].max()
    
    # Sprint berechnen
    s_start, s_end, phase_name = get_current_sprint(latest_date)
    phase_df = df_all[(df_all['Buchungsdatum'] >= s_start) & (df_all['Buchungsdatum'] <= s_end)].copy()
    
    # Lifestyle-Berechnung für aktuellen Sprint
    life_kats = [k for k in CATEGORIES.keys() if any(x in k for x in ['Spaß', 'Amazon', 'Wetten', 'Klarna', 'Mode'])]
    sum_life_phase = abs(phase_df[phase_df['Kategorie'].isin(life_kats) & (phase_df['Betrag'] < 0)]['Betrag'].sum())
    rem_life_phase = max(0, LIMIT_LIFESTYLE_PHASE - sum_life_phase)
    
    # Pacing Logic (Burn-Rate)
    total_days = (s_end - s_start).days + 1
    days_passed = (latest_date - s_start).days + 1
    ideal_burn = LIMIT_LIFESTYLE_PHASE * (days_passed / total_days)
    burn_status = "🟢 Optimal (Unter Budget)" if sum_life_phase <= ideal_burn else "🔴 Zu hoch (Burn-Rate reduzieren!)"
    
    # CSS für das Metric-Styling (Dynamisch nach Phase)
    wrapper_class = "phase-felix" if "Felix" in phase_name else "phase-janina"
    st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
    
    # --- TABS FÜR MOBILE NAVIGATION ---
    tab1, tab2, tab3 = st.tabs(["💸 Sprint-Cockpit", "📈 Vermögen 2030", "🔍 Analyse"])
    
    with tab1:
        st.markdown(f"<h3 style='text-align: center; color: #334155; margin-bottom: 20px;'>Aktueller Sprint: {phase_name}</h3>", unsafe_allow_html=True)
        
        # Top KPIs
        c1, c2 = st.columns(2)
        c1.metric("Verfügbares Restbudget", euro(rem_life_phase))
        c2.metric("Bereits Ausgegeben", euro(sum_life_phase))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Pacing Widget
        st.markdown(f"**Pacing (Tag {days_passed} von {total_days})**")
        progress = min(sum_life_phase / LIMIT_LIFESTYLE_PHASE, 1.0)
        st.progress(progress)
        st.caption(f"Status: **{burn_status}** | Ideallinie heute: {euro(ideal_burn)}")
        
        st.divider()
        st.markdown("#### Letzte Lifestyle-Buchungen")
        recent_life = phase_df[phase_df['Kategorie'].isin(life_kats) & (phase_df['Betrag'] < 0)].sort_values('Buchungsdatum', ascending=False).head(5)
        for _, r in recent_life.iterrows():
            st.markdown(f"*{r['Buchungsdatum'].strftime('%d.%m.')}* | **{get_clean_name(r)}** <span style='float:right; color:#ef4444;'>{euro(r['Betrag'])}</span>", unsafe_allow_html=True)
            
    with tab2:
        st.markdown("### 🎯 Die 5-Jahres-Festung (Silvester 2031)")
        
        with st.expander("🏦 Cash-Konten (Realitäts-Puffer)", expanded=True):
            st.markdown("""
            *✅ TM7 Küche (1.549 €) & Giro-Puffer (363 €) gesichert.*
            
            * **🐾 Tierkonto:** Ziel **5.000 € Cap** *(Inkl. 1.000 € Steuer-Boost)*
            * **🌴 Wünschekonto:** Rollierend **~ 2.500 €** *(Inkl. 500 € Steuer-Boost)*
            * **🛡️ Kriegskasse (Aktien-Munition):** Rollierend **~ 2.000 €** *(Inkl. 500 € Steuer-Boost)*
            """)
            
        with st.expander("📈 Dividenden-Maschine & Autoverkauf (Mai 2026)", expanded=True):
            st.markdown("""
            **Die Auto-Deckelung (Cap 100):**
            * 🚗 BMW: **100 Stück** (Dann Sparplan Stopp)
            * 🚙 Mercedes: **100 Stück** (Dann Sparplan Stopp)
            
            **Das Britische Royal-Trio (Die 0% Quellensteuer-Raketen):**
            * 💊 GSK plc (Jan, Apr, Jul, Okt)
            * 🚬 B.A.T. (Feb, Mai, Aug, Nov)
            * 🧼 Unilever (Mär, Jun, Sep, Dez)
            
            **Sicherheitsnetz:**
            * 🌍 Vanguard All-World ETF
            
            *(Hinweis: Ab 2027 fließen die 200 € aus BMW/Mercedes als Drittel-Sparplan in das Britische Trio).*
            """)

    with tab3:
        st.markdown("### 🔍 Kategorien-Deep-Dive")
        st.caption(f"Zeigt alle Ausgaben im Zeitraum: {s_start.strftime('%d.%m.')} bis {s_end.strftime('%d.%m.')}")
        
        # Aggregierte Daten für den Sprint
        cat_data = []
        for cat in sorted(CATEGORIES.keys()):
            val = phase_df[phase_df['Kategorie'] == cat]['Betrag'].sum()
            val = val if 'Einnahmen' in cat else abs(val) if val < 0 else 0
            if val > 0: cat_data.append({'Kategorie': cat[4:], 'Betrag': val})
            
        if cat_data:
            st.dataframe(pd.DataFrame(cat_data).style.format({'Betrag': '{:,.2f} €'}), use_container_width=True)
        else:
            st.info("Noch keine Buchungen in diesem Sprint.")
            
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("🚀 Lade oben deine CSV hoch, um dein Mobile-Dashboard zu starten!")

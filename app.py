import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Goossens Finance", layout="wide")

# Custom CSS für Mobile-Optimierung
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #007bff; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

LIMIT_LIFESTYLE = 1200.00
TARGET_GROWTH = 233.00
SALARY_DETECTOR = {'Janina': 'educura', 'Felix': 'walbusch'}

GERMAN_MONTHS = {1:'Januar', 2:'Februar', 3:'März', 4:'April', 5:'Mai', 6:'Juni', 
                 7:'Juli', 8:'August', 9:'September', 10:'Oktober', 11:'November', 12:'Dezember'}

CATEGORIES = {
    '00. Einnahmen (Gehalt & Co)': ['educura', 'walbusch', 'bundesagentur für arbeit', 'kindergeld', 'gehalt', 'lohn', 'bezüge', 'wp-abrechnung', 'zins', 'dividende'],
    '01. Einmalige Anschaffungen': ['hoppe', 'olavson', 'küchenstudio', 'werkzeugstore', 'tonies', 'wunsch-stern', 'monoki', 'kueche finale rate'],
    '02. Fix: Lebensmittel': ['aldi', 'edeka', 'rewe', 'lidl', 'penny', 'dm-drogerie', 'rossmann', 'eismann', 'pegels', 'apotheke', 'flaschenpost', 'e-center', 'fressnapf', 'bäcker', 'backstube', 'baeckerei', 'buesch', 'kamps', 'hoenen'],
    '03. Fix: Pferd (Flash)': ['renee faatz', 'stallmiete', 'horze', 'reitsport'],
    '04. Fix: Sprit & Auto': ['shell', 'aral', 'markant', 'tankstelle', 'bundeskasse', 'kfz-steuer'],
    '05. Fix: Versicherungen': ['vhv', 'itzehoer', 'landeskrankenhilfe', 'arag', 'huk'],
    '06. Fix: Wohnkosten': ['ing-diba', 'r+v', 'darlehen', 'mormels', 'new niederrhein', 'grundbesitzabgaben', 'stadt kempen', 'stadt moenchengladbach', 'rundfunk', 'eigentümergemeinschaft'],
    '07. Sparen': ['sparen', 'sparrate', 'bauspar', 'deka'],
    '08. Spaß: Abos (fix)': ['spotify', 'netflix', 'wow tv', 'disney', 'google', 'apple', 'fitx', 'waipu', 'exaring', 'e-plus', 'audible', 'vodafone'],
    '09. Spaß: Amazon': ['amazon', 'amzn'],
    '10. Spaß: Gastro & Essen': ['lieferando', 'ubereats', 'pizza', 'sushi', 'restaurant', 'takeaway', 'paypal'],
    '11. Spaß: Klarna (Einkauf)': ['klarna'],
    '12. Spaß: Mode & Shopping': ['riverty', 'bestsecret', 'best secret', 'zalando', 'otto payments'],
    '13. Spaß: Wetten & Lotto': ['tipico', 'lotto', 'westlotto'],
    '14. Sonstiges': ['cafe', 'q-park', 'sparkasse', 'parken', 'bargeldauszahlung']
}

SEARCH_ORDER = ['13. Spaß: Wetten & Lotto', '09. Spaß: Amazon', '11. Spaß: Klarna (Einkauf)'] + sorted(list(CATEGORIES.keys()))

def euro(x): return f"{x:,.2f} €".replace(".", "X").replace(",", ".").replace("X", ",")

def get_clean_name(row):
    empf, zweck = str(row['Empfaenger']).strip(), str(row['Verwendungszweck']).upper()
    if any(p in empf.upper() for p in ['PAYPAL', 'KLARNA', 'RIVERTY', 'AMAZON', 'VISA']):
        clean = re.sub(r'[^A-Z\s]', ' ', re.sub(r'\d{5,}', '', zweck.replace('PP.', '').replace('KAUFUMSATZ', ''))).strip()
        parts = clean.split()
        if parts: return f"{empf.split()[0]} ({' '.join(parts[:2]).title()})"
    return empf[:30]

# ==========================================
# 2. LOGIK & DATEN
# ==========================================
@st.cache_data
def process_csv(file):
    df = pd.read_csv(file, sep=';', encoding='latin1')
    if df['Betrag'].dtype == 'O':
        df['Betrag'] = df['Betrag'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    df['Buchungsdatum'] = pd.to_datetime(df['Buchungsdatum'], format='%d.%m.%Y')
    df = df[~((df['Empfaenger'].str.contains('Felix Goossens', na=False)) & (df['Betrag'].abs() > 1000))]
    
    def categorize(row):
        text = (str(row['Empfaenger']) + " " + str(row['Verwendungszweck'])).lower()
        for cat in SEARCH_ORDER:
            if any(kw.lower() in text for kw in CATEGORIES[cat]): return cat
        return '14. Sonstiges'

    df['Kategorie'] = df.apply(categorize, axis=1)
    df['Monat_Jahr'] = df['Buchungsdatum'].apply(lambda x: f"{GERMAN_MONTHS[x.month]} {x.year}")
    return df

# --- SIDEBAR & UPLOAD ---
st.sidebar.title("📁 Daten-Upload")
uploaded_file = st.sidebar.file_uploader("Buchungsliste.csv auswählen", type="csv")

if uploaded_file:
    df_all = process_csv(uploaded_file)
    labs = df_all.sort_values('Buchungsdatum')['Monat_Jahr'].unique().tolist()
    
    st.sidebar.divider()
    sel = st.sidebar.selectbox("Zeitraum wählen", options=labs, index=len(labs)-1)
    bal = st.sidebar.number_input("Aktueller Saldo App (€)", value=0.0, step=10.0)
    
    # --- BERECHNUNGEN ---
    m_df = df_all[df_all['Monat_Jahr'] == sel].copy()
    prev_lab = labs[labs.index(sel)-1] if labs.index(sel) > 0 else sel
    p_df = df_all[df_all['Monat_Jahr'] == prev_lab].copy()

    life_kats = [k for k in CATEGORIES.keys() if any(x in k for x in ['Spaß', 'Amazon', 'Wetten', 'Klarna'])]
    sum_inc = m_df[m_df['Kategorie'] == '00. Einnahmen (Gehalt & Co)']['Betrag'].sum()
    sum_life = abs(m_df[m_df['Kategorie'].isin(life_kats) & (m_df['Betrag'] < 0)]['Betrag'].sum())
    rem_life = max(0, LIMIT_LIFESTYLE - sum_life)
    sum_savings = abs(m_df[m_df['Kategorie'] == '07. Sparen']['Betrag'].sum())
    actual_growth = sum_inc - abs(m_df[m_df['Betrag'] < 0]['Betrag'].sum())
    sparquote = ((sum_savings + actual_growth) / sum_inc * 100) if sum_inc > 0 else 0

    # Wochenbudget
    today = datetime.now()
    last_day = (datetime(today.year, today.month % 12 + 1, 1) - timedelta(days=1)).day
    weeks_left = max(0.5, (last_day - today.day) / 7)

    # --- UI HEADER ---
    st.title(f"📊 Finanz-Cockpit: {sel}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo App", euro(bal))
    col2.metric("Sparquote", f"{sparquote:.1f} %")
    col3.metric("Wochen-Budget", euro(rem_life/weeks_left))

    # --- HAUPTTABELLE ---
    st.divider()
    def get_val(df_in, cat):
        v = df_in[df_in['Kategorie'] == cat]['Betrag'].sum()
        return v if 'Einnahmen' in cat else abs(v) if v < 0 else 0

    t_data = []
    for cat in sorted(CATEGORIES.keys()):
        cv, pv = get_val(m_df, cat), get_val(p_df, cat)
        t_data.append({'Kategorie': cat, 'Vormonat': euro(pv), 'Aktuell': euro(cv), 'Diff': f"{cv-pv:+,.2f} €"})
    
    st.table(pd.DataFrame(t_data))

    # --- LIFESTYLE SUMMARY (MOBILE OPTIMIZED) ---
    st.info(f"**Lifestyle-Budget:** {euro(sum_life)} verbraucht von {euro(LIMIT_LIFESTYLE)} (**Rest: {euro(rem_life)}**)")

    # --- DRILL DOWN ---
    st.subheader("🔍 Ursachen-Analyse")
    drill_cat = st.selectbox("Kategorie für Detail-Vergleich wählen", ["--- Bitte wählen ---"] + sorted(list(CATEGORIES.keys())))
    
    if drill_cat != "--- Bitte wählen ---":
        dm, dp = m_df[m_df['Kategorie'] == drill_cat].sort_values('Buchungsdatum'), p_df[p_df['Kategorie'] == drill_cat].sort_values('Buchungsdatum')
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            st.write(f"**{prev_lab}**")
            for _, r in dp.iterrows(): st.text(f"{r['Buchungsdatum'].strftime('%d.%m.')} {get_clean_name(r)}: {euro(r['Betrag'])}")
        with dcol2:
            st.write(f"**{sel}**")
            for _, r in dm.iterrows(): st.text(f"{r['Buchungsdatum'].strftime('%d.%m.')} {get_clean_name(r)}: {euro(r['Betrag'])}")

else:
    st.info("Bitte lade links in der Sidebar die Buchungsliste.csv hoch, um die App zu starten.")
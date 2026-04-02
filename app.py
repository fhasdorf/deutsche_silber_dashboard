# -*- coding: utf-8 -*-
# @Author: Frank Hasdorf

import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Mitbewerber Analyse | Deutsche Silber SE", layout="wide")

# --- 2. DATEN LADEN & BEREINIGEN ---
@st.cache_data
def load_data():
    csv_pfad = "bergrettigheter.csv" 
    try:
        df = pd.read_csv(csv_pfad, sep=';')
        if len(df.columns) == 1:
            df = pd.read_csv(csv_pfad, sep=',')
        
        df['Areal_m2'] = df['Areal_m2'].astype(str).str.replace(',', '.')
        df['Areal_m2'] = pd.to_numeric(df['Areal_m2'], errors='coerce')
        df['Areal_km2'] = df['Areal_m2'] / 1_000_000
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame()

df_lizenzen = load_data()

if df_lizenzen.empty:
    st.warning("Keine Daten geladen. Bitte prüfen, ob 'bergrettigheter.csv' im selben Ordner liegt.")
    st.stop()

# --- 3. LAYOUT & SIDEBAR ---
st.title("📊 Explorationsmarkt Norwegen: Mitbewerber-Analyse")
st.markdown("Interaktives Dashboard zur Identifikation der Marktführer im norwegischen Bergbausektor.")

st.sidebar.header("Filter")
alle_inhaber = sorted(df_lizenzen['Rettighetshaver'].dropna().unique().tolist())
ausgewaehlter_inhaber = st.sidebar.selectbox("Suche nach spezifischem Unternehmen:", ["Alle anzeigen"] + alle_inhaber)

# --- 4. ZENTRALES WÖRTERBUCH (Der Bugfix!) ---
# Das Wörterbuch muss hier oben stehen, damit die ganze App es kennt.
mineral_erweitert = {
    'Kobber': 'Kupfer', 'Gull': 'Gold', 'Sølv': 'Silber', 'Sink': 'Zink',
    'Bly': 'Blei', 'Kobolt': 'Kobalt', 'Nikkel': 'Nickel', 'Platina': 'Platin',
    'Jern': 'Eisen', 'REE': 'Seltene Erden (REE)', 'Titan': 'Titan',
    'Zirkonium': 'Zirkonium', 'Niob': 'Niob', 'Molybden': 'Molybdän', 'Arsen': 'Arsen'
}

# --- 5. DATEN-AGGREGATION TOP 10 ---
mitbewerber_stats = df_lizenzen.groupby('Rettighetshaver').agg(
    Anzahl_Lizenzen=('Rettighetsnummer', 'count'),
    Gesamtflaeche_km2=('Areal_km2', 'sum')
).reset_index()

top_10_player = mitbewerber_stats.sort_values(by='Gesamtflaeche_km2', ascending=False).head(10)

# --- 6. DASHBOARD BEREICH (OBEN): BALKENDIAGRAMM & TABELLE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Top 10 Player nach Fläche")
    fig_bar = px.bar(
        top_10_player, 
        x='Gesamtflaeche_km2', 
        y='Rettighetshaver', 
        orientation='h',
        hover_data=['Anzahl_Lizenzen'],
        labels={'Gesamtflaeche_km2': 'Fläche (km²)', 'Rettighetshaver': 'Unternehmen'},
        color='Gesamtflaeche_km2',
        color_continuous_scale='Blues'
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}) 
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("🔍 Detailansicht")
    if ausgewaehlter_inhaber == "Alle anzeigen":
        anzeige_df = top_10_player.rename(columns={
            'Rettighetshaver': 'Rechteinhaber',
            'Anzahl_Lizenzen': 'Anzahl Lizenzen',
            'Gesamtflaeche_km2': 'Fläche (km²)'
        })
        st.dataframe(anzeige_df, use_container_width=True, hide_index=True)
        
    else:
        st.write(f"**Details für {ausgewaehlter_inhaber}:**")
        gefilterte_df = df_lizenzen[df_lizenzen['Rettighetshaver'] == ausgewaehlter_inhaber]
        
        anzeige_detail_df = gefilterte_df[['Rettighetsnummer', 'Rettighetsnavn', 'Mineral', 'Areal_km2']].rename(columns={
            'Rettighetsnummer': 'Lizenznummer',
            'Rettighetsnavn': 'Projektname',
            'Mineral': 'Ziel-Mineralien',
            'Areal_km2': 'Fläche (km²)'
        })

        def uebersetze_komma_liste(mineral_string):
            if pd.isna(mineral_string): 
                return "Unbekannt"
            teile = str(mineral_string).split(',')
            uebersetzt = [mineral_erweitert.get(teil.strip(), teil.strip()) for teil in teile]
            return ", ".join(uebersetzt)

        anzeige_detail_df['Ziel-Mineralien'] = anzeige_detail_df['Ziel-Mineralien'].apply(uebersetze_komma_liste)
        st.dataframe(anzeige_detail_df, use_container_width=True, hide_index=True)

# --- 7. DASHBOARD BEREICH (UNTEN): MINERALIEN & LIZENZARTEN ---
st.markdown("---") 
st.subheader("⛏️ Portfolio-Analyse: Erze & Lizenzstatus")

df_minerals = df_lizenzen.copy()
df_minerals['Mineral'] = df_minerals['Mineral'].fillna('Unbekannt')
df_minerals['Mineral'] = df_minerals['Mineral'].astype(str).str.split(',')
df_exploded = df_minerals.explode('Mineral')
df_exploded['Mineral'] = df_exploded['Mineral'].str.strip() 

# Jetzt kennt Python mineral_erweitert hier unten problemlos!
df_exploded['Mineral'] = df_exploded['Mineral'].replace(mineral_erweitert)

if ausgewaehlter_inhaber != "Alle anzeigen":
    df_exploded = df_exploded[df_exploded['Rettighetshaver'] == ausgewaehlter_inhaber]
    df_types = df_lizenzen[df_lizenzen['Rettighetshaver'] == ausgewaehlter_inhaber]
else:
    df_types = df_lizenzen

col3, col4 = st.columns(2)

with col3:
    st.write(f"**Gesuchte Mineralien** ({ausgewaehlter_inhaber})")
    mineral_counts = df_exploded['Mineral'].value_counts().reset_index()
    mineral_counts.columns = ['Mineral', 'Anzahl Nennungen']
    
    fig_minerals = px.pie(
        mineral_counts.head(10),
        values='Anzahl Nennungen', 
        names='Mineral', 
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    st.plotly_chart(fig_minerals, use_container_width=True)

with col4:
    st.write(f"**Lizenzstatus** ({ausgewaehlter_inhaber})")
    type_counts = df_types['Rettighetstype'].value_counts().reset_index()
    type_counts.columns = ['Lizenzart', 'Anzahl']
    
    type_counts['Lizenzart'] = type_counts['Lizenzart'].replace({
        'UNDERSØKELSESRETT': 'Exploration (Untersuchung)',
        'UNDERSOEKELSESRETT': 'Exploration (Untersuchung)',
        'UTVINNINGSRETT': 'Abbau (Gewinnung)'
    })
    
    fig_types = px.bar(
        type_counts, 
        x='Anzahl', 
        y='Lizenzart', 
        orientation='h',
        color='Lizenzart',
        color_discrete_sequence=['#3186cc', '#ff9900']
    )
    fig_types.update_layout(showlegend=False)
    st.plotly_chart(fig_types, use_container_width=True)

# --- 8. FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; font-size: 14px; color: #6c757d;">
        <b>© 2026 Geodaten-Analyse | Frank Hasdorf</b><br>
        <i>Datenquelle: Direktoratet for mineralforvaltning (Norwegen)</i><br>
        <br>
        <span style="font-size: 12px;">Entwickelt mit 🐍 Python & 👑 Streamlit</span>
    </div>
    """, 
    unsafe_allow_html=True
)

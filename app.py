# -*- coding: utf-8 -*-
# @Author: Frank Hasdorf
# @Project: Deutsche Silber SE
# @Date:   02-04-2026 15:11:55
# @Last Modified by:   Frank Hasdorf
# @Last Modified time: 02-04-2026 16:08:19


import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Seiten-Konfiguration (Muss ganz oben stehen)
st.set_page_config(page_title="Mitbewerber Analyse | Deutsche Silber SE", layout="wide")

## 2. Daten laden (mit Cache für maximale Geschwindigkeit)
@st.cache_data
def load_data():
    csv_pfad = "bergrettigheter.csv"
    try:
        df = pd.read_csv(csv_pfad, sep=';')
        if len(df.columns) == 1:
            df = pd.read_csv(csv_pfad, sep=',')
        
        # Text bereinigen und in echte Zahlen umwandeln ---
        # 1. Kommas zu Punkten machen
        df['Areal_m2'] = df['Areal_m2'].astype(str).str.replace(',', '.')
        # 2. In eine Zahl (float) umwandeln, unlesbares zu NaN machen
        df['Areal_m2'] = pd.to_numeric(df['Areal_m2'], errors='coerce')
        
        # Mathe-Operation!
        df['Areal_km2'] = df['Areal_m2'] / 1_000_000
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame()

df_lizenzen = load_data()

# Sicherheits-Stopper, falls die Tabelle leer ist
if df_lizenzen.empty:
    st.warning("Keine Daten geladen. Bitte Pfad in app.py prüfen.")
    st.stop()

# 3. Layout der Web-App
st.title("📊 Explorationsmarkt Norwegen: Mitbewerber-Analyse")
st.markdown("Interaktives Dashboard zur Identifikation der Marktführer im norwegischen Bergbausektor.")

# --- SIDEBAR (Für interaktive Filter) ---
st.sidebar.header("Filter")
# Eine Liste aller einzigartigen Rechteinhaber erstellen
alle_inhaber = sorted(df_lizenzen['Rettighetshaver'].dropna().unique().tolist())
ausgewaehlter_inhaber = st.sidebar.selectbox("Suche nach spezifischem Unternehmen:", ["Alle anzeigen"] + alle_inhaber)

# --- DATEN-AGGREGATION ---
mitbewerber_stats = df_lizenzen.groupby('Rettighetshaver').agg(
    Anzahl_Lizenzen=('Rettighetsnummer', 'count'),
    Gesamtflaeche_km2=('Areal_km2', 'sum')
).reset_index()

top_10_player = mitbewerber_stats.sort_values(by='Gesamtflaeche_km2', ascending=False).head(10)

# --- DASHBOARD BEREICH ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Top 10 Player nach Fläche")
    # Interaktives Plotly-Balkendiagramm
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
    # Dreht das Diagramm um, damit der Größte oben ist
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}) 
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("🔍 Detailansicht")
    if ausgewaehlter_inhaber == "Alle anzeigen":
        # 1. Spalten für die Top 10 Übersicht übersetzen
        anzeige_df = top_10_player.rename(columns={
            'Rettighetshaver': 'Rechteinhaber',
            'Anzahl_Lizenzen': 'Anzahl Lizenzen',
            'Gesamtflaeche_km2': 'Fläche (km²)'
        })
        # Index ausblenden (die Nummern links) für einen saubereren Look
        st.dataframe(anzeige_df, use_container_width=True, hide_index=True)
        
    else:
        st.write(f"**Details für {ausgewaehlter_inhaber}:**")
        # Filtere die Originaldatenbank nach der Auswahl im Dropdown
        gefilterte_df = df_lizenzen[df_lizenzen['Rettighetshaver'] == ausgewaehlter_inhaber]
        
        # 2. Spalten für die Einzel-Unternehmensansicht übersetzen
        anzeige_detail_df = gefilterte_df[['Rettighetsnummer', 'Rettighetsnavn', 'Mineral', 'Areal_km2']].rename(columns={
            'Rettighetsnummer': 'Lizenznummer',
            'Rettighetsnavn': 'Projektname',
            'Mineral': 'Ziel-Mineralien',
            'Areal_km2': 'Fläche (km²)'
        })
        st.dataframe(anzeige_detail_df, use_container_width=True, hide_index=True)

        # --- NEUER ABSCHNITT: MINERALIEN & LIZENZARTEN ---
st.markdown("---") # Trennlinie für eine saubere Optik
st.subheader("⛏️ Portfolio-Analyse: Erze & Lizenzstatus")

# 1. Daten für die Mineralien vorbereiten (Das "Explode" Manöver)
df_minerals = df_lizenzen.copy()
df_minerals['Mineral'] = df_minerals['Mineral'].fillna('Unbekannt')
# Splitte die kommagetrennten Listen in echte Python-Listen
df_minerals['Mineral'] = df_minerals['Mineral'].astype(str).str.split(',')
# "Explodiere" die Listen in einzelne Zeilen
df_exploded = df_minerals.explode('Mineral')
# Entferne störende Leerzeichen (aus " Sølv" wird "Sølv")
df_exploded['Mineral'] = df_exploded['Mineral'].str.strip() 

# Übersetzung der norwegischen Erznamen ---
mineral_uebersetzung = {
    'Kobber': 'Kupfer',
    'Gull': 'Gold',
    'Sølv': 'Silber',
    'Sink': 'Zink',
    'Bly': 'Blei',
    'Kobolt': 'Kobalt',
    'Nikkel': 'Nickel',
    'Platina': 'Platin',
    'Jern': 'Eisen',
    'REE': 'Seltene Erden (REE)' # Rare Earth Elements
}
# Wendet das Wörterbuch auf die Spalte an
df_exploded['Mineral'] = df_exploded['Mineral'].replace(mineral_uebersetzung) 

# 2. Filtern basierend auf der Auswahl oben (Alle oder bestimmtes Unternehmen)
if ausgewaehlter_inhaber != "Alle anzeigen":
    df_exploded = df_exploded[df_exploded['Rettighetshaver'] == ausgewaehlter_inhaber]
    df_types = df_lizenzen[df_lizenzen['Rettighetshaver'] == ausgewaehlter_inhaber]
else:
    df_types = df_lizenzen

# 3. Zwei neue Spalten für die Diagramme bauen
col3, col4 = st.columns(2)

with col3:
    st.write(f"**Gesuchte Mineralien** ({ausgewaehlter_inhaber})")
    # Zähle, wie oft jedes Mineral vorkommt
    mineral_counts = df_exploded['Mineral'].value_counts().reset_index()
    mineral_counts.columns = ['Mineral', 'Anzahl Nennungen']
    
    # Ein schickes Donut-Diagramm
    fig_minerals = px.pie(
        mineral_counts.head(10), # Nur die Top 10, sonst wird es unübersichtlich
        values='Anzahl Nennungen', 
        names='Mineral', 
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    st.plotly_chart(fig_minerals, use_container_width=True)

with col4:
    st.write(f"**Lizenzstatus** ({ausgewaehlter_inhaber})")
    
    # Zähle die Lizenzarten
    type_counts = df_types['Rettighetstype'].value_counts().reset_index()
    type_counts.columns = ['Lizenzart', 'Anzahl']
    
    # Übersetze die norwegischen Fachbegriffe
    type_counts['Lizenzart'] = type_counts['Lizenzart'].replace({
        'UNDERSØKELSESRETT': 'Exploration (Untersuchung)',
        'UNDERSOEKELSESRETT': 'Exploration (Untersuchung)',
        'UTVINNINGSRETT': 'Abbau (Gewinnung)'
    })
    
    # Ein Balkendiagramm für den Status
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

    # --- FOOTER ---
st.markdown("---") # Optische Trennlinie
st.markdown(
    """
    <div style="text-align: center; font-size: 14px; color: #6c757d;">
        <b>© 2026 Geodaten-Analyse | Frank Hasdorf</b><br>
        <i>Datenquelle: Direktoratet For Mineralforvaltning (Norwegen)</i><br>
        <br>
        <span style="font-size: 12px;">Entwickelt mit 🐍 Python & 👑 Streamlit</span>
    </div>
    """, 
    unsafe_allow_html=True
)
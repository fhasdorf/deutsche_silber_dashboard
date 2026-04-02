import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Mitbewerber Analyse | Deutsche Silber SE", layout="wide")

# --- 2. DATEN LADEN & BEREINIGEN ---
@st.cache_data
def load_data():
    csv_pfad = "bergrettigheter.csv" # Relativer Pfad für den Streamlit-Server
    try:
        df = pd.read_csv(csv_pfad, sep=';')
        if len(df.columns) == 1:
            df = pd.read_csv(csv_pfad, sep=',')
        
        # Text bereinigen und in echte Zahlen umwandeln (Kommas zu Punkten)
        df['Areal_m2'] = df['Areal_m2'].astype(str).str.replace(',', '.')
        df['Areal_m2'] = pd.to_numeric(df['Areal_m2'], errors='coerce')
        
        # Fläche in km² berechnen
        df['Areal_km2'] = df['Areal_m2'] / 1_000_000
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame()

df_lizenzen = load_data()

# Sicherheits-Stopper, falls die Tabelle leer ist
if df_lizenzen.empty:
    st.warning("Keine Daten geladen. Bitte prüfen, ob 'bergrettigheter.csv' im selben Ordner liegt.")
    st.stop()

# --- 3. LAYOUT & SIDEBAR ---
st.title("📊 Explorationsmarkt Norwegen: Mitbewerber-Analyse")
st.markdown("Interaktives Dashboard zur Identifikation der Marktführer im norwegischen Bergbausektor.")

st.sidebar.header("Filter")
alle_inhaber = sorted(df_lizenzen['Rettighetshaver'].dropna().unique().tolist())
ausgewaehlter_inhaber = st.sidebar.selectbox("Suche nach spezifischem Unternehmen:", ["Alle anzeigen"] + alle_inhaber)

# --- 4. DATEN-AGGREGATION TOP 10 ---
mitbewerber_stats = df_lizenzen.groupby('Rettighetshaver').agg(
    Anzahl_Lizenzen=('Rettighetsnummer', 'count'),
    Gesamtflaeche_km2=('Areal_km2', 'sum')
).reset_index()

top_10_player = mitbewerber_stats.sort_values(by='Gesamtflaeche_km2', ascending=False).head(10)

# --- 5. DASHBOARD BEREICH (OBEN): BALKENDIAGRAMM & TABELLE ---
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
    # Dreht das Diagramm um, damit der Größte oben ist
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

        # Wörterbuch für die Übersetzung
        mineral_erweitert = {
            'Kobber': 'Kupfer', 'Gull': 'Gold', 'Sølv': 'Silber', 'Sink': 'Zink',
            'Bly': 'Blei', 'Kobolt': 'Kobalt', 'Nikkel': 'Nickel', 'Platina': 'Platin',
            'Jern': 'Eisen', 'REE': 'Seltene Erden (REE)', 'Titan': 'Titan',
            'Zirkonium': 'Zirkonium', 'Niob': 'Niob', 'Molybden': 'Molybdän', 'Arsen': 'Arsen'
        }

        # Funktion zur Übersetzung von Komma-Listen in der Tabelle
        def uebersetze_komma_liste(mineral_string):
            if pd.isna(mineral_string):

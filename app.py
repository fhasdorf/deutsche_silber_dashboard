# -*- coding: utf-8 -*-
# @Author: Frank Hasdorf
# @Project: Deutsche Silber SE
# @Last Modified by:   Frank Hasdorf

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import math
import geopandas as gpd

# --- 1. SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Mitbewerber Analyse | Deutsche Silber SE", layout="wide")

# --- 2. DATEN LADEN & BEREINIGEN (CSV) ---
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
        st.error(f"Fehler beim Laden der CSV-Daten: {e}")
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

# --- 4. ZENTRALES WÖRTERBUCH ---
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

# --- 8. WHITE SPOT ANALYSE & INTERAKTIVE KARTE (Cloud-Ready mit GeoJSON) ---
st.markdown("---")
st.header("🗺️ White Spot Analyse & Competitor Map")

# --- LAYER DEFINIEREN (Die extrahierten GeoJSON-Dateien) ---
verfuegbare_layer = ['MalmRegistrering_flate', 'MalmForekomst_flate']

def uebersetze_layer(layer_name):
    ersetzungen = {
        'MalmRegistrering_flate': 'Erz-Registrierungen (Flächen)',
        'MalmForekomst_flate': 'Erz-Vorkommen (Flächen)'
    }
    return ersetzungen.get(layer_name, layer_name)

# --- SIDEBAR ERWEITERUNG ---
st.sidebar.markdown("---")
st.sidebar.subheader("Karten-Optionen")
show_competitors = st.sidebar.checkbox("Reale Geo-Polygone anzeigen", value=False)

gewaehlter_layer = None
if show_competitors:
    gewaehlter_layer = st.sidebar.selectbox(
        "Welchen Geodaten-Layer laden?", 
        verfuegbare_layer, 
        format_func=uebersetze_layer
    )

show_infrastructure = st.sidebar.checkbox("Infrastruktur (Häfen) anzeigen", value=False)

# 1. Daten und Proxy-Scoring (Unsere White Spots)
silber_proxies = ['Blei', 'Zink', 'Kupfer', 'Antimon', 'Arsen', 'Galenit', 'Sphalerit']

data_spots = {
    'Spot_Name': ['Stordø', 'Ulriksdal', 'Nyseter', 'Gravdal'],
    'Lat': [59.78, 63.45, 60.55, 60.38], 
    'Lon': [5.50, 10.12, 9.85, 5.32],
    'Historische_Funde': ['Kupfer, Zink, Pyrit', 'Eisen, Kupfer', 'Zink, Blei, Silber', 'Kupfer, Zink, Blei']
}
df_spots = pd.DataFrame(data_spots)

def berechne_proxy_score(funde):
    score = 0
    gefundene = []
    for p in silber_proxies:
        if p.lower() in funde.lower():
            score += 1
            gefundene.append(p)
    return score, ", ".join(gefundene)

df_spots[['Proxy_Score', 'Gematchte_Proxies']] = df_spots['Historische_Funde'].apply(
    lambda x: pd.Series(berechne_proxy_score(x))
)

# 2. Leichte GeoJSON laden 
@st.cache_data
def load_geodata(layer_name):
    if not layer_name: return None
    
   
    geojson_pfad = f"geodaten/{layer_name}.geojson" 
    
    try:
        gdf = gpd.read_file(geojson_pfad)
        
        for col in gdf.columns:
            if col != 'geometry':
                gdf[col] = gdf[col].astype(str)
                
        return gdf
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei {geojson_pfad}: {e}")
        return None

gdf_lizenzen = load_geodata(gewaehlter_layer) if show_competitors else None

if show_competitors and gdf_lizenzen is not None:
    st.sidebar.success(f"✅ {len(gdf_lizenzen)} Geo-Objekte blitzschnell geladen!")

# 3. KARTE INITIALISIEREN
m = folium.Map(location=[61.5, 8.5], zoom_start=6, tiles='OpenStreetMap')

# LAYER: White Spots & 30-km-Radius
fg_spots = folium.FeatureGroup(name="White Spots (Targets)")
for idx, row in df_spots.iterrows():
    folium.Marker(
        location=[row['Lat'], row['Lon']],
        popup=f"<b>{row['Spot_Name']}</b><br>Score: {row['Proxy_Score']}/7<br>Proxies: {row['Gematchte_Proxies']}",
        tooltip=f"🎯 Target: {row['Spot_Name']}",
        icon=folium.Icon(color='red', icon='star')
    ).add_to(fg_spots)
    
    folium.Circle(
        location=[row['Lat'], row['Lon']],
        radius=30000, 
        color='green',
        weight=2,
        fill=True,
        fill_opacity=0.05,
        tooltip="30 km Explorationsradius"
    ).add_to(fg_spots)
fg_spots.add_to(m)

# LAYER: Reale Konkurrenz-Polygone aus GeoJSON
if show_competitors and gdf_lizenzen is not None and not gdf_lizenzen.empty:
    fg_comp = folium.FeatureGroup(name=f"Geo-Layer: {gewaehlter_layer}")
    folium.GeoJson(
        gdf_lizenzen,
        name="Lizenzen",
        style_function=lambda feature: {
            'fillColor': 'orange',
            'color': 'darkorange',
            'weight': 1,
            'fillOpacity': 0.4,
        }
    ).add_to(fg_comp)
    fg_comp.add_to(m)

# LAYER: Infrastruktur
if show_infrastructure:
    fg_infra = folium.FeatureGroup(name="Logistik")
    haefen = {'Hafen Bergen': [60.39, 5.32], 'Hafen Trondheim': [63.44, 10.40], 'Hafen Mo i Rana': [66.31, 14.14]}
    for name, coords in haefen.items():
        folium.Marker(location=coords, popup=name, icon=folium.Icon(color='gray', icon='ship', prefix='fa')).add_to(fg_infra)
    fg_infra.add_to(m)

folium.LayerControl().add_to(m)

# 4. Anzeige in Streamlit
col_map1, col_map2 = st.columns([1, 2])

with col_map1:
    st.subheader("Target-Bewertung")
    df_display = df_spots[['Spot_Name', 'Proxy_Score', 'Gematchte_Proxies']].sort_values(by='Proxy_Score', ascending=False)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.info("Der grüne 30-km-Radius zeigt unsere strategische Pufferzone. Lizenzen innerhalb dieses Bereichs konkurrieren um dieselbe geologische Formation und Infrastruktur.")

with col_map2:
    st_folium(m, width=800, height=500, returned_objects=[])
    
    st.info("""
    **🗺️ Kartenlegende:** ⭐ **Rote Sterne:** Unsere White Spots (Targets)  
    🟢 **Grüne Zonen:** 30 km strategischer Explorationsradius  
    🟧 **Orange Flächen:** Reale Erzvorkommen (aus norwegischen Geodaten)  
    🛣️ **Autobahnen / Bahnstrecken:** Gelbe & gestrichelte Linien (OpenStreetMap)
    """)

# --- 9. FOOTER ---
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

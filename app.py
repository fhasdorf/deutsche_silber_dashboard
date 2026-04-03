# -*- coding: utf-8 -*-
# @Author: Frank Hasdorf
# @Date:   02-04-2026 15:11:55
# @Last Modified by:   Frank Hasdorf
# @Last Modified time: 03-04-2026 17:48:10


def main():
    print("Hello, World!")


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
# @Author: Frank Hasdorf
# @Project: Deutsche Silber SE - Professional Business Intelligence

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
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
        
        df['Rettighetshaver'] = df['Rettighetshaver'].fillna('Unbekannt').astype(str).str.strip()
        df['Areal_m2'] = df['Areal_m2'].astype(str).str.replace(',', '.')
        df['Areal_m2'] = pd.to_numeric(df['Areal_m2'], errors='coerce').fillna(0)
        df['Areal_km2'] = df['Areal_m2'] / 1_000_000
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der CSV-Daten: {e}")
        return pd.DataFrame()

df_lizenzen = load_data()

# --- 3. SIDEBAR & FILTER ---
st.sidebar.header("Analyse-Filter")
namen_liste = sorted(df_lizenzen['Rettighetshaver'].unique().tolist())
ausgewaehlter_inhaber = st.sidebar.selectbox("Unternehmen wählen:", ["Alle anzeigen"] + namen_liste)

# --- 4. ZENTRALES WÖRTERBUCH & PROXY-LOGIK ---
mineral_erweitert = {
    'Kobber': 'Kupfer', 'Gull': 'Gold', 'Sølv': 'Silber', 'Sink': 'Zink',
    'Bly': 'Blei', 'Kobolt': 'Kobalt', 'Nikkel': 'Nickel', 'Platina': 'Platin',
    'Jern': 'Eisen', 'REE': 'Seltene Erden (REE)', 'Titan': 'Titan'
}
silber_proxies = ['Blei', 'Zink', 'Kupfer', 'Antimon', 'Arsen', 'Galenit', 'Sphalerit']

# --- 5. DATEN-AGGREGATION ---
if ausgewaehlter_inhaber == "Alle anzeigen":
    df_filtered = df_lizenzen
else:
    suche = ausgewaehlter_inhaber.lower().strip()
    df_filtered = df_lizenzen[df_lizenzen['Rettighetshaver'].str.lower().str.strip() == suche]

mitbewerber_stats = df_lizenzen.groupby('Rettighetshaver')['Areal_km2'].sum().reset_index()
top_10_player = mitbewerber_stats.sort_values(by='Areal_km2', ascending=False).head(10)

# --- 6. DASHBOARD (OBEN) ---
st.title("📊 Explorationsmarkt Norwegen: Mitbewerber-Analyse")
c1, c2 = st.columns(2)

with c1:
    if ausgewaehlter_inhaber == "Alle anzeigen":
        st.subheader("🏆 Top 10 Unternehmen nach Fläche")
        st.plotly_chart(px.bar(top_10_player, x='Areal_km2', y='Rettighetshaver', orientation='h', color='Areal_km2', color_continuous_scale='Blues'), use_container_width=True)
    else:
        st.subheader(f"📊 Kennzahlen: {ausgewaehlter_inhaber}")
        flaeche = df_filtered['Areal_km2'].sum()
        m1, m2 = st.columns(2)
        m1.metric("Lizenzen", len(df_filtered))
        m2.metric("Gesamtfläche", f"{flaeche:.2f} km²")
        avg_f = mitbewerber_stats['Areal_km2'].mean()
        st.plotly_chart(px.bar(pd.DataFrame({'Kat': [ausgewaehlter_inhaber, 'Markt-Ø'], 'km2': [flaeche, avg_f]}), x='Kat', y='km2', color='Kat'), use_container_width=True)

with c2:
    st.subheader("🔍 Projekt-Details")
    st.dataframe(df_filtered[['Rettighetsnummer', 'Rettighetsnavn', 'Mineral', 'Areal_km2']].head(50), use_container_width=True, hide_index=True)

# --- 7. WHITE SPOT ANALYSE DATEN ---
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

df_spots[['Proxy_Score', 'Gematchte_Proxies']] = df_spots['Historische_Funde'].apply(lambda x: pd.Series(berechne_proxy_score(x)))

# --- 8. KARTE & GEO-DATEN ---
st.markdown("---")
st.header("🗺️ White Spot Analyse & Competitor Map")

show_geo = st.sidebar.checkbox("Reale Flächen (Geo-Polygone) laden", value=False)

@st.cache_data
def load_geodata(layer_name):
    try:
        path = f"geodaten/{layer_name}.geojson"
        gdf = gpd.read_file(path)
        for col in gdf.columns:
            if col != 'geometry': gdf[col] = gdf[col].astype(str)
        return gdf
    except: return None

m = folium.Map(location=[61.5, 8.5], zoom_start=6)

# White Spots (Targets) mit dem 30km Radius
fg_spots = folium.FeatureGroup(name="Unsere Targets")
for _, row in df_spots.iterrows():
    folium.Marker(
        [row['Lat'], row['Lon']],
        popup=f"<b>{row['Spot_Name']}</b><br>Score: {row['Proxy_Score']}/7<br>Funde: {row['Gematchte_Proxies']}",
        tooltip=f"🎯 Target: {row['Spot_Name']}",
        icon=folium.Icon(color='red', icon='star')
    ).add_to(fg_spots)
    folium.Circle([row['Lat'], row['Lon']], radius=30000, color='green', weight=2, fill=True, fill_opacity=0.05).add_to(fg_spots)
fg_spots.add_to(m)

if show_geo:
    lay = st.sidebar.selectbox("Layer:", ['konkurrenz_claims', 'MalmRegistrering_flate', 'MalmForekomst_flate'])
    gdf = load_geodata(lay)
    if gdf is not None and not gdf.empty:
        # Element 29 Fix (Karten-Filter)
        if lay == 'konkurrenz_claims' and ausgewaehlter_inhaber != "Alle anzeigen":
            c_col = [c for c in gdf.columns if c.lower() in ['rettighetsh', 'rettighethaver']]
            if c_col:
                gdf = gdf[gdf[c_col[0]].str.lower().str.contains(ausgewaehlter_inhaber.lower(), na=False)]
        folium.GeoJson(gdf, style_function=lambda x: {'fillColor': 'orange', 'color': 'red', 'weight': 1}).add_to(m)

# Anzeige: Tabelle links, Karte rechts
cm1, cm2 = st.columns([1, 2])
with cm1:
    st.subheader("Target-Bewertung")
    st.dataframe(df_spots[['Spot_Name', 'Proxy_Score', 'Gematchte_Proxies']].sort_values(by='Proxy_Score', ascending=False), use_container_width=True, hide_index=True)
    st.info("Der grüne 30-km-Radius zeigt unsere strategische Pufferzone.")
with cm2:
    st_folium(m, width=800, height=500, returned_objects=[])

# --- 9. FOOTER ---
st.markdown("---")
st.markdown("<div style='text-align: center; font-size: 12px; color: grey;'>© 2026 Deutsche Silber SE | Frank Hasdorf</div>", unsafe_allow_html=True)

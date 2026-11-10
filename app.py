import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Électricité - 12 Quartiers",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Analyse de la consommation électrique dans 12 quartiers")
st.markdown("""
Ce tableau de bord présente l'analyse de deux ans de relevés (2024-2025) pour 12 quartiers de Port-au-Prince, 
Delmas, Pétion-Ville et Cap-Haïtien afin de déterminer si la consommation suit la chaleur ou les heures de courant.
""")

@st.cache_data
def load_data():
    df = pd.read_csv("donnees/consommation_propre.csv")
    df['mois'] = pd.to_datetime(df['mois'])
    df['annee'] = df['mois'].dt.year.astype(str)
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("Le fichier `donnees/consommation_propre.csv` est introuvable. Veuillez exécuter le notebook `exploration.ipynb` pour le générer.")
    st.stop()

st.sidebar.header("Filtres de navigation")

communes_disponibles = sorted(df['commune'].unique())
communes_selectionnees = st.sidebar.multiselect(
    "Sélectionnez les communes",
    options=communes_disponibles,
    default=communes_disponibles
)

annees_disponibles = sorted(df['annee'].unique(), reverse=True)
annee_selectionnee = st.sidebar.selectbox(
    "Sélectionnez l'année",
    options=annees_disponibles,
    index=0 if "2025" in annees_disponibles else 0
)

if not communes_selectionnees:
    st.warning("Veuillez sélectionner au moins une commune dans la barre latérale.")
    st.stop()

df_filtre = df[(df['commune'].isin(communes_selectionnees)) & (df['annee'] == str(annee_selectionnee))]

st.subheader(f"Indicateurs clés - Année {annee_selectionnee}")

total_kwh = df_filtre['kwh'].sum()

df_quartier_unique = df_filtre.drop_duplicates(subset=['quartier'])
total_abonnes = df_quartier_unique['abonnes'].sum()
kwh_par_abonne = total_kwh / total_abonnes if total_abonnes > 0 else 0

moy_heures_courant = df_filtre['heures_courant'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Consommation totale", f"{total_kwh / 1e6:.2f} millions kWh")
col2.metric("Consommation par abonné", f"{kwh_par_abonne:.1f} kWh")
col3.metric("Heures de courant (moyenne)", f"{moy_heures_courant:.1f} h")

tabs = st.tabs([
    "Chaleur ou courant ?", 
    "Comparaison par commune", 
    "Consommation par quartier", 
    "Heures Courant", 
    "Plus grandes consommations"
])

with tabs[0]:
    st.markdown("### Chaleur vs Heures de courant")
    st.write("Analyse de l'influence respective de la température et de la disponibilité du réseau sur la consommation.")
    st.info("💡 **Constat clé :** Les corrélations montrent une forte dépendance aux heures de courant (0.76) par rapport à la température (-0.15).")
    
    scatter = alt.Chart(df_filtre).mark_circle(size=70).encode(
        x=alt.X('heures_courant:Q', title='Heures de courant'),
        y=alt.Y('kwh:Q', title='Consommation (kWh)'),
        color='commune:N',
        tooltip=['quartier', 'commune', 'kwh', 'heures_courant']
    ).interactive()
    st.altair_chart(scatter, use_container_width=True)
    
    corr_c = df[df['type'] == 'Résidentiel']['kwh_par_abonne'].corr(df[df['type'] == 'Résidentiel']['heures_courant'])
    corr_t = df[df['type'] == 'Résidentiel']['kwh_par_abonne'].corr(df[df['type'] == 'Résidentiel']['temperature_c'])
    st.metric("Corrélations avec le Courant et avec la Température", f"{corr_c:.2f} et {corr_t:.2f}")

with tabs[1]:
    st.markdown("### Comparaison de la consommation par commune")
    st.title("Evolution de la consommation par commune")
    evolution_mois = df.pivot_table(index="mois", columns="commune", values="kwh_par_abonne")
    st.line_chart(evolution_mois)
    
    evolution_annee = df.pivot_table(index=["commune"], columns="annee", values="kwh", aggfunc="sum")
    evolution_annee["hausse_%"] = ((evolution_annee["2025"] / evolution_annee["2024"] - 1) * 100).round(1)
    
    hausse_max = evolution_annee.nlargest(1, "hausse_%")
    nom_commune = hausse_max.index[0]
    val_hausse = hausse_max.iloc[0]["hausse_%"]
    signe = "+" if val_hausse >= 0 else ""
    st.metric("Plus grande hausse", f"{nom_commune} {signe}{val_hausse}%")

with tabs[2]:
    st.markdown("### Consommation par quartier")
    quartier_agg = df_filtre.groupby('quartier')['kwh_par_abonne'].mean().sort_values(ascending=False)
    st.bar_chart(quartier_agg)
    
    types_agg = df.groupby("type")["kwh_par_abonne"].mean().round(1)
    comm_val = types_agg.get('Commercial', 0)
    res_val = types_agg.get('Résidentiel', 0)
    st.metric("Consommations moyenne par abonné par type pour 2025", f"Commercial : {comm_val} kWh et Résidentiel : {res_val} kWh")

with tabs[3]:
    st.markdown("### Heures Courant")
    cap_infos = df[df["commune"] == "Cap-Haïtien"]["heures_courant"]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    cap_infos.plot(kind="hist", edgecolor="white", bins=15, ax=ax)
    ax.set_title("Répartition des Heures courant au Cap-Haïtien")
    ax.set_xlabel("Heures de courant")
    ax.set_ylabel("Fréquence")
    ax.grid(True)
    st.pyplot(fig)

    nb_releves = len(copy_df := df.copy()[
        (df['mois'].dt.year == 2025) & (df['heures_courant'] < 8)
    ])
    st.metric("Relevés sous 8 heures en 2025", f"{nb_releves} relevés")

with tabs[4]:
    st.markdown("### Plus grandes consommations")
    top3 = df.nlargest(3, "kwh")[["mois", "quartier", "kwh"]].copy()
    top3["label"] = top3["quartier"] + " - " + top3["mois"].dt.strftime('%Y-%m')
    st.bar_chart(top3, x="label", y="kwh")

st.markdown("---")
st.markdown("### Conclusion générale")
st.markdown("""
**Réponse finale :** La consommation électrique des 12 quartiers suit en priorité **les heures de courant** (corrélation de **0.76**) plutôt que la chaleur (corrélation de **-0.15**). L'accès physique à l'électricité dicte l'essentiel de la demande énergétique globale sur la période étudiée.
""")

with st.expander("🔍 Afficher les données filtrées (Détails tabulaires)"):
    st.dataframe(df_filtre)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 17:40:43 2026

@author: fcvmathieu
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 27 13:16:14 2025

@author: fcvmathieu
"""

import streamlit as st
import pandas as pd
import datetime
import os
import pickle
from io import BytesIO
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import plotly.graph_objects as go
from urllib.parse import quote
from statsbombpy import sb
import requests_cache
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
import plotly.express as px
import seaborn as sns
import base64
import uuid
import json
from pathlib import Path
import requests
from fpdf import FPDF
import tempfile
import base64
import unicodedata
from scipy.stats import zscore


def check_scout_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Recrutement | Accès Sécurisé")
        id_input = st.text_input("Identifiant :", type="password")
        if st.button("Connexion"):
            if id_input == "ernesto":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Identifiant incorrect. Essayez encore.")
        st.stop()  # Stop rest of script if not logged in

check_scout_login()



# Display the club logo from GitHub at the top right
logo_url = ''
col1, col2 = st.columns([9, 1])
with col1:
    st.title("Recrutement | Ernesto")
with col2:
    st.image(logo_url, use_container_width=True)
    
st.markdown("<hr style='border:1px solid #ddd' />", unsafe_allow_html=True)

# ---- Statsbomb ----


DEFAULT_CREDS = {
    "user": "mathieu.feigean@fcversailles.com",
    "passwd": "uVBxDK5X",
}

# Looking at all competitions to search for comp and season id
comp = sb.competitions(creds = DEFAULT_CREDS)

# Disable caching to avoid SQLite errors
sb.CACHE_ENABLED = False  
session = requests_cache.CachedSession(backend="memory")

df1 = sb.player_season_stats(competition_id=129, season_id=318,creds = DEFAULT_CREDS)
df2 = sb.player_season_stats(competition_id=7, season_id=318,creds = DEFAULT_CREDS)
df3 = sb.player_season_stats(competition_id=8, season_id=318,creds = DEFAULT_CREDS)
df4 = sb.player_season_stats(competition_id=177, season_id=318,creds = DEFAULT_CREDS)
df5 = sb.player_season_stats(competition_id=63, season_id=318,creds = DEFAULT_CREDS)


data = pd.concat([df1, df2,df3,df4,df5], ignore_index=True)

cols_to_drop = [
    'account_id', 'player_id', 'team_id', 'competition_id', 'season_id', 
    'country_id', 'player_female', 'player_first_name', 'player_last_name', 'player_known_name'
]

existing_cols = [col for col in cols_to_drop if col in data.columns]

if missing := list(set(cols_to_drop) - set(existing_cols)):
    st.warning(f"Colonnes absentes ignorées : {missing}")

data = data.drop(columns=existing_cols)



# Remove the "player_season_" prefix from applicable column names
updated_columns = {col: col.replace("player_season_", "") for col in data.columns if col.startswith("player_season_")}
data.rename(columns=updated_columns, inplace=True)

data = data.dropna(axis=1, how='all')

data['birth_date1'] = pd.to_datetime(data['birth_date'], errors='coerce').dt.year
data['birth_date1'] = data['birth_date1'].astype(float).astype('Int64')

# Create age column
current_year = datetime.datetime.now().year  # Use full module reference
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
data['age'] = current_year - data['birth_date1']
data = data.drop(columns=['birth_date1'])

column_order = (
    ['player_name', 'primary_position', 'secondary_position', 
     'team_name', 'competition_name','season_name', 
     'birth_date','age', 'player_weight', 
     'player_height', 'minutes', 'starting_appearances', 'appearances', 'average_minutes', 'most_recent_match', '90s_played'] + 
    [col for col in data.columns if col not in [
    'player_name', 'primary_position', 'secondary_position', 
    'team_name', 'competition_name','season_name',
    'birth_date','age', 'player_weight', 
    'player_height', 'minutes', 'starting_appearances', 'appearances', 'average_minutes', 'most_recent_match', '90s_played']]
)

data = data[column_order]


params = st.query_params
default_page = params.get("page", "Statsbomb")
PAGES = ["Statsbomb"]
page = st.sidebar.selectbox("Select Page", PAGES, index=PAGES.index(default_page))


if page == "Statsbomb":
    st.title("Statsbomb")

    def plot_scatter(df, players, x_col, y_col, x_label, y_label, title):
        x_median = df[x_col].median()
        y_median = df[y_col].median()
    
        # Séparer joueurs sélectionnés et non sélectionnés
        df_highlight = df[df["Name"].isin(players)]
        df_normal = df[~df["Name"].isin(players)]
    
        fig = go.Figure()
    
        # 🔵 Points normaux (par compétition)
        for comp in df_normal["competition_name"].unique():
            df_comp = df_normal[df_normal["competition_name"] == comp]
            fig.add_trace(go.Scatter(
                x=df_comp[x_col],
                y=df_comp[y_col],
                mode='markers',
                name=comp,
                marker=dict(size=8, opacity=0.7),
                text=df_comp["Name"],
                hovertemplate=(
                    f"<b>%{{text}}</b><br>{x_label}: %{{x:.2f}}<br>{y_label}: %{{y:.2f}}<extra></extra>"
                )
            ))
    
        # ⚫ Joueurs sélectionnés
        fig.add_trace(go.Scatter(
            x=df_highlight[x_col],
            y=df_highlight[y_col],
            mode='markers+text',
            name="Joueurs sélectionnés",
            marker=dict(size=12, color="black", line=dict(width=1, color="white")),
            text=df_highlight["Name"].apply(lambda x: x.split()[-1]),  # affiche juste le nom
            textposition="top center",
            hovertemplate=(
                f"<b>%{{text}}</b><br>{x_label}: %{{x:.2f}}<br>{y_label}: %{{y:.2f}}<extra></extra>"
            )
        ))
    
        # ➕ Lignes médianes
        fig.add_vline(
            x=x_median,
            line=dict(color="gray", dash="dash", width=1),
            annotation_text=f"Médiane {x_label}: {x_median:.2f}",
            annotation_position="top left"
        )
        fig.add_hline(
            y=y_median,
            line=dict(color="gray", dash="dash", width=1),
            annotation_text=f"Médiane {y_label}: {y_median:.2f}",
            annotation_position="bottom right"
        )
    
        # Mise en page
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            legend_title="Compétition",
            height=700,
            template="simple_white"
        )
    
        return fig
    
    # Dictionnaire des compétences
    competences_dict = {
        "Création des occasions": ("np_xg_90", "xa_90"),
        "Qualité de Dribble": ("dribbles_90", "dribble_ratio"),
        "Etat de confiance": ("npxgxa_90", "over_under_performance_90"),
        "Qualité de tirs": ("obv_shot_90", "np_psxg_90"),
        "Faire progresseur le jeu vers l'avant": ("carry_length", "deep_progressions_90"),
        "Agir le plus proche possible du but": ("op_passes_into_and_touches_inside_box_90", "deep_completions_90"),
        "Capacité à conserver le ballon": ("change_in_passing_ratio", "turnovers_90"),
        "Création de danger": ("obv_dribble_carry_90", "obv_pass_90"),
        "Intensité sans ballon": ("average_x_pressure", "counterpressures_90"),
        "Pressing": ("padj_pressures_90", "pressure_regains_90"),
        "Récupérer des ballons": ("ball_recoveries_90", "padj_interceptions_90"),
        "Duels Aérien": ("aerial_wins_90", "aerial_ratio")
    }

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        competition = st.multiselect("Compétition", data["competition_name"].dropna().unique())
    
    with col2:
        ordered_positions = ['Goalkeeper','Centre Back','Right Centre Back','Left Centre Back','Right Back','Left Back','Left Wing Back','Right Wing Back', 'Centre Defensive Midfielder',
                             'Right Defensive Midfielder','Left Defensive Midfielder','Right Centre Midfielder','Left Centre Midfielder', 'Right Midfielder','Left Midfielder',
                             'Centre Attacking Midfielder','Right Attacking Midfielder','Left Attacking Midfielder','Left Wing','Right Wing', 
                             'Centre Forward','Right Centre Forward','Left Centre Forward']

        available_positions = [pos for pos in ordered_positions if pos in data["primary_position"].unique()]
        position = st.multiselect("Position principale", available_positions)

    with col3:
        age = st.slider(
            "Âge",
            min_value=int(data["age"].min()),
            max_value=int(data["age"].max()),
            value=(int(data["age"].min()), int(data["age"].max()))
        )
    
    with col4:
        minutes = st.slider(  # ⚠️ ici on appelle la variable "minutes" (pas min_minutes)
            "Minutes",
            min_value=int(data["minutes"].min()),
            max_value=int(data["minutes"].max()),
            value=(int(data["minutes"].min()), int(data["minutes"].max()))
        )
    

    filtered_data = data.copy()
    if competition:
        filtered_data = filtered_data[filtered_data["competition_name"].isin(competition)]
    if position:
        filtered_data = filtered_data[filtered_data["primary_position"].isin(position)]

    filtered_data = filtered_data[
        (filtered_data["age"] >= age[0]) &
        (filtered_data["age"] <= age[1]) &
        (filtered_data["minutes"] >= minutes[0]) &
        (filtered_data["minutes"] <= minutes[1])
    ]
    
       # Liste des joueurs disponibles après filtre
    available_players = filtered_data["player_name"].unique()
    
    # Session state pour conserver la sélection des joueurs
    if "player_selection" not in st.session_state:
        st.session_state.player_selection = []
    
    # Liste fusionnée : joueurs disponibles + ceux déjà sélectionnés
    merged_players = list(set(available_players).union(set(st.session_state.player_selection)))
    
    # Multiselect avec persistance
    player_selection = st.multiselect(
        "Choisis les joueurs à mettre en valeur",
        options=merged_players,
        default=st.session_state.player_selection
    )
    
    # Mise à jour de la session
    st.session_state.player_selection = player_selection


    selected_competence = st.selectbox("Choisis une compétence à analyser", list(competences_dict.keys()))
    x_col, y_col = competences_dict[selected_competence]


    if not filtered_data.empty:
        df_for_plot = filtered_data.rename(columns={"player_name": "Name"})  # plus besoin de Season
        fig = plot_scatter(df_for_plot, player_selection, x_col, y_col, x_col, y_col, selected_competence)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        
        
    chosen_variables = [
        "counterpressures_90", "aggressive_actions_90",
        "aerial_wins_90", "aerial_ratio",
        "change_in_passing_ratio", "turnovers_90",
        "padj_tackles_90", "padj_interceptions_90",
        "blocks_per_shot", "padj_clearances_90",
        "passing_ratio", "dispossessions_90",
        "carries_90", "carry_length",
        "forward_pass_proportion", "obv_pass_90",
        "dribbled_past_90", "dribble_faced_ratio",
        "crosses_90", "xa_90",
        "shot_touch_ratio", "touches_inside_box_90",
        "np_psxg_90", "obv_shot_90",
        "total_dribbles_90", "obv_dribble_carry_90",
        "defensive_action_regains_90", "pressure_regains_90",
        "np_xg_90", "np_xg_per_shot","xs_ratio","sp_xa_90","sp_key_passes_90","gsaa_90","obv_defensive_action_90","ball_recoveries_90","deep_progressions_90","op_f3_passes_90"
    ]
    
    column_mappings = {
        "Agresseur": ["counterpressures_90", "aggressive_actions_90"],
        "Header": [ "aerial_wins_90", "aerial_ratio"],
        "Technicien": ["change_in_passing_ratio", "turnovers_90"],
        "Defender": ["padj_tackles_90", "padj_interceptions_90"],
        "Protecteur": ["blocks_per_shot", "padj_clearances_90"],
        "Annihilateur": ["obv_defensive_action_90", "ball_recoveries_90"],
        "Conserver": ["passing_ratio", "dispossessions_90"],
        "Progress": ["carries_90", "carry_length"],
        "Pass": ["forward_pass_proportion", "obv_pass_90"],
        "1v1": ["dribbled_past_90", "dribble_faced_ratio"], 
        "Assist": ["crosses_90", "xa_90"],     
        "Box": ["shot_touch_ratio", "touches_inside_box_90"],
        "Tireur": ["np_psxg_90", "obv_shot_90"],
        "Percuteur": ["total_dribbles_90", "obv_dribble_carry_90"],
        "Recuperateur": ["defensive_action_regains_90", "pressure_regains_90"],
        "Striker": ["np_xg_90", "np_xg_per_shot"],
        "GK": ["xs_ratio", "gsaa_90"],
        "Set Pieces": ["sp_xa_90","sp_key_passes_90"],
        "Last third": ["deep_progressions_90","op_f3_passes_90"]
    }
    
     
    
    # 🛑 Variables pour lesquelles un score élevé est négatif
    negatively_correlated = [
        "turnovers_90", "dispossessions_90", "dribbled_past_90"
    ]
    
    zscore_df = filtered_data[['player_name', 'primary_position']].copy()
    for var in chosen_variables:
        if var in filtered_data.columns:
            values = filtered_data[var]
            if var in negatively_correlated:
                zscore_df[var] = -zscore(values, nan_policy="omit")
            else:
                zscore_df[var] = zscore(values, nan_policy="omit")
        else:
            st.warning(f"⚠️ Colonne introuvable : {var}")
        
    # 🧮 Création des profils
    aggregated_df = zscore_df[['player_name', 'primary_position']].copy()
    for profile, cols in column_mappings.items():
        if cols[0] in zscore_df.columns and cols[1] in zscore_df.columns:
            aggregated_df[profile] = zscore_df[cols[0]] + zscore_df[cols[1]]
    
    aggregated_df["Total Score"] = aggregated_df[list(column_mappings.keys())].sum(axis=1)
    
    # ✅ Renommer pour affichage
    aggregated_df = aggregated_df.rename(columns={
        "player_name": "Name",
        "primary_position": "Position"
    })
    
    # ➕ Ajout de la compétition pour styliser
    aggregated_df = aggregated_df.merge(
        filtered_data[["player_name", "competition_name"]],
        how="left",
        left_on="Name",
        right_on="player_name"
    )
    aggregated_df.drop(columns=["player_name"], inplace=True)
    
        # 📋 Choix des profils à afficher
        # 📋 Choix des profils à afficher
    selected_profiles = st.multiselect(
        "Selectionner compétences:",
        options=list(column_mappings.keys()),
        default=["Agresseur", "Defender", "Striker"]
    )

    if selected_profiles:
        # Coefficients personnalisés pour chaque profil sélectionné
        st.markdown("##### Pondération des profils sélectionnés")
        profile_weights = {}
        cols = st.columns(5)
        for idx, profile in enumerate(selected_profiles):
            with cols[idx % 5]:
                profile_weights[profile] = st.number_input(
                    f"{profile} :", min_value=0.0, max_value=10.0, value=1.0, step=0.1
                )
    
        # 💡 Calcul du score pondéré
        aggregated_df["Profile Score"] = sum(
            aggregated_df[profile] * weight for profile, weight in profile_weights.items()
        )
    
        # 📄 Colonnes dans l’ordre souhaité
        columns_to_display = (
            ['Name', 'Position'] +
            selected_profiles +
            ['Profile Score', 'Total Score']
        )
    
        # Création de la table finale
        table_df = (
            aggregated_df[columns_to_display]
            .drop_duplicates(subset=["Name"])
            .sort_values(by='Profile Score', ascending=False)
            .head(30)
        )
    
        # 🎨 Stylisation
        def highlight_name(val, comp):
            color_map = {
                c: plt.cm.tab10(i / 10) for i, c in enumerate(aggregated_df["competition_name"].dropna().unique())
            }
            rgba = color_map.get(comp, (1, 1, 1, 1))  # blanc par défaut
            r, g, b = [int(x * 255) for x in rgba[:3]]
            return f"color: rgb({r},{g},{b})"
    
        def style_table(df, full_df):
            styled = df.style
            cmap_cols = selected_profiles + ["Profile Score", "Total Score"]
            styled = styled.background_gradient(cmap="YlGnBu", subset=cmap_cols)
            styled = styled.apply(
                lambda row: [
                    highlight_name(row['Name'], full_df.loc[full_df['Name'] == row['Name'], 'competition_name'].values[0])
                    if col == 'Name' else ''
                    for col in df.columns
                ],
                axis=1
            )
            return styled
    
        st.subheader("Liste des joueurs")
        st.dataframe(style_table(table_df, aggregated_df), use_container_width=True)
    
        # 🔧 Nettoie les caractères spéciaux pour PDF
        def clean_text(text):
            if not isinstance(text, str):
                text = str(text)
            return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')
    
        # 📄 Classe PDF simple avec Arial
        class PDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 12)
                self.cell(0, 10, "Player Profile Table", 0, 1, "C")
                self.ln(5)
    
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 8)
    
        # 🧱 Dimensions
        col_width = 25
        row_height = 6
    
        # En-têtes
        for col in table_df.columns:
            pdf.cell(col_width, row_height, clean_text(col), border=1)
        pdf.ln(row_height)
    
        # Lignes du tableau
        for _, row in table_df.iterrows():
            for item in row:
                text = clean_text(round(item, 2)) if isinstance(item, float) else clean_text(item)
                pdf.cell(col_width, row_height, text, border=1)
            pdf.ln(row_height)
    
        # 📤 Export en PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdf.output(tmpfile.name)
            with open(tmpfile.name, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode("utf-8")
            download_link = f'<a href="data:application/pdf;base64,{base64_pdf}" download="player_table.pdf">📄 Télécharger la table en PDF</a>'
            st.markdown(download_link, unsafe_allow_html=True)
    
    else:
        st.info("Sélectionne au moins un profil pour afficher la table et générer le PDF.")
    
    with st.expander("📘 Glossaire des profils (clique pour afficher)"):
        st.markdown("""
        <style>
        .profil-label {
            font-weight: bold;
            color: #2c3e50;
        }
        .profil-desc {
            margin-bottom: 10px;
        }
        </style>
    
        <div class='profil-desc'><span class='profil-label'>🧨 Agresseur :</span> Capacité à effectuer des contre-pressings et des actions agressives immédiatement après la perte du ballon.</div>
        <div class='profil-desc'><span class='profil-label'>🪖 Header :</span> Capacité à remporter les duels aériens et à être efficace dans les airs.</div>
        <div class='profil-desc'><span class='profil-label'>🎩 Technicien :</span> Capacité à limiter les pertes de balle et à améliorer la précision des passes.</div>
        <div class='profil-desc'><span class='profil-label'>🛡 Defender :</span> Aptitude à réaliser des tacles et des interceptions efficaces.</div>
        <div class='profil-desc'><span class='profil-label'>🧱 Protecteur :</span> Capacité à bloquer les tirs et à dégager proprement la zone défensive.</div>
        <div class='profil-desc'><span class='profil-label'>🚫 Annihilateur :</span> Capacité à détruire les actions adverses et récupérer des ballons clés.</div>
        <div class='profil-desc'><span class='profil-label'>🔒 Conserver :</span> Capacité à conserver la possession, éviter les pertes inutiles.</div>
        <div class='profil-desc'><span class='profil-label'>➡️ Progress :</span> Capacité à faire avancer le jeu via des courses ou transmissions verticales.</div>
        <div class='profil-desc'><span class='profil-label'>🎯 Pass :</span> Capacité à effectuer des passes vers l’avant créatrices de valeur.</div>
        <div class='profil-desc'><span class='profil-label'>⚔️ 1v1 :</span> Capacité à résister aux dribbles adverses et à défendre en un contre un.</div>
        <div class='profil-desc'><span class='profil-label'>🅰️ Assist :</span> Capacité à créer des occasions via des centres et des passes décisives.</div>
        <div class='profil-desc'><span class='profil-label'>📦 Box :</span> Présence et efficacité dans la surface adverse.</div>
        <div class='profil-desc'><span class='profil-label'>🎯 Tireur :</span> Qualité des tirs, dangerosité générée.</div>
        <div class='profil-desc'><span class='profil-label'>🏃 Percuteur :</span> Capacité à dribbler et porter le ballon pour déséquilibrer.</div>
        <div class='profil-desc'><span class='profil-label'>♻️ Recuperateur :</span> Capacité à récupérer la possession suite à des actions défensives.</div>
        <div class='profil-desc'><span class='profil-label'>🎯 Striker :</span> Efficacité devant le but, qualité des occasions et des tirs.</div>
        <div class='profil-desc'><span class='profil-label'>🧤 GK :</span> Efficacité du gardien à stopper les tirs et surpasser les attentes.</div>
        <div class='profil-desc'><span class='profil-label'>🎯 Set Pieces :</span> Qualité des passes sur coups de pied arrêtés et création d’occasions.</div>
        """, unsafe_allow_html=True)


st.markdown("""
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #f8f9fa;
            padding: 10px;
            text-align: center;
            font-size: 14px;
            color: #333;
        }
    </style>
    <div class="footer">
        <p><strong>M.Feigean</strong> - Football Development</p>
    </div>
    """, unsafe_allow_html=True)

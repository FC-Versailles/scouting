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

st.set_page_config(layout='wide')

# Display the club logo from GitHub at the top right
logo_url = 'https://raw.githubusercontent.com/FC-Versailles/scouting/main/logo.png'
col1, col2 = st.columns([9, 1])
with col1:
    st.title("Recrutement | FC Versailles")
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

df1 = sb.player_season_stats(competition_id=129, season_id=317,creds = DEFAULT_CREDS)
df2 = sb.player_season_stats(competition_id=7, season_id=317,creds = DEFAULT_CREDS)
df3 = sb.player_season_stats(competition_id=8, season_id=317,creds = DEFAULT_CREDS)

data = pd.concat([df1, df2,df3], ignore_index=True)

data = data.drop(columns=[
    'account_id', 'player_id', 'team_id', 'competition_id', 'season_id', 
    'country_id', 'player_female', 'player_first_name', 'player_last_name', 'player_known_name'
])


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



# ---- GOOGLE SHEETS CONFIGURATION ----
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_FILE = 'token.pickle'
SPREADSHEET_ID = '1bqVJ5zSBJJsZe_PsH5lzspFKA6P0l3Mfc4jta00Jh9k'
DATABASE_RANGE = 'Feuille 1'

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def fetch_google_sheet(spreadsheet_id, range_name):
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    if not values:
        st.error("No data found in the specified range.")
        return pd.DataFrame()
    header = values[0]
    data = values[1:]
    return pd.DataFrame(data, columns=header)

@st.cache_data(ttl=60)
def load_data():
    return fetch_google_sheet(SPREADSHEET_ID, DATABASE_RANGE)

df = load_data()
df = df.loc[:, ~df.columns.duplicated()]

df['Date de naissance'] = pd.to_numeric(df['Date de naissance'], errors='coerce')
current_year = datetime.datetime.now().year
df['Age'] = current_year - df['Date de naissance']

params = st.query_params
default_page = params.get("page", "FCV Database")
PAGES = ["FCV Database", "Chercher Joueurs", "Statsbomb"]
page = st.sidebar.selectbox("Select Page", PAGES, index=PAGES.index(default_page))

#####################################################################################################################

if page == "FCV Database":
    st.markdown('<h2 style="color:#0031E3; margin-bottom: 20px;">📂 Scouting Database</h2>', unsafe_allow_html=True)


    # Create Filter Columns
    f1_col1, f1_col2, f1_col3, f1_col4, f1_col5 = st.columns(5)
    f2_col1, f2_col2, f2_col3, f2_col4, f2_col5 = st.columns(5)

    # 🔹 Position Filter
    positions = ["AILL", "ATT", "DC", "DD", "DG", "GB", "MC", "MO"]
    selected_position = f1_col1.multiselect("🔍 Le poste", options=positions, default=[])

    # 🔹 Championship Filter
    championships = df['Championnat'].dropna().unique().tolist()
    selected_championship = f1_col2.multiselect("🏆 Le championnat", options=championships, default=[])
    
    
    # 🔹 Footedness Filter
    pied_options = df['Pied'].dropna().unique().tolist()
    selected_pied = f1_col3.multiselect("🦶 Pied", options=pied_options, default=[])
    
    # 🔹 Contract End Filter
    contract_dates = df['Fin de contrat'].dropna().unique().tolist()
    selected_contract = f1_col4.multiselect("📅 Fin de contrat", options=contract_dates, default=[])
    

    # ✅ **Convert "Submitted at" to Datetime Format**
    df["Submitted at"] = pd.to_datetime(df["Submitted at"], errors="coerce").dt.tz_localize(None)

    # ✅ Ensure Submission Date is not empty
    if df["Submitted at"].notna().sum() > 0:
        min_date = df["Submitted at"].min()
        max_date = df["Submitted at"].max()
    else:
        min_date = datetime.datetime.now() - datetime.timedelta(days=30)
        max_date = datetime.datetime.now()


    # ✅ Submission Date Slider (Use datetime.date() to fix TypeError)
    selected_start_date, selected_end_date = f1_col5.slider(
        "📆 Date d'ajout",
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=(min_date.date(), max_date.date()),
        format="MM-YY"
    )

    # ✅ Convert selected dates back to datetime for filtering
    selected_start_date = datetime.datetime.combine(selected_start_date, datetime.time.min)
    selected_end_date = datetime.datetime.combine(selected_end_date, datetime.time.max)


    # 🔹 Convert Birth Year
    df["Date de naissance"] = pd.to_numeric(df["Date de naissance"], errors="coerce")

    # 🔹 Ensure Valid Birth Years Exist
    if df["Date de naissance"].notna().sum() > 0:
        min_birth_year = int(df["Date de naissance"].min(skipna=True))
        max_birth_year = int(df["Date de naissance"].max(skipna=True))
    else:
        min_birth_year, max_birth_year = 1980, datetime.datetime.now().year

    # ✅ Birth Year Slider
    selected_birth_year = f2_col1.slider(
        "📅 Date de Naissance",
        min_birth_year,
        max_birth_year,
        (min_birth_year, max_birth_year)
    )

    # 🔹 Player Search Box
    search_query = f2_col5.text_input("🔎 Recherche joueur", "")
    
        # 🔹 Type de joueur Filter
    type_options = df['Type de joueur'].dropna().unique().tolist()
    selected_type = f2_col3.multiselect("🎯 Type de joueur", options=type_options, default=[])
    
    # 🔹 Potential Filter
    potential_options = df['Potential'].dropna().unique().tolist()
    selected_potential = f2_col4.multiselect("💎 Potential", options=potential_options, default=[])
    
        # 🔹 Profil Filter
    profil_options = [
    "Initiateur", "Agresseur", "Facilitateur", "Défensif", "Progresseur", "Overlapper", "Directeur",
    "Linebreaker", "Recuperateur", "Createur", "Catalyseur", "Box-to-box", "Explorateur",
    "Détonateur", "Libérateur", "Box Killer", "Mobile finisher", "Target man"]
    selected_profil = f2_col2.multiselect("🧬 Profil", options=profil_options, default=[])



    # 🔹 Apply Filters
    filtered_df = df.copy()
    if selected_position:
        filtered_df = filtered_df[
            filtered_df['Poste'].apply(
                lambda postes: any(pos in postes for pos in selected_position) if isinstance(postes, str) else False
            )
        ]

    if selected_championship:
        filtered_df = filtered_df[filtered_df['Championnat'].isin(selected_championship)]
    if selected_pied:
        filtered_df = filtered_df[filtered_df['Pied'].isin(selected_pied)]
    if selected_contract:
        filtered_df = filtered_df[filtered_df['Fin de contrat'].isin(selected_contract)]
    if search_query:
        filtered_df = filtered_df[filtered_df['Player'].str.contains(search_query, case=False, na=False)]
    if selected_type:
        filtered_df = filtered_df[filtered_df['Type de joueur'].isin(selected_type)]
    if selected_potential:
        filtered_df = filtered_df[filtered_df['Potential'].isin(selected_potential)]
    if selected_profil:
        filtered_df = filtered_df[
            filtered_df['Profil'].apply(
                lambda profils: any(p in profils for p in selected_profil) if isinstance(profils, str) else False
            )
        ]
    

    # ✅ **Filter by Submission Date Range**
    filtered_df = filtered_df[
        (filtered_df["Submitted at"] >= selected_start_date) & 
        (filtered_df["Submitted at"] <= selected_end_date)
    ]

    # ✅ **Filter by Birth Year**
    filtered_df = filtered_df[
        (filtered_df["Date de naissance"] >= selected_birth_year[0]) &
        (filtered_df["Date de naissance"] <= selected_birth_year[1])
    ]

    # ✅ **Filter by Player Name (Case Insensitive)**
    if search_query:
        filtered_df = filtered_df[filtered_df['Player'].str.contains(search_query, case=False, na=False)]
    
  
    # Sort by most recent submission
    filtered_df = filtered_df.sort_values(by="Submitted at", ascending=False)
    
    full_filtered_df = filtered_df.copy()
    # Columns to Display
    columns_to_display = ["Prénom", "Player", "Date de naissance", "Pied", "Taille", "Poste", "Championnat", "Club", "Fin de contrat", "Profil", "Type de joueur", "Potential"]
    filtered_df_for_display = full_filtered_df[columns_to_display]

    
        # Apply CSS for styling
    st.markdown("""
    <style>
        table {
            width: 100% !important;
            border-collapse: collapse !important;
        }
        th {
            background-color: #beb245 !important;
            text-align: center !important; /* Center align header text */
            padding: 10px !important;
        }
        td {
            text-align: center !important;
            vertical-align: top !important;
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            padding: 8px !important;
            border: 1px solid #ddd !important;
        }
    </style>
    """, unsafe_allow_html=True)

    
    # Display table without index
    st.write(filtered_df_for_display.head(500).to_html(index=False, escape=False), unsafe_allow_html=True)

    
    # Export to Excel
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Scouting Data')
        return output.getvalue()
    
    excel_data = convert_df_to_excel(filtered_df)
    st.download_button(
        label="📂 Télécharger la liste",
        data=excel_data,
        file_name="FCV_Scouting_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Display Reports (détaillés pour les 5 premiers joueurs filtrés)
    st.subheader("📄 Liste des joueurs")
    
    top_players_df = full_filtered_df.head(10)
    for _, player_data in top_players_df.iterrows():
        player_name = player_data['Player']
        link = f"[📎 Voir la fiche complète](/?page=Chercher%20Joueurs&player={player_name})"
        encoded_name = quote(player_name)
        st.markdown(f"""
        <h3 style='color:#444;'>📋 Rapport pour {player_name}</h3>
        <a href='/?page=Chercher%20Joueurs&player={encoded_name}' style='text-decoration:none;'>
            <button style='background-color:#0043a4; color:white; padding:6px 12px; border:none; border-radius:5px;'>
                📎 Voir la fiche complète
            </button>
        </a>
        """, unsafe_allow_html=True)
    
        col1, col2 = st.columns(2)
    
        with col1:
            st.markdown(f"**Prénom :** {player_data.get('Prénom', '')}")
            st.markdown(f"**Âge :** {player_data.get('Age', '')}")
            st.markdown(f"**Taille :** {player_data.get('Taille', '')}")
            st.markdown(f"**Pied :** {player_data.get('Pied', '')}")
            st.markdown(f"**Poste :** {player_data.get('Poste', '')}")
            st.markdown(f"**Profil :** {player_data.get('Profil', '')}")
            st.markdown(f"**Type de joueur :** {player_data.get('Type de joueur', '')}")
    
        with col2:
            st.markdown(f"**Soumis le :** {player_data.get('Submitted at', '')}")
            st.markdown(f"**Date de naissance :** {player_data.get('Date de naissance', '')}")
            st.markdown(f"**Club :** {player_data.get('Club', '')}")
            st.markdown(f"**Championnat :** {player_data.get('Championnat', '')}")
            st.markdown(f"**Fin de contrat :** {player_data.get('Fin de contrat', '')}")
            st.markdown(f"**Transfermarkt :** {player_data.get('Transfermarkt', '')}")
            st.markdown(f"**Potential :** {player_data.get('Potential', '')}")
    
        rapport = str(player_data.get("Rapport", "")).strip()
        if rapport:
            st.subheader("📝 Commentaire du scout")
            st.markdown(f"<div style='white-space: pre-wrap;'>{rapport}</div>", unsafe_allow_html=True)
        else:
            st.warning("Aucun rapport disponible pour ce joueur.")
    

        st.markdown("<hr style='border:1px solid #ddd' />", unsafe_allow_html=True)
    
    
if page == "Chercher Joueurs":
    st.markdown('<h2 style="color:#0031E3; margin-bottom: 20px;">\U0001F50E Chercher un Joueur</h2>', unsafe_allow_html=True)

    default_player = params.get("player", "")
    search_input = st.text_input("\U0001F50E Nom du joueur", value=default_player)

    if search_input:
        st.query_params.update({"page": "Chercher Joueurs", "player": search_input})
    else:
        st.query_params.update({"page": "Chercher Joueurs"})

    matched_players = df[df['Player'].str.contains(search_input, case=False, na=False)] if search_input else pd.DataFrame()

    if not matched_players.empty:
        for _, player_data in matched_players.iterrows():
            st.markdown(f"<h3 style='color:#444;'>\U0001F4CB Rapport pour {player_data['Player']}</h3>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                for field in ["Prénom", "Âge", "Taille", "Pied", "Poste", "Profil", "Type de joueur"]:
                    st.markdown(f"**{field} :** {player_data.get(field, '')}")
            with col2:
                for field in ["Submitted at", "Date de naissance", "Club", "Championnat", "Fin de contrat", "Transfermarkt", "Potential"]:
                    st.markdown(f"**{field} :** {player_data.get(field, '')}")

            rapport = str(player_data.get("Rapport", "")).strip()
            if rapport:
                st.subheader("\U0001F4DD Commentaire du scout")
                st.markdown(f"<div style='white-space: pre-wrap;'>{rapport}</div>", unsafe_allow_html=True)
            else:
                st.warning("Aucun rapport disponible pour ce joueur.")

            radar_sets = [
                ("\U0001F4CA Physical Skills", ["Physiquement fort", "Intensité des courses", "Volume des courses"], 'rgba(0, 48, 135, 0.7)'),
                ("\U0001F3AF Contribution au jeu", ["Conserver ", "Progresser", "Créer du danger", "Contribuer"], 'rgba(255, 111, 0, 0.7)'),
                ("\U0001F6E1\ufe0f Défensive", ["Implication défensive", "Duels et interceptions", "Chasseur", "Jeu de tête"], 'rgba(0, 135, 91, 0.7)')
            ]

            radar_col1, radar_col2, radar_col3 = st.columns(3)

            for radar_title, fields, color in radar_sets:
                if all(field in player_data and str(player_data[field]).strip() not in ["", "NA", "N/A"] for field in fields):
                    try:
                        values = [float(player_data[field]) for field in fields]
                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(
                            r=values,
                            theta=fields,
                            fill='toself',
                            name=radar_title,
                            marker=dict(color=color)
                        ))
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 5],
                                    tickvals=[0, 1, 2, 3, 4, 5],
                                    ticktext=["0", "1", "2", "3", "4", "5"]
                                )
                            ),
                            showlegend=False,
                            title=radar_title
                        )
                        if radar_title == "\U0001F4CA Physical Skills":
                            radar_col1.plotly_chart(fig, use_container_width=True)
                        elif radar_title == "\U0001F3AF Contribution au jeu":
                            radar_col2.plotly_chart(fig, use_container_width=True)
                        else:
                            radar_col3.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.info("⚠️ Erreur dans la génération du radar.")
                        st.write(e)
                else:
                    st.info(f"⚠️ Données insuffisantes pour afficher le graphique : {radar_title}")

            st.markdown("---")

    elif search_input:
        st.info("Aucun joueur trouvé avec ce nom.")

# ================== PDF MANAGEMENT ==================

    st.markdown("#### 💬 Actualisation du rapport")
    
    COMMENT_DIR = "comments_storage"
    os.makedirs(COMMENT_DIR, exist_ok=True)
    
    # 1. Ajouter un commentaire
    with st.form("add_comment_form"):
        new_comment = st.text_area("✍️ Ajouter un commentaire")
        submitted = st.form_submit_button("💾 Enregistrer le commentaire")
        if submitted and new_comment.strip() != "":
            comment_id = str(uuid.uuid4())[:8]
            filename = f"{comment_id}.txt"
            with open(os.path.join(COMMENT_DIR, filename), "w", encoding="utf-8") as f:
                f.write(new_comment)
            st.success("✅ Commentaire ajouté.")
            st.rerun()
    
    # 2. Lister tous les commentaires
    comment_files = sorted(os.listdir(COMMENT_DIR))
    
    if not comment_files:
        st.info("Aucun commentaire enregistré.")
    else:
        for file in comment_files:
            file_path = os.path.join(COMMENT_DIR, file)
            with open(file_path, "r", encoding="utf-8") as f:
                comment_text = f.read()
    
            with st.expander("💬 Commentaire", expanded=False):
                st.markdown(f"<div style='white-space: pre-wrap;'>{comment_text}</div>", unsafe_allow_html=True)
    
                if st.button(f"🗑 Supprimer", key=file):
                    os.remove(file_path)
                    st.warning(f"❌ Commentaire supprimé.")
                    st.rerun()
    
    st.markdown("---")


    st.markdown("#### 📂 Documents")
    
    PDF_DIR = "pdf_storage"
    os.makedirs(PDF_DIR, exist_ok=True)
    
    # 1. Upload PDF
    uploaded_file = st.file_uploader("Uploader un rapport PDF", type=["pdf"])
    if uploaded_file is not None:
        save_path = os.path.join(PDF_DIR, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ Fichier {uploaded_file.name} ajouté avec succès.")
        st.rerun()

    
    # 2. Lister les fichiers déjà présents
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    
    if not pdf_files:
        st.info("Aucun PDF disponible.")
    else:
        for pdf_file in pdf_files:
            file_path = os.path.join(PDF_DIR, pdf_file)
    
            with st.expander(f"📄 {pdf_file}", expanded=False):
                # Prévisualisation du PDF intégré
                with open(file_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
    
                # Bouton de suppression
                if st.button(f"🗑 Supprimer {pdf_file}", key=pdf_file):
                    os.remove(file_path)
                    st.warning(f"❌ {pdf_file} supprimé.")
                    st.rerun()
    

elif page == "Statsbomb":
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
        "Compétences : Création des occasions": ("np_xg_90", "xa_90"),
        "Compétences : Qualité de Dribble": ("dribbles_90", "dribble_ratio"),
        "Compétences : Etat de confiance": ("npxgxa_90", "over_under_performance_90"),
        "Compétences : Qualité de tirs": ("obv_shot_90", "np_psxg_90"),
        "Compétences : Faire progresseur le jeu vers l'avant": ("carry_length", "deep_progressions_90"),
        "Compétences : Agir le plus proche possible du but": ("op_passes_into_and_touches_inside_box_90", "deep_completions_90"),
        "Compétences : Capacité à conserver le ballon": ("change_in_passing_ratio", "turnovers_90"),
        "Compétences : Création de danger": ("obv_dribble_carry_90", "obv_pass_90"),
        "Compétences : Intensité sans ballon": ("average_x_pressure", "counterpressures_90"),
        "Compétences : Pressing": ("padj_pressures_90", "pressure_regains_90"),
        "Compétences : Récupérer des ballons": ("ball_recoveries_90", "padj_interceptions_90"),
        "Compétences : Duels Aérien": ("aerial_wins_90", "aerial_ratio")
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
    
    player_selection = st.multiselect("Choisis les joueurs à mettre en valeur", filtered_data["player_name"].unique())

    selected_competence = st.selectbox("Choisis une compétence à analyser", list(competences_dict.keys()))
    x_col, y_col = competences_dict[selected_competence]


    if not filtered_data.empty:
        df_for_plot = filtered_data.rename(columns={"player_name": "Name"})  # plus besoin de Season
        fig = plot_scatter(df_for_plot, player_selection, x_col, y_col, x_col, y_col, selected_competence)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        
        
    st.markdown("<hr style='border:1px solid #ddd' />", unsafe_allow_html=True)


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
        "dribbles_90", "obv_dribble_carry_90",
        "defensive_action_regains_90", "pressure_regains_90",
        "np_xg_90", "np_xg_per_shot"
    ]
    
    column_mappings = {
        "Agresseur": ["counterpressures_90", "aggressive_actions_90"],
        "Header": [ "aerial_wins_90", "aerial_ratio"],
        "Technicien": ["change_in_passing_ratio", "turnovers_90"],
        "Defender": ["padj_tackles_90", "padj_interceptions_90"],
        "Blocker": ["blocks_per_shot", "padj_clearances_90"],
        "Conserver": ["passing_ratio", "dispossessions_90"],
        "Progress": ["carries_90", "carry_length"],
        "Pass": ["forward_pass_proportion", "obv_pass_90"],
        "Dribble": ["dribbled_past_90", "dribble_faced_ratio"],       
        "Assist": ["crosses_90", "xa_90"],     
        "Box": ["shot_touch_ratio", "touches_inside_box_90"],
        "Tireur": ["np_psxg_90", "obv_shot_90"],
        "Pecuteur": ["dribbles_90", "obv_dribble_carry_90"],
        "Recuperateur": ["defensive_action_regains_90", "pressure_regains_90"],
        "Striker": ["np_xg_90", "np_xg_per_shot"],
    }
    
        # Z-score
    zscore_df = data[['player_name', 'primary_position'] + chosen_variables].copy()
    zscore_df.fillna(zscore_df.median(numeric_only=True), inplace=True)
    zscore_df[chosen_variables] = (zscore_df[chosen_variables] - zscore_df[chosen_variables].mean()) / zscore_df[chosen_variables].std()
    
    # Aggregate profile scores
    aggregated_df = zscore_df[['player_name', 'primary_position']].copy()
    for profile_name, vars_ in column_mappings.items():
        aggregated_df[profile_name] = zscore_df[vars_[0]] + zscore_df[vars_[1]]
    
    aggregated_df["Total_Profile_Score"] = aggregated_df[list(column_mappings.keys())].sum(axis=1)
    
    # ✅ Rename columns for plotting
    aggregated_df = aggregated_df.rename(columns={
        "player_name": "Name",
        "primary_position": "Position"
    })
    
    # Streamlit app
    st.title(" #### Player Profiling: Championnat National")
      
    # Select profiles to show in the table
    selected_profiles = st.multiselect("Select profiles to display in the table:", options=list(column_mappings.keys()), default=["Agresseur", "Defender", "Striker"])
    
    # Show table below
    if selected_profiles:
        table_df = aggregated_df[['Name', 'Position'] + selected_profiles + ['Total_Profile_Score']].sort_values(by='Total_Profile_Score', ascending=False)
        st.subheader("Player Table")
        st.dataframe(table_df, use_container_width=True)
    


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

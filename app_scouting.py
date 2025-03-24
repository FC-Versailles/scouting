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

st.set_page_config(layout='wide')

# Display the club logo from GitHub at the top right
logo_url = 'https://raw.githubusercontent.com/FC-Versailles/scouting/main/logo.png'
col1, col2 = st.columns([9, 1])
with col1:
    st.title("Recrutement | FC Versailles")
with col2:
    st.image(logo_url, use_container_width=True)
    
st.markdown("<hr style='border:1px solid #ddd' />", unsafe_allow_html=True)

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
PAGES = ["FCV Database", "Chercher Joueurs", "Statsbomb Data"]
page = st.sidebar.selectbox("Select Page", PAGES, index=PAGES.index(default_page))




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
    
  
    full_filtered_df = filtered_df.copy() 
    # Columns to Display
    columns_to_display = ["Prénom","Player", "Date de naissance","Pied","Taille", "Poste", "Championnat", "Club", "Fin de contrat","Profil","Type de joueur","Potential"]
    filtered_df = filtered_df[columns_to_display]
    
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
    st.write(filtered_df.head(500).to_html(index=False, escape=False), unsafe_allow_html=True)
    
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
    
    
elif page == "Chercher Joueurs":
    st.markdown('<h2 style="color:#0031E3; margin-bottom: 20px;">🔎 Chercher un Joueur</h2>', unsafe_allow_html=True)

    params = st.query_params
    default_player = params.get("player", "")

    search_input = st.text_input("🔎 Nom du joueur", value=default_player)
    
    if search_input:
        st.query_params.update({"page": "Chercher Joueurs", "player": search_input})
    else:
        st.query_params.update({"page": "Chercher Joueurs"})


    matched_players = df[df['Player'].str.contains(search_input, case=False, na=False)] if search_input else pd.DataFrame()


    if not matched_players.empty:
        for _, player_data in matched_players.iterrows():
            st.markdown(f"<h3 style='color:#444;'>📋 Rapport pour {player_data['Player']}</h3>", unsafe_allow_html=True)
    
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
                st.subheader("📝 Commmentaire du scout")
                st.markdown(f"<div style='white-space: pre-wrap;'>{rapport}</div>", unsafe_allow_html=True)
            else:
                st.warning("Aucun rapport disponible pour ce joueur.")
                
                        # 🔹 Radar Plot – Physical Skills
            phys_fields = ["Physiquement fort", "Intensité des courses", "Volume des courses"]
            
            # Vérifie que les champs existent et sont valides
            if all(field in player_data and str(player_data[field]).strip() not in ["", "NA", "N/A"] for field in phys_fields):
                try:
                    # Convertir en float
                    values = [float(player_data[field]) for field in phys_fields]
            
                    # Créer le radar Plotly
                    fig = go.Figure()
            
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=phys_fields,
                        fill='toself',
                        name='Physical Skills',
                        marker=dict(color='rgba(0, 48, 135, 0.7)')
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 5],
                                tickfont_size=12,
                                tickvals=[0,1, 2, 3, 4, 5],
                                ticktext=["0","1", "2", "3", "4", "5"]
                            )
                        ),
                        showlegend=False,
                        title="📊 Physical Skills"
                    )

        
                    st.plotly_chart(fig, use_container_width=True)
            
                except ValueError:
                    st.info("⚠️ Certaines valeurs physiques ne sont pas exploitables pour générer le graphique.")
            else:
                st.info("⚠️ Données physiques insuffisantes pour afficher le graphique radar.")

    
            st.markdown("---")
    elif search_input:
        st.info("Aucun joueur trouvé avec ce nom.")
    
     
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
    

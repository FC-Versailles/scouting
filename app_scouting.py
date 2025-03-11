import streamlit as st
import pandas as pd
import datetime
import os
import pickle
from io import BytesIO
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

st.set_page_config(layout='wide')

# Display the club logo from GitHub at the top right
logo_url = 'https://raw.githubusercontent.com/FC-Versailles/scouting/main/logo.png'
col1, col2 = st.columns([9, 1])
with col1:
    st.title("Recrutement| FC Versailles")
with col2:
    st.image(logo_url, use_container_width=True)
    
# Add a horizontal line to separate the header
st.markdown("<hr style='border:1px solid #ddd' />", unsafe_allow_html=True)


# ---- GOOGLE SHEETS CONFIGURATION ----
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_FILE = 'token.pickle'
SPREADSHEET_ID = '1bqVJ5zSBJJsZe_PsH5lzspFKA6P0l3Mfc4jta00Jh9k'  # Replace with actual Google Sheet ID
DATABASE_RANGE = 'Feuille 1'

# ---- FUNCTION: GET GOOGLE SHEETS CREDENTIALS ----
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

# ---- FUNCTION: FETCH GOOGLE SHEET DATA ----
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

# ---- FUNCTION: LOAD MAIN DATABASE ----
@st.cache_data(ttl=60)
def load_data():
    return fetch_google_sheet(SPREADSHEET_ID, DATABASE_RANGE)

df = load_data()
df = df.loc[:, ~df.columns.duplicated()]

# Convert "Date de naissance" to numeric for age calculation
if "Date de naissance" in df.columns:
    df["Date de naissance"] = pd.to_numeric(df["Date de naissance"], errors="coerce")
    current_year = datetime.datetime.now().year
    df["Age"] = current_year - df["Date de naissance"]
else:
    st.error("⚠️ 'Date de naissance' column missing in database!")

# Sidebar for page selection
page = st.sidebar.selectbox("Select Page", ["FCV Database", "Statsbomb Data"])

if page == "FCV Database":
    st.header("📂 Scouting Database")

    # Create Filter Columns
    col1, col2, col3, col4, col5 = st.columns(5)

    # 🔹 Position Filter
    positions = df['Poste'].dropna().unique().tolist()
    selected_position = col1.multiselect("🔍 Le poste", options=positions, default=[])

    # 🔹 Championship Filter
    championships = df['Championnat'].dropna().unique().tolist()
    selected_championship = col2.multiselect("🏆 Le championnat", options=championships, default=[])

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
    selected_start_date, selected_end_date = col5.slider(
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
    selected_birth_year = col3.slider(
        "📅 Date de Naissance",
        min_birth_year,
        max_birth_year,
        (min_birth_year, max_birth_year)
    )

    # 🔹 Player Search Box
    search_query = col4.text_input("🔎 Recherche joueur", "")

    # 🔹 Apply Filters
    filtered_df = df.copy()

    if selected_position:
        filtered_df = filtered_df[filtered_df['Poste'].isin(selected_position)]
    if selected_championship:
        filtered_df = filtered_df[filtered_df['Championnat'].isin(selected_championship)]

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


    # ---- SELECT COLUMNS TO DISPLAY ----
    columns_to_display = ["Player","Pied", "Poste","Championnat", "Club", "Fin de contrat", "Rapport"]
    filtered_df = filtered_df[columns_to_display]

    # ---- DISPLAY INTERACTIVE TABLE WITH IMPROVED RAPPORT VISIBILITY ----
    st.markdown("""
        <style>
            .st-emotion-cache-1uixxvy {  /* Custom class for text columns */
                max-height: 6em !important;
                overflow: auto !important;
                white-space: pre-wrap !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.data_editor(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Rapport": st.column_config.TextColumn(
                width="large",
                max_chars=None,
                help="Rapport détaillé sur le joueur"
            )
        }
    )

# ---- EXPORT TO EXCEL BUTTON ----
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Scouting Data')
        processed_data = output.getvalue()
        return processed_data
    
    excel_data = convert_df_to_excel(filtered_df)
    st.download_button(
        label="📂 Download Excel",
        data=excel_data,
        file_name="FCV_Scouting_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


     # ---- ADD EXPANDABLE "VIEW REPORT" FOR EACH PLAYER ----
    st.subheader("📄 Rapport sur les joueurs")
    
    # Select the first 5 players from the filtered dataframe
    top_players_df = df.loc[filtered_df.index[:5], ["Player","Transfermarkt","Pied", "Taille", "Poste","Championnat", "Club", "Fin de contrat", "Rapport"]]
    
    # Debugging: Check if "Rapport" and "Comment" exist
    
    
    for _, row in top_players_df.iterrows():
        with st.expander(f"🔍 {row['Player']} | {row['Poste']} pour {row['Club']}"):
            st.write(f"**Player:** {row['Player']}")
            st.write(f"**Transfermarkt:** {row['Transfermarkt']}")
            
            
            
            st.write(f"**Position:** {row['Poste']}")
            st.write(f"**Club:** {row['Club']}")
            st.write(f"**Contract End:** {row['Fin de contrat']}")
    
            st.write("### ✍️ Scouting Report:")
    
            # Convert NaN to empty string and strip whitespace
            rapport_value = str(row.get("Rapport", "")).strip()
    
            # Display "Rapport"
            if rapport_value:
                st.markdown(f"<div style='white-space: pre-wrap;'><strong>📝 Rapport:</strong><br>{rapport_value}</div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ No 'Rapport' available for this player.")


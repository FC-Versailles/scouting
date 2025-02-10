#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:14:37 2025

@author: fcvmathieu
"""

import streamlit as st

# Set Streamlit Page Configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="FC Versailles | Player Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

from statsbombpy import sb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from adjustText import adjust_text
import plotly.graph_objects as go
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pickle
import ast
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_pdf import PdfPages
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from fpdf import FPDF
import datetime


DEFAULT_CREDS = {
    "user": "mathieu.feigean@fcversailles.com",
    "passwd": "uVBxDK5X",
}

# Looking at all competitions to search for comp and season id
comp = sb.competitions(creds = DEFAULT_CREDS)

# Disable caching to avoid SQLite errors
sb.CACHE_ENABLED = False  

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

##########################################################################################


# ---- GOOGLE SHEETS CONFIGURATION ----
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_FILE = 'token.pickle'
SPREADSHEET_ID = '1bqVJ5zSBJJsZe_PsH5lzspFKA6P0l3Mfc4jta00Jh9k'  # Replace with your actual Google Sheet ID
DATABASE_RANGE = 'Feuille 1'  # Your main protected player database
REPORTS_RANGE = 'Reports'  # Separate sheet to store scouting reports

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
    max_columns = len(header)
    adjusted_data = [
        row + [None] * (max_columns - len(row)) if len(row) < max_columns else row[:max_columns]
        for row in data
    ]
    return pd.DataFrame(adjusted_data, columns=header)

# ---- FUNCTION: LOAD MAIN DATABASE ----
@st.cache_data(ttl=60)
def load_data():
    return fetch_google_sheet(SPREADSHEET_ID, DATABASE_RANGE)

df = load_data()
df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns

##########################################################################################

# Create Navigation for Multi-Page Application
st.sidebar.title("FC Versailles | Analyse des Joueurs")
page = st.sidebar.radio("", ["Scouting", "Rating", "Player Analysis","FCV Database"])

# Define Pages
if page == "Scouting":
    st.title("Scouting")
    
    # Filter Options
    positions = st.multiselect('Select Player Positions', options=data['primary_position'].unique(), key="scouting_positions")
    competitions = st.multiselect('Select Competitions', options=data['competition_name'].unique(), key="scouting_competitions")
    age = st.slider('Age', int(data['age'].min()), int(data['age'].max()), (int(data['age'].min()), int(data['age'].max())), key="rating_age")
    minutes = st.slider('Minutes', int(data['minutes'].min()), int(data['minutes'].max()), (int(data['minutes'].min()), int(data['minutes'].max())), key="rating_minutes")
    
    filtered_data = data
    if positions:
        filtered_data = filtered_data[filtered_data['primary_position'].isin(positions)]
    if competitions:
        filtered_data = filtered_data[filtered_data['competition_name'].isin(competitions)]
    if competitions:
        filtered_data = filtered_data[filtered_data['age'].isin(age)]
    if competitions:
        filtered_data = filtered_data[filtered_data['minutes'].isin(minutes)]
    
    st.dataframe(filtered_data, height=600)  # Ensure 'player_name' and 'primary_position' remain visible when scrolling

elif page == "Rating":
    st.title("Rating")
    
    # Sidebar Filters
    st.sidebar.subheader("Filters")
    position_filter = st.sidebar.multiselect('Select Player Positions', options=data['primary_position'].dropna().unique(), key="rating_positions")
    team_filter = st.sidebar.multiselect('Select Team', options=data['team_name'].dropna().unique(), key="rating_teams")
    competition_filter = st.sidebar.multiselect('Select Competition', options=data['competition_name'].dropna().unique(), key="rating_competitions")
    season_filter = st.sidebar.multiselect('Select Season', options=data['season_name'].dropna().unique(), key="rating_seasons")
    age_filter = st.sidebar.slider('Age', int(data['age'].min(skipna=True)), int(data['age'].max(skipna=True)), (int(data['age'].min(skipna=True)), int(data['age'].max(skipna=True))), key="Age")
    height_filter = st.sidebar.slider('Height Range (cm)', int(data['player_height'].min()), int(data['player_height'].max()), (int(data['player_height'].min()), int(data['player_height'].max())), key="rating_height")
    minutes_filter = st.sidebar.slider('Minutes Played Range', int(data['minutes'].min()), int(data['minutes'].max()), (int(data['minutes'].min()), int(data['minutes'].max())), key="rating_minutes")
    
    # Apply filters
    filtered_data = data
    if position_filter:
        filtered_data = filtered_data[filtered_data['primary_position'].isin(position_filter)]
    if team_filter:
        filtered_data = filtered_data[filtered_data['team_name'].isin(team_filter)]
    if competition_filter:
        filtered_data = filtered_data[filtered_data['competition_name'].isin(competition_filter)]
    if season_filter:
        filtered_data = filtered_data[filtered_data['season_name'].isin(season_filter)]
    
    filtered_data = filtered_data[(filtered_data['age'] >= age_filter[0]) & (filtered_data['age'] <= age_filter[1])]
    filtered_data = filtered_data[(filtered_data['player_height'] >= height_filter[0]) & (filtered_data['player_height'] <= height_filter[1])]
    filtered_data = filtered_data[(filtered_data['minutes'] >= minutes_filter[0]) & (filtered_data['minutes'] <= minutes_filter[1])]
    
    # Select Metrics for Comparison
    metric_start = data.columns.get_loc("np_xg_per_shot")
    metric_columns = data.columns[metric_start:].tolist()
    
    if metric_columns:
        x_axis = st.selectbox('Select X Axis Metric', options=metric_columns, key="rating_x_axis")
        y_axis = st.selectbox('Select Y Axis Metric', options=metric_columns, key="rating_y_axis")
    else:
        st.write("No available metrics for selection.")
        x_axis, y_axis = None, None

    if x_axis and y_axis:
        fig = go.Figure()
        
        for competition, comp_data in filtered_data.groupby('competition_name'):
            fig.add_trace(go.Scatter(
                x=comp_data[x_axis],
                y=comp_data[y_axis],
                mode='markers',
                name=competition,
                text=comp_data['player_name'],
                hoverinfo='text',
                marker=dict(size=10, opacity=0.7)
            ))

        fig.update_layout(
            title=f'{x_axis} vs {y_axis}',
            xaxis_title=x_axis,
            yaxis_title=y_axis,
            template="plotly_white"
        )

        st.plotly_chart(fig)
    else:
        st.write("Select metrics for the plot.")



elif page == "Player Analysis":
    st.title("Player Analysis")

    # Player Selection
    player_name = st.selectbox('Select Player', options=data['player_name'].unique(), key="player_analysis")

    if player_name:
        player_data = data[data['player_name'] == player_name]
        st.write(player_data)

        # Display Key Metrics
        st.write("### Key Metrics")
        st.write(player_data.describe().T)
    else:
        st.write("Select a player to analyze.")
        
        
elif page == "FCV Database":
    st.title("📂 FCV Player Database")

    # Create Filter Columns
    col1, col2, col3, col4, col5 = st.columns(5)

    # 🔹 Position Filter
    positions = df['Poste'].dropna().unique().tolist()
    selected_position = col1.multiselect("🔍 Select Position", options=positions, default=[])

    # 🔹 Championship Filter
    championships = df['championnat'].dropna().unique().tolist()
    selected_championship = col2.multiselect("🏆 Select Championship", options=championships, default=[])

    # 🔹 Birth Year (Converted to Age)
    df['Date de naissance'] = pd.to_numeric(df['Date de naissance'], errors='coerce')
    current_year = datetime.datetime.now().year  # ✅ Correct reference
    df['Age'] = current_year - df['Date de naissance']


    min_birth_year = int(df['Date de naissance'].min(skipna=True))
    max_birth_year = int(df['Date de naissance'].max(skipna=True))
    
    selected_birth_year = col3.slider("📅 Select Birth Year", min_birth_year, max_birth_year, (min_birth_year, max_birth_year))
    
    # 🔹 Player Search Box
    search_query = col4.text_input("🔎 Search Player", "")

    # 🔹 Sorting by Key Metric
    sorting_metric = col5.selectbox("📊 Sort by Metric", ["Age", "Fin de Contrat"])

    # ---- APPLY FILTERS ----
    filtered_df = df.copy()

    if selected_position:
        filtered_df = filtered_df[filtered_df['Poste'].isin(selected_position)]
    if selected_championship:
        filtered_df = filtered_df[filtered_df['championnat'].isin(selected_championship)]
    
    filtered_df = filtered_df[
        (filtered_df["Date de naissance"] >= selected_birth_year[0]) &
        (filtered_df["Date de naissance"] <= selected_birth_year[1])
    ]

    if search_query:
        filtered_df = filtered_df[filtered_df['Player'].str.contains(search_query, case=False, na=False)]

    # ---- SORTING ----
    if sorting_metric in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by=sorting_metric, ascending=False)

    # ---- SELECT COLUMNS TO DISPLAY ----
    columns_to_display = ["Player", "Prénom", "Age", "Poste", "Pied", "Club", "Fin de contrat"]
    
    # Ensure only existing columns are displayed
    filtered_df = filtered_df[columns_to_display]

    # ---- DISPLAY INTERACTIVE TABLE WITHOUT "Rapport" ----
    st.data_editor(
        filtered_df,
        hide_index=True,
        use_container_width=True
    )

    # ---- ADD EXPANDABLE "VIEW REPORT" FOR EACH PLAYER ----
    st.subheader("📄 Player Reports")
    
    # Select the first 10 players from the filtered dataframe
    top_players_df = filtered_df.head(5)
    
    for _, row in top_players_df.iterrows():
        with st.expander(f"🔍 {row['Player']} - {row['Poste']} at {row['Club']}"):
            st.write(f"**Player:** {row['Player']}")
            st.write(f"**Position:** {row['Poste']}")
            st.write(f"**Club:** {row['Club']}")
            st.write(f"**Contract End:** {row['Fin de contrat']}")
            st.write("### 📝 Scouting Report:")
    
            # Ensure the "Rapport" column exists and display it properly formatted
            if "Rapport" in df.columns:
                report_text = df.loc[df['Player'] == row['Player'], 'Rapport'].values[0] if not df.loc[df['Player'] == row['Player'], 'Rapport'].isna().all() else "No Report Available"
                st.markdown(f"<div style='white-space: pre-wrap;'>{report_text}</div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ No 'Rapport' column found in the database.")


    # ---- EXPORT OPTIONS ----
    colA, colB = st.columns([1, 1])

    # Export to Excel
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="Scouting_Data", index=False)
        processed_data = output.getvalue()
        return processed_data

    excel_data = convert_df_to_excel(filtered_df)
    colA.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name="FCV_Scouting_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Export to PDF

    def convert_df_to_pdf(df):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
    
        pdf.cell(200, 10, txt="FC Versailles Scouting Report", ln=True, align='C')
        pdf.ln(10)
    
        for i, row in df.iterrows():
            pdf.cell(200, 10, txt=f"Player: {row['Player']} | Position: {row['Poste']} | Age: {row['Age']}", ln=True)
            pdf.cell(200, 10, txt=f"Club: {row['Club']} | Contract End: {row['Fin de contrat']}", ln=True)
            pdf.ln(5)
    
        pdf_output = BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin1'))  # Fix the TypeError
    
        return pdf_output.getvalue()

    pdf_data = convert_df_to_pdf(filtered_df)
    colB.download_button(
        label="📄 Download PDF",
        data=pdf_data,
        file_name="FCV_Scouting_Report.pdf",
        mime="application/pdf"
    )

    # ---- VISUALIZATION ----
    st.subheader("📊 Player Distribution by Position")
    position_counts = filtered_df["Poste"].value_counts().reset_index()
    position_counts.columns = ["Position", "Count"]

    fig = px.bar(
        position_counts, 
        x="Position", 
        y="Count", 
        title="Players per Position", 
        text="Count", 
        color="Position"
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- SECTION: ADD NEW SCOUTING REPORT ----
st.title("📂 Add a Scouting Report")

# Select a Player from the Database
players_list = df["Player"].unique().tolist()
selected_player = st.selectbox("🔍 Select Player to Add Report", players_list)

# Upload an Image
uploaded_file = st.file_uploader("📸 Upload Image", type=["png", "jpg", "jpeg"])

# Add Scouting Report Text
new_report = st.text_area("📝 Add Your Observations", "")

# Submit Button
if st.button("✅ Submit Report"):
    if selected_player and new_report:
        # Get current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert image to link (Placeholder for cloud storage logic)
        if uploaded_file:
            image_link = f"Uploaded: {uploaded_file.name}"  # In real-world use Google Drive
        else:
            image_link = "No Image"

        # Append data to Google Sheets
        sheet = build('sheets', 'v4', credentials=get_credentials()).spreadsheets()
        new_entry = [[timestamp, selected_player, image_link, new_report]]

        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=REPORTS_RANGE,  # Stores reports in a separate sheet
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": new_entry}
        ).execute()

        st.success(f"✅ Report for {selected_player} successfully added!")

    else:
        st.error("⚠️ Please select a player and write a report before submitting.")






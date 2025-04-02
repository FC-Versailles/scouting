#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 10:57:19 2025

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

st.set_page_config(layout='wide')

# ---- GOOGLE SHEETS CONFIGURATION ----
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_FILE = 'token.pickle_v1'
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
                'client_secret_v1.json', SCOPES
            )
            creds = flow.run_console()  # ✅ PATCH ICI
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

# --- INTERFACE STREAMLIT ---
st.title("Modifier la database")

joueurs = df['Player'].dropna().unique()
joueur_selectionne = st.selectbox("Choisir un joueur", joueurs)

joueur_data = df[df['Player'] == joueur_selectionne].iloc[0]

champ_personnalise = {
    "Poste": {"type": "multiselect", "options": ["AILL", "ATT", "DC", "DD", "DG", "GB", "MC", "MO"]},
    "Championnat": {"type": "selectbox", "options": ["National 1", "N2", "N3", "Ligue 2", "Benelux", "Reserve", "Autres"]},
    "Pied": {"type": "selectbox", "options": ["D", "G", "Les deux", "D, Les deux", "G"]},
    "Blessure ?": {"type": "selectbox", "options": ["oui", "non", "Pas de connaissance"]},
    "Profil": {"type": "selectbox", "options": [
        "Initiateur", "Agresseur", "Facilitateur", "Défensif", "Progresseur", "Overlapper",
        "Directeur", "Linebreaker", "Recuperateur", "Createur", "Catalyseur", "Box-to-box",
        "Explorateur", "Détonateur", "Libérateur", "Box killer", "Mobile finisher", "Target man"]},
    "Type de joueur": {"type": "selectbox", "options": ["Non adapté","Top >80", "Core>50", "Squad >20", "Fringe<20"]},
    "Potential": {"type": "selectbox", "options": ["Non adapté","Champions league", "Ligue 1", "Ligue 2", "National"]}
}

# Ajout automatique des critères notés sur 5
champs_note_5 = [
    "Physiquement fort", "Intensité des courses", "Vitesse", "Volume des courses",
    "Conserver", "Progresser", "Créer du danger", "Contribuer", "Implication défensive",
    "Duels et interceptions", "Chasseur", "Qualité technique", "Intensité",
    "Intelligence de jeu", "Leader"
]

for champ in champs_note_5:
    champ_personnalise[champ] = {"type": "slider", "min": 1, "max": 5}

# Formulaire Streamlit dynamique
with st.form("edit_form"):
    nouvelles_valeurs = {}

    for colonne in df.columns:
        if colonne == "Player":
            continue

        valeur_actuelle = joueur_data[colonne] if pd.notna(joueur_data[colonne]) else ""
        valeur_actuelle = str(valeur_actuelle)

        if colonne in champ_personnalise:
            champ = champ_personnalise[colonne]
            if champ["type"] == "slider":
                try:
                    val = int(valeur_actuelle)
                except:
                    val = champ["min"]
                nouvelles_valeurs[colonne] = st.slider(colonne, min_value=champ["min"], max_value=champ["max"], value=val)
            elif champ["type"] == "selectbox":
                index = champ["options"].index(valeur_actuelle) if valeur_actuelle in champ["options"] else 0
                nouvelles_valeurs[colonne] = st.selectbox(colonne, options=champ["options"], index=index)
            elif champ["type"] == "multiselect":
                valeurs = valeur_actuelle.split(", ") if valeur_actuelle else []
                nouvelles_valeurs[colonne] = st.multiselect(colonne, options=champ["options"], default=valeurs)
        else:
            nouvelles_valeurs[colonne] = st.text_input(colonne, valeur_actuelle)

    submit = st.form_submit_button("Enregistrer")

if submit:
    row_index = df[df['Player'] == joueur_selectionne].index[0] + 2  # ligne réelle dans Sheets

    def col_idx_to_letter(n):
        string = ""
        while n >= 0:
            n, r = divmod(n, 26)
            string = chr(65 + r) + string
            n -= 1
        return string

    row_values = []
    for col in df.columns:
        if col == "Player":
            row_values.append(joueur_selectionne)
        elif col in champ_personnalise and champ_personnalise[col]["type"] == "multiselect":
            row_values.append(", ".join(nouvelles_valeurs.get(col, [])))
        else:
            val = nouvelles_valeurs.get(col, joueur_data[col])
            row_values.append(str(val) if val is not None else "")

    last_col_index = len(df.columns) - 1
    last_col_letter = col_idx_to_letter(last_col_index)
    range_to_update = f"{DATABASE_RANGE}!A{row_index}:{last_col_letter}{row_index}"

    update_body = {
        "values": [row_values]
    }

    st.write("✅ Debug - plage:", range_to_update)
    st.write("✅ Debug - valeurs:", row_values)

    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    try:
        response = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption="USER_ENTERED",
            body=update_body
        ).execute()
        st.success("✅ Modifications enregistrées dans Google Sheets")
    except Exception as e:
        st.error(f"❌ Erreur lors de la mise à jour Google Sheets : {e}")

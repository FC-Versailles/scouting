#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 16:21:01 2025

@author: fcvmathieu
"""

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load the data
data_path = 'competence.csv'  # Replace with the correct file path
data = pd.read_csv(data_path)

# Remove the 'Unnamed: 0' column if it exists
if 'Unnamed: 0' in data.columns:
    data = data.drop(columns=['Unnamed: 0'])

# Streamlit app
st.title("Football Player Performance Data")

# Display the dataset with options to select columns
st.sidebar.header("Options")
columns = data.columns.tolist()
selected_columns = st.multiselect("Select variables to display:", columns, default=columns)

# Filter data by selected columns
data_filtered = data.copy()
for column in columns:
    if column == 'Name':
        search_text = st.sidebar.text_input(f"Search in {column}:", value="")
        if search_text:
            data_filtered = data_filtered[data_filtered[column].str.contains(search_text, case=False, na=False)]
    elif data[column].dtype == 'object':
        unique_values = data[column].dropna().unique().tolist()
        selected_values = st.sidebar.multiselect(f"Filter {column}:", unique_values, default=unique_values)
        data_filtered = data_filtered[data_filtered[column].isin(selected_values)]
    else:
        min_val = float(data[column].min())
        max_val = float(data[column].max())
        range_values = st.sidebar.slider(f"Filter {column}:", min_val, max_val, (min_val, max_val))
        data_filtered = data_filtered[(data_filtered[column] >= range_values[0]) & (data_filtered[column] <= range_values[1])]

# Filter data by selected columns for display
display_data = data_filtered[selected_columns]

# Set a larger table size for better visualization
st.write("### Dataset")
st.dataframe(display_data, height=600, width=1200)

# Apply a color map to the numerical columns
if not display_data.empty:
    numerical_columns = display_data.select_dtypes(include=['float64', 'int64']).columns
    if not numerical_columns.empty:
        cmap = sns.diverging_palette(240, 10, as_cmap=True)
        styled_table = display_data.style.background_gradient(cmap=cmap, subset=numerical_columns)
        st.write(styled_table.to_html(), unsafe_allow_html=True)

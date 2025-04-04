import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import os

# Load datasets
local_df = pd.read_excel("Local_meet_results.xlsx", engine="openpyxl")
records_df = pd.read_excel("National_records.xlsx", engine="openpyxl")

# Clean column names
local_df.columns = local_df.columns.str.strip()
records_df.columns = records_df.columns.str.strip()

# Clean up local results
local_df['First_Name'] = local_df['First_Name'].str.strip()
local_df['Last_Name'] = local_df['Last_Name'].str.strip()
local_df['Full_Name'] = local_df['First_Name'] + ' ' + local_df['Last_Name']
local_df['Category'] = local_df['Category'].str.strip().str.title()
local_df['Gender'] = local_df['Gender'].str.strip().str.title()
local_df['Result'] = pd.to_numeric(local_df['Result'], errors='coerce')
local_df = local_df.dropna(subset=['Result'])

# Clean national records
records_df['Category'] = records_df['Category'].str.strip().str.title()
records_df['Gender'] = records_df['Gender'].str.strip().str.title()
records_df['Record'] = pd.to_numeric(records_df['Record'], errors='coerce')
records_df = records_df.dropna(subset=['Record'])

# Get best result per athlete
best_per_athlete = (
    local_df.sort_values('Result')
            .drop_duplicates(subset=['Category', 'Gender', 'Full_Name'], keep='first')
)

# Get top 6 per Category x Gender
top6 = (
    best_per_athlete
        .sort_values('Result')
        .groupby(['Category', 'Gender'], group_keys=False)
        .head(6)
)

# Merge top 6 with national records
comparison = top6.merge(records_df, on=['Category', 'Gender'], how='left')

# Calculate comparison metrics
comparison['Beats_Record'] = comparison['Result'] < comparison['Record']
comparison['Diff_to_Record'] = comparison['Result'] - comparison['Record']
comparison['%_Diff'] = ((comparison['Result'] - comparison['Record']) / comparison['Record']) * 100
comparison['Within_1.5%'] = comparison['%_Diff'] <= 1.5
comparison['Within_3.0%'] = comparison['%_Diff'] <= 3.0

# Categorize bar color based on % difference
def get_color_class(percent_diff):
    if percent_diff <= 1.5:
        return 'green'
    elif percent_diff <= 3.0:
        return 'yellow'
    else:
        return 'red'

comparison['Color_Class'] = comparison['%_Diff'].apply(get_color_class)

# Color mapping
color_map = {
    'green': 'green',
    'yellow': 'gold',
    'red': 'crimson'
}

# Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H2("🎯 % Difference from National Record", style={'textAlign': 'center'}),

    html.Div([
        dcc.Dropdown(
            id='category-dropdown',
            options=[{'label': cat, 'value': cat} for cat in sorted(comparison['Category'].unique())],
            value=sorted(comparison['Category'].unique())[0],
            style={'width': '40%', 'marginRight': '20px'}
        ),
        dcc.Dropdown(
            id='gender-dropdown',
            options=[{'label': gender, 'value': gender} for gender in sorted(comparison['Gender'].unique())],
            value=sorted(comparison['Gender'].unique())[0],
            style={'width': '40%'}
        )
    ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '30px'}),

    dcc.Graph(id='percent-diff-plot')
], style={'padding': '40px'})


@app.callback(
    Output('percent-diff-plot', 'figure'),
    Input('category-dropdown', 'value'),
    Input('gender-dropdown', 'value')
)
def update_percent_diff_plot(selected_category, selected_gender):
    filtered = comparison[
        (comparison['Category'] == selected_category) &
        (comparison['Gender'] == selected_gender)
    ].sort_values('%_Diff')

    colors = filtered['Color_Class'].map(color_map)

    fig = go.Figure(go.Bar(
        x=filtered['%_Diff'],
        y=filtered['Full_Name'],
        orientation='h',
        marker=dict(color=colors),
        text=filtered['%_Diff'].round(2).astype(str) + '%',
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br>"
            "% Difference: %{x:.2f}%<br>"
            "Result: %{customdata[0]}<br>"
            "Record: %{customdata[1]}<extra></extra>"
        ),
        customdata=filtered[['Result', 'Record']]
    ))

    fig.update_layout(
        title=f"{selected_category} – {selected_gender}: % Slower Than National Record",
        title_x=0.5,
        xaxis_title="% Difference",
        yaxis_title="Athlete",
        yaxis=dict(autorange='reversed'),
        plot_bgcolor='white'
    )

    return fig

# Render-compatible run config
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

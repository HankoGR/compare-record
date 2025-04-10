import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import os

# File path
FILENAME = "Local_meet_results.xlsx"

# Load existing data or create new
if os.path.exists(FILENAME):
    df = pd.read_excel(FILENAME, engine="openpyxl")
else:
    df = pd.DataFrame(columns=["First_Name", "Last_Name", "Category", "Gender", "Result"])

# Clean and prepare
def preprocess(df):
    df = df.copy()
    df['Full_Name'] = df['First_Name'].str.strip() + ' ' + df['Last_Name'].str.strip()
    df['Category'] = df['Category'].str.strip().str.title()
    df['Gender'] = df['Gender'].str.strip().str.title()
    df['Result'] = pd.to_numeric(df['Result'], errors='coerce')
    df = df.dropna(subset=['Result'])
    return df

df = preprocess(df)

# Load records
records_df = pd.read_excel("National_records.xlsx", engine="openpyxl")
records_df.columns = records_df.columns.str.strip()
records_df['Category'] = records_df['Category'].str.strip().str.title()
records_df['Gender'] = records_df['Gender'].str.strip().str.title()
records_df['Record'] = pd.to_numeric(records_df['Record'], errors='coerce')
records_df = records_df.dropna(subset=['Record'])

# App
app = Dash(__name__)

app.layout = html.Div([
    html.H2("🏁 Submit Your Time", style={'textAlign': 'center'}),

    html.Div([
        dcc.Input(id='first-name', type='text', placeholder='First Name', style={'marginRight': '10px'}),
        dcc.Input(id='last-name', type='text', placeholder='Last Name', style={'marginRight': '10px'}),
        dcc.Dropdown(
            id='category',
            options=[{'label': c, 'value': c} for c in sorted(records_df['Category'].unique())],
            placeholder='Category',
            style={'width': '20%', 'marginRight': '10px'}
        ),
        dcc.Dropdown(
            id='gender',
            options=[{'label': g, 'value': g} for g in sorted(records_df['Gender'].unique())],
            placeholder='Gender',
            style={'width': '20%', 'marginRight': '10px'}
        ),
        dcc.Input(id='result', type='number', placeholder='Your Time (e.g. 11.25)', style={'marginRight': '10px'}),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '30px'}),

    dcc.Graph(id='comparison-graph'),
    html.Div(id='submission-confirm', style={'textAlign': 'center', 'marginTop': '10px', 'fontStyle': 'italic'})
], style={'padding': '40px'})


@app.callback(
    Output('comparison-graph', 'figure'),
    Output('submission-confirm', 'children'),
    Input('submit-button', 'n_clicks'),
    State('first-name', 'value'),
    State('last-name', 'value'),
    State('category', 'value'),
    State('gender', 'value'),
    State('result', 'value')
)
def update_dashboard(n_clicks, first, last, category, gender, result):
    if not all([first, last, category, gender, result]):
        return go.Figure(), "Please fill in all fields."

    # Load + update data
    new_entry = pd.DataFrame([{
        'First_Name': first.strip(),
        'Last_Name': last.strip(),
        'Category': category,
        'Gender': gender,
        'Result': result
    }])

    df_existing = pd.read_excel(FILENAME, engine="openpyxl")
    updated_df = pd.concat([df_existing, new_entry], ignore_index=True)
    updated_df.to_excel(FILENAME, index=False)

    df_clean = preprocess(updated_df)

    # Get best results per athlete
    best = df_clean.sort_values('Result').drop_duplicates(['Category', 'Gender', 'Full_Name'], keep='first')

    # Top 6 + current user
    top6 = (
        best[best['Category'] == category][best['Gender'] == gender]
        .sort_values('Result')
        .head(6)
    )

    full_name = f"{first.strip()} {last.strip()}"
    user_row = best[(best['Full_Name'] == full_name) & 
                    (best['Category'] == category) & 
                    (best['Gender'] == gender)]

    if not user_row.empty and full_name not in top6['Full_Name'].values:
        top6 = pd.concat([top6, user_row])

    # Merge with records
    merged = top6.merge(records_df, on=['Category', 'Gender'], how='left')
    merged['%_Diff'] = ((merged['Result'] - merged['Record']) / merged['Record']) * 100
    merged['Ranked_Name'] = [f"{i+1}. {name}" for i, name in enumerate(merged['Full_Name'])]

    colors = ['green' if x <= 1.5 else 'gold' if x <= 3 else 'crimson' for x in merged['%_Diff']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=merged['%_Diff'],
        y=merged['Ranked_Name'],
        orientation='h',
        marker=dict(color=colors),
        text=merged['%_Diff'].round(2).astype(str) + '%',
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br>"
            "% Difference: %{x:.2f}%<br>"
            "Result: %{customdata[0]}<br>"
            "Record: %{customdata[1]}<extra></extra>"
        ),
        customdata=merged[['Result', 'Record']]
    ))

    fig.update_layout(
        title=f"{category} – {gender}: % Slower Than National Record",
        title_x=0.5,
        xaxis_title="% Difference",
        yaxis_title="Athlete",
        yaxis=dict(autorange='reversed'),
        plot_bgcolor='white'
    )

    # Calculate full ranking
    ranking_df = best[(best['Category'] == category) & (best['Gender'] == gender)].sort_values('Result').reset_index(drop=True)
    position = ranking_df[ranking_df['Full_Name'] == full_name].index[0] + 1
    total = len(ranking_df)

    message = (
        f"✅ Result submitted for {full_name} in {category} ({gender}) – Time: {result:.2f} seconds. "
        f"\U0001F3C5 You are currently ranked {position} out of {total}."
    )

    return fig, message


# Render-compatible run
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
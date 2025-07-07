import datetime
import os
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import sqlite3
import pandas as pd
import plotly.express as px
import json


STATUS_COLORS = {
  "completed": "#28a745",
  "in progress": "#ffc107",
  "on hold": "#dc3545",
}



def load_tasks():
    conn = sqlite3.connect("discord_tasks.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['date'] = df['timestamp'].dt.date
    df['week'] = df['timestamp'].dt.strftime('%Y-%U')

    # Parse author JSON field
    def parse_author(raw):
        try:
            obj = json.loads(raw)
            return obj.get('name', raw)
        except:
            return raw

    df['author'] = df['author'].fillna("").apply(parse_author).str.strip()
    df = df[df['author'] != ""]

    df['status'] = df['status'].str.lower()

    return df

def render_filters(df, authors=None):
    today = datetime.date.today()
    author_options = (
        [{"label": a, "value": a} for a in sorted(set(authors))]
        if authors else
        [{"label": a, "value": a} for a in sorted(df['author'].dropna().unique())]
    )

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label(" Author"),
                dcc.Dropdown(options=author_options, id="filter-author", placeholder="Select author", 
                             style={"color": "black"}),
            ],
           ),
            dbc.Col([
                html.Label(" Status"),
                dcc.Dropdown(options=[
                    {"label": "Completed", "value": "completed"},
                    {"label": "In Progress", "value": "in progress"},
                    {"label": "On Hold", "value": "on hold"}
                ], id="filter-status", placeholder="Select status", style={"color": "black"})
            ],
           ),
            dbc.Col([
                html.Label(" Channel"),
                dcc.Dropdown(options=[
                    {"label": c.capitalize(), "value": c} for c in ["front", "back", "database", "général"]
                ], id="filter-channel", placeholder="Select channel", style={"color": "black"})
            ],
          ),
            dbc.Col(
            [
                html.Label("Date Range", style={"marginBottom": "1 rem"}),
                dcc.DatePickerRange(
                    id="filter-date",
                    className="my-picker", 
                    min_date_allowed=df['timestamp'].min().date(),
                    max_date_allowed=today,
                    start_date=df['timestamp'].min().date(),
                    end_date=today,
                    display_format="MM/DD/YYYY",
                    
                    style={"color": "black","width": "100%"},
                ),
            ],
            
            className="d-flex flex-column"
        ),

    ], 
    className="mb-4",
   
    
)
])


def render_analytics_tab(df=None, dark_mode=False):
    if df is None:
        df = load_tasks()

    # KPIs
    total_tasks = len(df)
    tasks_today = len(df[df['date'] == pd.Timestamp.today().date()])
    open_tasks = len(df[df['status'] == "in progress"])
    completed_tasks = len(df[df['status'] == "completed"])
    on_hold_tasks = len(df[df['status'] == "on hold"])
    high_priority_tasks = len(df[df['content'].str.contains("urgent|priority|high", case=False, na=False)])

    # Charts
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    status_counts['status'] = pd.Categorical(status_counts['status'],
                                             categories=['completed', 'in progress', 'on hold'],
                                             ordered=True)
    status_counts = status_counts.sort_values('status')
    status_donut_chart = px.pie(status_counts, names='status', values='count',color='status', hole=0.5,
                                title="Task Status Distribution (Donut)",color_discrete_map=STATUS_COLORS)
    status_donut_chart.update_traces(textinfo='percent+label', pull=[0.05]*len(status_counts))
    status_donut_chart.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    time_trend = df.groupby('date').size().reset_index(name="count")
    line_chart = px.line(time_trend, x='date', y='count', title=" Task Trend Over Time", template='plotly_dark' if dark_mode else 'plotly_white')

    channel_group = df.groupby(['channel', 'status']).size().reset_index(name='count')
    grouped_bar = px.bar(channel_group, x='channel', y='count', color='status', barmode='group',
                         title=" Tasks Per Channel by Status",color_discrete_map=STATUS_COLORS)
    grouped_bar.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    all_authors = df_initial['author'].unique()
    user_summary = df['author'].value_counts().reindex(all_authors, fill_value=0).reset_index()
    user_summary.columns = ['author', 'count']
    user_bar = px.bar(user_summary, x='author', y='count', title="Tasks Per User",
                      color_discrete_sequence=["#6A5ACD"])
    user_bar.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    activity_data = df.groupby(['date', 'author']).size().reset_index(name='tasks')
    grouped_activity_bar = px.bar(activity_data, x='date', y='tasks', color='author',
                                  barmode='group', title="Daily User Activity (Grouped Bar)")
    grouped_activity_bar.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    # Layout
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Alert(f" Total Tasks: {total_tasks}", color="primary")),
            dbc.Col(dbc.Alert(f" Tasks Today: {tasks_today}", color="info")),
            dbc.Col(dbc.Alert(f" Open Tasks: {open_tasks}", color="warning")),
            dbc.Col(dbc.Alert(f" Completed Tasks: {completed_tasks}", color="success")),
            dbc.Col(dbc.Alert(f" On Hold Tasks: {on_hold_tasks}", color="secondary")),
            
        ], className="mb-4"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=status_donut_chart), width=6),
            dbc.Col(dcc.Graph(figure=line_chart), width=6),
        ]),

        html.Hr(),

        dbc.Row([dbc.Col(dcc.Graph(figure=grouped_bar), width=12)]),

        html.Hr(),

        html.H5("Tasks Per User"),
        dcc.Graph(figure=user_bar),

        html.Hr(),

        html.H5(" Daily User Activity"),
        dcc.Graph(figure=grouped_activity_bar),
    ])



df_initial = load_tasks()

def create_dashboard(server=None, dark_mode=False, authors=None):
    
    theme = dbc.themes.DARKLY if dark_mode else dbc.themes.BOOTSTRAP
    
    ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
    app = Dash(__name__,
               server=server,
               url_base_pathname="/dashboard/",
               suppress_callback_exceptions=True,
               external_stylesheets=[theme],
                assets_folder=ASSETS_PATH,
               
               
               )

    app.title = " Task Analytics Dashboard"

    app.layout = dbc.Container([
        html.H2(" Discord Task Analytics", className="mt-4 mb-4 text-center"),
        render_filters(df_initial, authors),
        html.Div(id="analytics-content", children=render_analytics_tab(df_initial, dark_mode)),
        
        dcc.Interval(
            id='interval-component',
            interval=10*1000,  # Refresh every 60 seconds
            n_intervals=0
    )
    ], fluid=True)

    return app



@callback(
    Output("analytics-content", "children"),
    Input("filter-author", "value"),
    Input("filter-status", "value"),
    Input("filter-channel", "value"),
    Input("filter-date", "start_date"),
    Input("filter-date", "end_date"),
    Input("interval-component", "n_intervals")
)

def update_dashboard(author, status, channel, start_date, end_date, n_intervals):
    df = load_tasks()
    if author:
        df = df[df['author'].str.lower() == author.lower()]
    if status:
        df = df[df['status'] == status]
    if channel:
        df = df[df['channel'] == channel]
    if start_date and end_date:
        df = df[(df['timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
                (df['timestamp'].dt.date <= pd.to_datetime(end_date).date())]
    
    return render_analytics_tab(df, dark_mode=True)


if __name__ == "__main__":
    app = create_dashboard(server=None, dark_mode=True)
    app.run_server(debug=True, host="0.0.0.0", port=8050)

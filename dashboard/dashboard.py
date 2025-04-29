from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import sqlite3
import pandas as pd
import plotly.express as px


def load_tasks():
    conn = sqlite3.connect("discord_tasks.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['date'] = df['timestamp'].dt.date
    df['week'] = df['timestamp'].dt.strftime('%Y-%U')  # Week-Year

    # Clean authors
    df['author'] = df['author'].fillna("").str.strip()
    df = df[df['author'] != ""]

    return df


def render_filters(df, authors=None):
    author_options = (
        [{"label": a, "value": a} for a in sorted(set(authors))]
        if authors else
        [{"label": a, "value": a} for a in sorted(df['author'].dropna().unique())]
    )

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("👤 Author"),
                dcc.Dropdown(options=author_options, id="filter-author", placeholder="Select author", style={"color": "black"})
            ]),
            dbc.Col([
                html.Label("📌 Status"),
                dcc.Dropdown(options=[
                    {"label": s, "value": s} for s in df['status'].dropna().unique()
                ], id="filter-status", placeholder="Select status", style={"color": "black"})
            ]),
            dbc.Col([
                html.Label("🏷️ Channel"),
                dcc.Dropdown(options=[
                    {"label": c, "value": c} for c in df['channel'].dropna().unique()
                ], id="filter-channel", placeholder="Select channel", style={"color": "black"})
            ]),
            dbc.Col([
                html.Label("📅 Date Range"),
                dcc.DatePickerRange(
                    id="filter-date",
                    min_date_allowed=df['timestamp'].min().date(),
                    max_date_allowed=df['timestamp'].max().date(),
                    start_date=df['timestamp'].min().date(),
                    end_date=df['timestamp'].max().date()
                )
            ]),
            dbc.Col([
                html.Label("⚠️ High Priority"),
                dcc.Checklist(
                    id="filter-priority",
                    options=[{"label": "Show only high-priority", "value": "high"}],
                    value=[],
                    inline=True
                )
            ])
        ], className="mb-4")
    ])


def render_analytics_tab(df=None, dark_mode=False):
    if df is None:
        df = load_tasks()

    # Calculate KPIs
    total_tasks = len(df)
    tasks_today = len(df[df['date'] == pd.Timestamp.today().date()])
    open_tasks = len(df[df['status'].str.lower() == "in progress"])
    completed_tasks = len(df[df['status'].str.lower() == "completed"])
    high_priority_tasks = len(df[df['content'].str.contains("urgent|priority|high", case=False, na=False)])

    # Charts
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    status_donut_chart = px.pie(status_counts, names='status', values='count', hole=0.5,
                                title="Task Status Distribution (Donut)")
    status_donut_chart.update_traces(textinfo='percent+label', pull=[0.05]*len(status_counts))
    status_donut_chart.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    time_trend = df.groupby('date').size().reset_index(name="count")
    line_chart = px.line(time_trend, x='date', y='count', title="📅 Task Trend Over Time")

    channel_group = df.groupby(['channel', 'status']).size().reset_index(name='count')
    grouped_bar = px.bar(channel_group, x='channel', y='count', color='status', barmode='group',
                         title="📺 Tasks Per Channel by Status")
    grouped_bar.update_layout(template='plotly_dark' if dark_mode else 'plotly_white')

    user_summary = df['author'].value_counts().reset_index()
    user_summary.columns = ['author', 'count']
    user_funnel = px.funnel(user_summary, x='count', y='author', title="🔽 Most Active Users (Funnel View)")

    heatmap_data = df.groupby(['author', 'date']).size().reset_index(name="tasks")
    heatmap_fig = px.density_heatmap(heatmap_data, x="date", y="author", z="tasks",
                                     color_continuous_scale="Viridis", title="🧑‍💼 Daily User Activity")

    return html.Div([

        # KPIs
        dbc.Row([
            dbc.Col(dbc.Alert(f"📋 Total Tasks: {total_tasks}", color="primary")),
            dbc.Col(dbc.Alert(f"🆕 Tasks Today: {tasks_today}", color="info")),
            dbc.Col(dbc.Alert(f"🛠️ Open Tasks: {open_tasks}", color="warning")),
            dbc.Col(dbc.Alert(f"✅ Completed Tasks: {completed_tasks}", color="success")),
            dbc.Col(dbc.Alert(f"🔥 High Priority: {high_priority_tasks}", color="danger")),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=status_donut_chart), width=6),
            dbc.Col(dcc.Graph(figure=line_chart), width=6),
        ]),

        html.Hr(),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=grouped_bar), width=12),
        ]),

        html.Hr(),

        html.H5("Most Active Users"),
        dcc.Graph(figure=user_funnel),

        html.Hr(),

        html.H5("🗓️ Daily User Activity"),
        dcc.Graph(figure=heatmap_fig),
    ])


# Load initial task data
df_initial = load_tasks()


def create_dashboard(server, dark_mode=False, authors=None):
    theme = dbc.themes.DARKLY if dark_mode else dbc.themes.BOOTSTRAP
    app = Dash(
        __name__,
        server=server,
        url_base_pathname="/dashboard/",
        suppress_callback_exceptions=True,
        external_stylesheets=[theme]
    )

    app.title = "📊 Task Analytics Dashboard"

    app.layout = dbc.Container([
        html.H2("📊 Discord Task Analytics", className="mt-4 mb-4 text-center"),
        render_filters(df_initial, authors),
        html.Div(id="analytics-content", children=render_analytics_tab(df_initial, dark_mode)),
    ], fluid=True)

    return app


@callback(
    Output("analytics-content", "children"),
    Input("filter-author", "value"),
    Input("filter-status", "value"),
    Input("filter-channel", "value"),
    Input("filter-date", "start_date"),
    Input("filter-date", "end_date"),
    Input("filter-priority", "value")
)
def update_dashboard(author, status, channel, start_date, end_date, priority):
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

    if priority and "high" in priority:
        df = df[df['content'].str.lower().str.contains("urgent|priority|high", na=False)]

    return render_analytics_tab(df, dark_mode=True)

from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
from flask import Flask
import pandas as pd
import sqlite3
from datetime import datetime


# Load data from classified_sentences.db
def load_data():
    conn = sqlite3.connect("classified_sentences.db")
    df = pd.read_sql_query("SELECT * FROM classified_messages", conn)
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.rename(columns={
        'timestamp': 'Timestamp',
        'author': 'Author',
        'sentence': 'Sentence',
        'category': 'Category',
        'status': 'Status'
    }, inplace=True)

    return df


def create_dashboard(server):
    app = Dash(__name__, server=server, url_base_pathname="/dashboard/", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Ticket Dashboard"

    df = load_data()

    today_str = datetime.today().strftime('%Y-%m-%d')
    df_today = df[df['Timestamp'].dt.strftime('%Y-%m-%d') == today_str]

    category_counts = df['Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']

    status_counts = df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']

    tickets_by_author = df['Author'].value_counts().reset_index()
    tickets_by_author.columns = ['Author', 'Count']

    app.layout = dbc.Container([
        html.H1("📊 Ticket Classification Dashboard", className="my-4 text-center"),

        # Message input + classification
        dbc.Row([
            dbc.Col([
                html.H4("🔍 Classify a New Message"),
                dcc.Textarea(id="message-input", placeholder="Enter your message here...", style={"width": "100%", "height": 100}),
                html.Br(),
                dbc.Button("Classify", id="classify-btn", color="primary", className="mt-2"),
                html.Div(id="classification-output", className="mt-3")
            ], width=6)
        ], className="mb-4"),

        # Metric cards
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("📁 Total Tickets"), html.H2(f"{len(df)}")])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("🗓️ Opened Today"), html.H2(f"{len(df_today)}")])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("✅ Open Tickets"), html.H2(f"{(df['Status'] == 'open').sum()}")])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("🚫 Closed Tickets"), html.H2(f"{(df['Status'] == 'closed').sum()}")])), width=3),
        ], className="mb-4"),

        # Charts
        dbc.Row([
            dbc.Col(dcc.Graph(figure=px.bar(category_counts, x='Category', y='Count', title="Tickets by Category")), width=6),
            dbc.Col(dcc.Graph(figure=px.pie(status_counts, names='Status', values='Count', title="Status Distribution")), width=6),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=px.bar(tickets_by_author, x='Author', y='Count', title="Tickets per Programmer")), width=12)
        ])
    ], fluid=True)

    # Classification callback
    @app.callback(
        Output("classification-output", "children"),
        Input("classify-btn", "n_clicks"),
        State("message-input", "value"),
        prevent_initial_call=True
    )
    def handle_classification(n_clicks, message):
        from text_processing import clean_text, segment_text
        import joblib

        model = joblib.load("random_forest_model.pkl")
        vectorizer = joblib.load("tfidf_vectorizer.pkl")
        label_encoder = joblib.load("label_encoder.pkl")

        def classify_message(text):
            cleaned = clean_text(text)
            segments = segment_text(cleaned)
            if not segments:
                return []
            vectors = vectorizer.transform(segments)
            preds = model.predict(vectors)
            categories = label_encoder.inverse_transform(preds)
            return list(zip(segments, categories))

        if not message:
            return dbc.Alert("❗ Please enter a message.", color="warning")

        results = classify_message(message)
        if not results:
            return dbc.Alert("❌ No valid sentences found.", color="danger")

        # Insert into DB
        try:
            conn = sqlite3.connect("classified_sentences.db")
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for sentence, category in results:
                cursor.execute("""
                    INSERT INTO classified_messages (timestamp, author, sentence, category, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (now, "manual_input", sentence, category, "open"))

            conn.commit()
            conn.close()
        except Exception as e:
            return dbc.Alert(f"❌ Database error: {str(e)}", color="danger")

        return html.Div([
            html.H5("🧠 Classification Result:"),
            html.Ul([html.Li(f"[{cat}] {sent}") for sent, cat in results]),
            dbc.Alert("✅ Stored successfully. Refresh the dashboard to see it!", color="success", className="mt-2")
        ])

    return app

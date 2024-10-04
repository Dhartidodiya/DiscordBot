# Discord Task Management Bot (MVVM Architecture)

This project is a Discord bot built in Python using the **MVVM (Model-View-ViewModel)** architecture. The bot allows users to store tasks, retrieve summaries, and translate content in a multi-channel environment. It leverages technologies such as the `discord.py` library for interaction with Discord, `transformers` for natural language processing, and SQLite for task storage.

## Features

- Store and retrieve tasks in multiple Discord channels.
- Summarize tasks using the T5 language model from Hugging Face's `transformers`.
- Automatically detect and translate tasks into English using `deep-translator`.
- Organize codebase using the **MVVM** architecture for clean separation of concerns.

## Project Structure

```text
/discord-bot-project/
│
├── /model/
│   └── task_model.py
│
├── /viewmodel/
│   └── task_viewmodel.py
│
├── /view/
│   └── task_view.py
│
├── /utils/
│   └── preprocess.py
│
├── .env
├── bot.py
├── requirements.txt
└── README.md
```

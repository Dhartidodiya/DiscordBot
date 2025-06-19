
import discord
import re
from collections import defaultdict
from services.predict_service import PredictService
from model.prediction_model import PredictionModel
from viewmodel.conversation_viewmodel import ConversationViewModel

CATEGORY_TO_CHANNEL = {
    "front": "front",
    "back": "back",
    "database": "database",
    "general": "général"
}

class PredictView(discord.Client):
    def __init__(self, model: PredictionModel, conversation_vm: ConversationViewModel,allowed_guild_id: int, **kwargs):
        intents = kwargs.get("intents", discord.Intents.default())
        super().__init__(intents=intents)
        self.model = model
        self.predict_service = PredictService()
        self.conversation_vm = conversation_vm
        self.allowed_guild_id = allowed_guild_id

    async def on_ready(self):
        print(f"✅ PredictBot ready as {self.user}")

    async def handle_prediction_message(self, message):
        if message.author == self.user or not message.guild:
            return
        
        # Restrict processing to the allowed guild/server
        if message.guild.id != self.allowed_guild_id:
            return

        user_id = str(message.author.id)
        author = str(message.author)
        content = message.content.strip()

        self.conversation_vm.store_user_message(user_id, message.author.name, content)

        predictions = await self.predict_service.predict(content)
        if not predictions:
            await message.channel.send("❌ Aucune prédiction reçue.")
            return

        categorized = defaultdict(lambda: defaultdict(list))
        for item in predictions:
            sentence = item["sentence"]
            category = item.get("category", "general").lower()
            title = item.get("title", "General")
            status = item.get("status") or "completed"
            label    = item.get("label") or "Terminé"
            emoji    = item.get("emoji", "🟢")     
            channel_name = CATEGORY_TO_CHANNEL.get(category, "général")

            self.model.store_prediction(sentence, title, author, channel_name, status,label,emoji)
            categorized[channel_name][title].append((sentence, f"{emoji} {label}"))

        for channel_name, projects in categorized.items():
            target_channel = discord.utils.get(message.guild.text_channels, name=channel_name)
            if not target_channel:
                continue

            for title, items in projects.items():
                formatted = self.format_message(title, author, items)
                await target_channel.send(formatted)

        await message.channel.send("✅ Tâches classées et enregistrées.")

    def format_message(self, title, author, items):
        # Safe-guard: treat None or "" as “Sans titre”
        safe_title = (title or "Sans titre").capitalize()
        title_line = f"> **{safe_title}** [{author}]"
        lines = [f"> ➤  {s.strip().capitalize()} [{st}]" for s, st in items]
        return f"{title_line}\n" + "\n".join(lines)


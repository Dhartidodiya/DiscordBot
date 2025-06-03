import discord
import aiohttp
import os
from datetime import datetime

class ReportView:
    def __init__(self, *, intents: discord.Intents):
        self.report_channel_name = os.getenv("REPORT_CHANNEL_NAME", "report")
        self.report_api_url = os.getenv("REPORT_API_URL")
        self.client = discord.Client(intents=intents)

    async def send_daily_report(self, channel):
        from datetime import datetime
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.report_api_url) as resp:
                    if resp.status != 200:
                        print(f"⚠️ Failed to fetch report. Status: {resp.status}")
                        return
                    data = await resp.json()
        except Exception as e:
            print(f"❌ API fetch error: {e}")
            return

        report_data = data.get("report", [])
        if not report_data:
            await channel.send("🕘 Aucun rapport pour aujourd'hui.")
            return

        header = (
                f">  **Rapport Quotidien d'Activité**\n"
                f"> {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                " "
            )
        await channel.send(header)

        for group in report_data:
            title = group["title"]
            entries = group["entries"]

            lines = [
                f"> **{title.capitalize()}**",  # Bold title
                " " 
            ]

            for entry in entries:
                sentence = entry["sentence"].strip().capitalize()
                status = entry["status"].capitalize()
                author = entry["author"]
                lines.append(f"> ➤ {sentence} [{status}] — 👤 {author}")

            await channel.send("\n".join(lines))


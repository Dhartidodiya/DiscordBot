import discord
import aiohttp
import os
from datetime import datetime, timedelta
import aiohttp
import dateparser
import re

class ReportView:
    def __init__(self, *, intents: discord.Intents, allowed_guild_id: int):
        self.allowed_guild_id = allowed_guild_id
        self.report_channel_name = os.getenv("REPORT_CHANNEL_NAME", "report")
        self.report_api_url = os.getenv("REPORT_API_URL")
        self.client = discord.Client(intents=intents)

    async def send_daily_report(self, channel):
        if channel.guild.id != self.allowed_guild_id:
            print(f"❌ Skipping report: guild ID {channel.guild.id} not allowed.")
            return
       
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
        await channel.send("\u200B")

        for group in report_data:
            title = group.get("title") or " "
            entries = group["entries"]
            
            embed = discord.Embed(
            title=f"**{title.capitalize()}**",
            )


            description_lines = []
            avatar_url = None
            display_name = None

            for entry in entries:
                sentence = entry["sentence"].strip().capitalize()
                status = entry["status"]
                emoji = entry.get("emoji", "")
                author = entry["author"]
                
                member = discord.utils.get(channel.guild.members, name=author)
                avatar_url = member.display_avatar.url if member else None
                display_name = member.display_name if member else author
                
                # Wrap long lines: add spacing before wrapped lines and indent status
                wrapped_sentence = sentence.replace('\n', '\n  ')
                description_lines.append(f"➤ {wrapped_sentence}\n  `{emoji} {status}`")

                # Add task as a field
                embed.add_field(
                    name=f"➤  {sentence}",
                    value=f"`{emoji} {status}`",
                    inline=False
                )
                
                # Set author with avatar image only once per group
                if avatar_url:
                    embed.set_author(name=f".{display_name}", icon_url=avatar_url)
                else:
                    embed.set_author(name=f".{author}")
                
                
            await channel.send(embed=embed)

    
    async def handle_report_query(self, message: discord.Message):
        if message.channel.name != self.report_channel_name:
            return

        query_text = message.content.strip()
        parsed_dates = self.extract_date_range(query_text)

        if not parsed_dates:
            await message.channel.send("❓ Je n'ai pas compris la date. Essayez par ex. 'les tâches d'hier'.")
            return

        from_date, to_date = parsed_dates
        url = f"{self.report_api_url}?q={query_text}"  # 👈 Let API do the parsing

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await message.channel.send("⚠️ Erreur API.")
                        return
                    data = await resp.json()
        except Exception as e:
            await message.channel.send(f"❌ Erreur de récupération : {e}")
            return

        report_data = data.get("report", [])
        if not report_data:
            await message.channel.send("📭 Aucune tâche trouvée pour cette période.")
            return

        for group in report_data:
            title = group.get("title", " ")
            entries = group["entries"]

            embed = discord.Embed(title=f"**{title.capitalize()}**")

            for entry in entries:
                sentence = entry["sentence"].strip().capitalize()
                status = entry["status"]
                emoji = entry.get("emoji", "")
                author = entry["author"]

                embed.add_field(
                    name=f"➤ {sentence}",
                    value=f"`{emoji} {status}`",
                    inline=False
                )

            await message.channel.send(embed=embed)
            
   
    def extract_date_range(self, text: str):
        text = text.lower()
        now = datetime.now()

        if "hier" in text or "yesterday" in text:
            d = now - timedelta(days=1)
            return d, d
        if "aujourd" in text or "today" in text:
            return now, now

        match = re.search(r"(?:from|du)\s+(.*?)\s+(?:to|au|jusqu[’']?à)\s+(.*)", text)
        if match:
            d1 = dateparser.parse(match.group(1), languages=["fr", "en"])
            d2 = dateparser.parse(match.group(2), languages=["fr", "en"])
            if d1 and d2:
                return d1, d2

        single = dateparser.parse(text, languages=["fr", "en"])
        if single:
            return single, single

        return None       
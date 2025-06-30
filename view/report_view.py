import discord
import aiohttp
import os
from datetime import datetime, timedelta
import aiohttp
import dateparser
import re
from utils.date_parser import parse_date_range
from utils.helpers import get_display_name_from_author

class ReportView:
    def __init__(self, *,allowed_guild_id: int):
        self.allowed_guild_id = allowed_guild_id
        self.report_channel_name = os.getenv("REPORT_CHANNEL_NAME", "report")
        self.report_api_url = os.getenv("REPORT_API_URL")
        
    async def send_daily_report(self, channel):
        if channel.guild.id != self.allowed_guild_id:
            print(f" Skipping report: guild ID {channel.guild.id} not allowed.")
            return
       
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.report_api_url) as resp:
                    if resp.status != 200:
                        print(f"Failed to fetch report. Status: {resp.status}")
                        return
                    data = await resp.json()
        except Exception as e:
            print(f" API fetch error: {e}")
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
                
                
                # member = discord.utils.get(channel.guild.members, name=author)
                # avatar_url = member.display_avatar.url if member else None
                # display_name, _ = get_display_name_from_author(author, channel.guild)
                display_name, avatar_url = get_display_name_from_author(author, channel.guild)

                
                # Wrap long lines: add spacing before wrapped lines and indent status
                wrapped_sentence = sentence.replace('\n', '\n  ')
                description_lines.append(f"➤ {wrapped_sentence}\n  `{emoji} {status}`")

                # Add task as a field
                embed.add_field(
                    name=f"➤  {sentence}",
                    value=f"`{emoji} {status}`",
                    inline=False
                )
                
                embed.set_author(name=f".{display_name}")
                
                
            await channel.send(embed=embed)

    
    async def handle_report_query(self, message: discord.Message):
        if message.channel.name != self.report_channel_name:
            return

        query_text = message.content.strip()
        print(f"[DEBUG] Query text: {query_text}")


        user_id = None
        query_user = None
        
        # Extract user mention or plain text username
        mention_match = re.search(r"<@!?(\d+)>", query_text)
        if mention_match:
            user_id = int(mention_match.group(1))
            print(f"[DEBUG] Extracted user_id: {user_id}")
            member = message.guild.get_member(int(user_id))
            query_user = member.name.lower() if member else None
            print(f"[DEBUG] Extracted query_user from mention: {query_user}")
        else:
            user_match = re.search(r"\b(?:de|by)\s+[@\.]?(\w+)", query_text, re.IGNORECASE)
            if user_match:
                query_user = user_match.group(1).lstrip('@.').lower()
                print(f"[DEBUG] Extracted query_user by text: {query_user}")
           

        # Extract status
        status_match = re.search(
            r"\b(?:status\s+)?(en\s+cours|in\s+progress|terminée?|finie?|completed|done)\b",
            query_text.lower()
        )
        query_status = status_match.group(1).lower() if status_match else None
        print(f"[DEBUG] Extracted query_status: {query_status}")
        if query_status in ["done", "terminée", "finie", "completed"]:
            query_status = "completed"
        elif query_status in ["en cours", "in progress"]:
            query_status = "in progress"

        # Extract date range
        from_date, to_date = parse_date_range(query_text)
        print(f"[DEBUG] Extracted date range: {from_date} → {to_date}")

        # If no date found AND no user or status, send clarification message
        if not from_date or not to_date:
            if not query_user and not query_status:
                await message.channel.send("❓ Je n'ai pas compris la date. Essayez par ex. 'rapport d'hier' ou 'du 5 juin au 10 juin'.")
                return
            else:
                from_date = to_date = None  # Dates are optional if user/status exists

        # Construct API URL
        params = []
        
        if user_id and query_status:
            url = f"{self.report_api_url}/report_by_user_and_status"
            params.append(f"user_id={user_id}")
            params.append(f"status={query_status}")
        elif user_id:
            url = f"{self.report_api_url}/report_by_user"
            params.append(f"user_id={user_id}")
        elif query_user and query_status:
            url = f"{self.report_api_url}/report_by_user_and_status"
            params.append(f"user={query_user}")
            params.append(f"status={query_status}")
        elif query_user:
            url = f"{self.report_api_url}/report_by_user"
            params.append(f"user={query_user}")
        elif query_status:
            url = f"{self.report_api_url}/report_by_status"
            params.append(f"status={query_status}")
        else:
            url = f"{self.report_api_url}/daily_report"
            
        
        if from_date and to_date:
            params.append(f"from={from_date}")
            params.append(f"to={to_date}")    
            
        # Combine full URL with parameters
        if params:
            url += "?" + "&".join(params)    
        print(f"[DEBUG] Final API URL: {url}")    
            
        # Call API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    print(f"[DEBUG] API status code: {resp.status}")
                    if resp.status != 200:
                        await message.channel.send("❌ Erreur lors de la récupération du rapport.")
                        return
                    data = await resp.json()
                    print(f"[DEBUG] API response JSON: {data}")
        except Exception as e:
            print(f"[DEBUG] Exception during API call: {e}")
            await message.channel.send(f"❌ Erreur de récupération : {e}")
            return

        report_data = data.get("report", [])
        if not report_data:
            await message.channel.send("❗ Aucune tâche trouvée pour cette période.")
            return

        header = f"> Rapport d'activité"
        if from_date and to_date:
            header += f" : {from_date} → {to_date}"
        await message.channel.send(header)

        for group in report_data:
            title = group.get("title") or " "
            entries = group["entries"]
            embed = discord.Embed(title=title.capitalize())
            field_count = 0
            for entry in entries:
                sentence = entry["sentence"].strip().capitalize()
                emoji = entry.get("emoji", "")
                status = entry["status"]
                time_str = entry.get("time", "")
                
                # Format time 
                if time_str:
                    try:
                        dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
                        formatted_time = dt_obj.strftime("%d/%m/%Y %H:%M")
                    except Exception as e:
                        formatted_time = time_str  # fallback to raw if parsing fails
                else:
                    formatted_time = "N/A"
                
                embed.add_field(
                    name=f"➤ {sentence}",
                    value=f"`{emoji} {status}` |  {formatted_time}",
                    inline=False
                )
                field_count += 1
                if field_count >= 25:
                    await message.channel.send(embed=embed)
                    embed = discord.Embed(title=f"{title.capitalize()} (suite)")
                    field_count = 0
            if field_count > 0:
                await message.channel.send(embed=embed)

            
   
    def extract_date_range(text: str):
        text = text.lower().strip()
        today = datetime.today().date()

        # Handle keywords
        if "aujourd'hui" in text or "today" in text:
            return today, today

        if "hier" in text or "yesterday" in text:
            return today - timedelta(days=1), today - timedelta(days=1)

        # Handle format: 05/06/2025 - 10/06/2025
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s*[-àto]+\s*(\d{1,2}/\d{1,2}/\d{4})", text)
        if match:
            d1 = dateparser.parse(match.group(1), languages=["fr", "en"])
            d2 = dateparser.parse(match.group(2), languages=["fr", "en"])
            if d1 and d2:
                return d1.date(), d2.date()

        # Handle format: "du 5 juin au 10 juin"
        match = re.search(r"(?:from|du)\s+(.*?)\s+(?:to|au|jusqu[’']?à)\s+(.*)", text)
        if match:
            d1 = dateparser.parse(match.group(1), languages=["fr", "en"])
            d2 = dateparser.parse(match.group(2), languages=["fr", "en"])
            if d1 and d2:
                return d1.date(), d2.date()

        # Handle format: "5 juin", "10 June", etc.
        d = dateparser.parse(text, languages=["fr", "en"])
        if d:
            return d.date(), d.date()

        #  No valid date found
        return None
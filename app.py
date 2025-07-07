
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from model.prediction_model import PredictionModel
from model.data_model import DataModel
from threading import Thread
from services.flask_server import create_flask_server
from dashboard.dashboard import create_dashboard 
import discord
from view.predict_view import PredictView
from viewmodel.conversation_viewmodel import ConversationViewModel
from view.report_view import ReportView

 

# Load environment variables from .env file
load_dotenv()

# Get Discord bot token
discord_token = os.getenv('DISCORD_TOKEN')

#  Fetch Report Channel ID from .env file
report_channel_id = int(os.getenv('REPORT_CHANNEL_ID', 0))  # Default to 0 if not found

allowed_guild_id = int(os.getenv("ALLOWED_GUILD_ID", 0))

if not discord_token:
    print(" Error: DISCORD_TOKEN is not set. Please check your .env file!")
    exit()
    

if report_channel_id == 0:
    print(" Warning: REPORT_CHANNEL_ID is not set. Please check your .env file!")

# Instantiate Model, ViewModel, and View
prediction_model = PredictionModel()
data_model = DataModel()
conversation_vm = ConversationViewModel()


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Main bot (handles user messages)
client = PredictView(
    model=prediction_model,
    conversation_vm=conversation_vm,
    allowed_guild_id=allowed_guild_id,
    intents=intents
)

report_client = ReportView(allowed_guild_id=allowed_guild_id)


# Scheduler
scheduler = AsyncIOScheduler()

DASHBOARD_DARK = True

@scheduler.scheduled_job("cron", hour=12, minute=8)
async def send_daily_report():
    print(" Scheduled: Sending daily report...")
    channel = client.get_channel(report_channel_id)
    if not channel:
        print(" Report channel not found.")
        return
    await report_client.send_daily_report(channel)



#  Start Flask dashboard in a new thread
def run_flask(authors):
    flask_app = create_flask_server()  #  Create central Flask app
    dash_app = create_dashboard(flask_app, dark_mode=DASHBOARD_DARK, authors=authors)
    dash_app.run(host="0.0.0.0", port=5000,debug=True,use_reloader=False)


@client.event
async def on_ready():
    print(f" Bot logged in as {client.user}")
    scheduler.start()
    print(" Scheduler started.")
    
    # Get author list from the allowed guild
    authors = set()
    for guild in client.guilds:
        if guild.id == allowed_guild_id:
            async for member in guild.fetch_members(limit=None):
                if not member.bot:
                    authors.add(member.name)
    Thread(target=run_flask, args=(sorted(authors),)).start()

@client.event
async def on_message(message):
    # Ignore bot's own messages or messages outside a guild
    if message.author.bot or not message.guild:
        return

    # Only pass to report handler if in the report channel
    if message.channel.name == os.getenv("REPORT_CHANNEL_NAME", "report"):
        content = message.content.lower()
        if any(word in content for word in ["rapport", "report", "status", "tâches", "tasks"]):
            await report_client.handle_report_query(message)
            return
            
    # Always pass message to the prediction handler
    await client.handle_prediction_message(message)
        

    
if __name__ == "__main__":
    client.run(discord_token)    
    
# # Command to clear a specified number of messages
# @bot.command()
# @commands.has_permissions(manage_messages=True)  # Ensure bot has permission
# async def clear(ctx, amount: int):
#     """Clear a specified number of messages in the channel."""
#     if amount <= 0:
#         await ctx.send("Please specify a valid number of messages to delete.")
#         return
#     await ctx.channel.purge(limit=amount)
#     await ctx.send(f"Cleared {amount} messages.", delete_after=5)

# # Command to clear all messages in the channel
# @bot.command()
# @commands.has_permissions(manage_messages=True)
# async def clear_all(ctx):
#     """Delete all messages in the channel."""
#     async for message in ctx.channel.history(limit=None):
#         try:
#             await message.delete()
#         except discord.Forbidden:
#             await ctx.send("I don't have permission to delete messages.")
#             break
#         except discord.HTTPException as e:
#             await ctx.send(f"Failed to delete a message due to {e}.")
#             break
#     await ctx.send("Cleared all messages in the channel.", delete_after=5)

# # Override the on_ready function
# @bot.event
# async def on_ready():
#     print(f'Logged on as {bot.user}')

# # Run the bot with the token from the .env file
# bot.run(discord_token)






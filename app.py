
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from model.task_model import TaskModel
from model.data_model import DataModel
from viewmodel.task_viewmodel import TaskViewModel
from viewmodel.ml_viewmodel import MLViewModel
from view.task_view import TaskView
from services.data_service import DataService
from threading import Thread
from flask_api import app as flask_app
from dashboard.dashboard import create_dashboard 

import discord
 

# Load environment variables from .env file
load_dotenv()

# Get Discord bot token
discord_token = os.getenv('DISCORD_TOKEN')

# ✅ Fetch Report Channel ID from .env file
report_channel_id = int(os.getenv('REPORT_CHANNEL_ID', 0))  # Default to 0 if not found


if not discord_token:
    print("❌ Error: DISCORD_TOKEN is not set. Please check your .env file!")
    exit()
    

if report_channel_id == 0:
    print("⚠ Warning: REPORT_CHANNEL_ID is not set. Please check your .env file!")

# Instantiate Model, ViewModel, and View
task_model = TaskModel(reset_table=False)
data_model = DataModel()
task_viewmodel = TaskViewModel()
ml_viewmodel = MLViewModel(data_model) 
data_service = DataService(data_model)


intents = discord.Intents.default()
intents.message_content = True
# intents.messages = True  # Ensure the bot can read messages

# # Initialize the bot with commands.Bot, inheriting from TaskView
# bot = commands.Bot(command_prefix="!", intents=intents)

client = TaskView(model=task_model, viewmodel=task_viewmodel,report_channel_id=report_channel_id, intents=intents)


# Setup scheduler for background jobs
scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", hours=12)
async def fetch_and_train():
    """Fetch messages and train the ML model every 12 hours."""
    print("🔄 Scheduled Task: Fetching messages and training the model...")
    fetched_count = await data_service.fetch_and_store_messages(client, channel_name="reporting")
    accuracy = ml_viewmodel.train_model()
    print(f"📊 Fetched {fetched_count} messages and trained the model. Accuracy: {accuracy:.2f}%")

@scheduler.scheduled_job("cron", hour=17)
async def send_daily_report():
    """Send the daily task report at 5 PM."""
    print("📤 Sending daily report...")
    channel = client.get_channel(report_channel_id)
    if channel:
        await client.send_daily_report(channel)
    else:
        print("❌ Report channel not found.")

@client.event
async def on_ready():
    print(f"✅ Bot logged in as {client.user}")
    scheduler.start()
    print("⏰ Scheduler started.")
    
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

create_dashboard(flask_app)



def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)
     

# ✅ Run the Discord bot
if __name__ == "__main__":
    
    # Run Flask in one thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Run Discord bot in main thread
    client.run(discord_token)

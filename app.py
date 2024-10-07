
import os
from dotenv import load_dotenv
from model.task_model import TaskModel
from viewmodel.task_viewmodel import TaskViewModel
from view.task_view import TaskView
import discord
 

# Load environment variables from .env file
load_dotenv()

# Get Discord bot token
discord_token = os.getenv('DISCORD_TOKEN')

# Instantiate Model, ViewModel, and View
task_model = TaskModel(reset_table=False)
task_viewmodel = TaskViewModel()

intents = discord.Intents.default()
intents.message_content = True
# intents.messages = True  # Ensure the bot can read messages

# # Initialize the bot with commands.Bot, inheriting from TaskView
# bot = commands.Bot(command_prefix="!", intents=intents)

client = TaskView(model=task_model, viewmodel=task_viewmodel, intents=intents)


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


# Run the Discord bot
client.run(discord_token)

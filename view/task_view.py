# /view/task_view.py
import discord
from deep_translator import GoogleTranslator
from model.task_model import TaskModel
from viewmodel.task_viewmodel import TaskViewModel
from langdetect import detect
from datetime import datetime, timedelta
from discord.ext import commands
from view.task_ui_componanets import AddTaskView, TaskViewButtons  
from discord.ui import View, Button
from discord import Embed


class TaskView(commands.Bot):
    def __init__(self, model, viewmodel, **options):
        intents = options.get('intents', discord.Intents.default())
        super().__init__(command_prefix="!", intents=intents)
        self.model = model
        self.viewmodel = viewmodel
        self.task_display_message = None  # Store reference to the task display message
        self.additional_task_messages = []  # Track additional task display messages
        self.add_commands()
        
        
    def add_commands(self):
        """Register commands for the bot."""
        print("Registering commands...") 
        
        @self.command()
        async def add_task(ctx):
            print("Add Task Command Triggered")  # Debug: Check if command is triggered
            await ctx.send("Click below to add a new task:", view=AddTaskView(task_view=self))

        @self.command()
        async def manage_tasks(ctx):
            """Display task management UI for all tasks in the database."""
            tasks = self.model.get_all_tasks()

            if not tasks:
                await ctx.send("No tasks available. Use 'Add Task' to create a new task.")
                return

            # Use `self` to access `build_task_embed` if the method is in the same class
            embeds = self.build_task_embed(tasks)

            if not embeds:  # Check if embeds were generated correctly
                await ctx.send("Unable to display tasks. Please try again later.")
                return

            # Send the first embed and track the message
            self.task_display_message = await ctx.send(embed=embeds[0])

            # Clear any previous additional messages
            await self.clear_additional_messages(ctx)

            # Send additional embeds as separate messages
            self.additional_task_messages = []
            for embed in embeds[1:]:
                msg = await ctx.send(embed=embed)
                self.additional_task_messages.append(msg)
                
        async def clear_additional_messages(self, ctx):
            """Delete additional task display messages from the channel."""
            if self.additional_task_messages:
                for msg in self.additional_task_messages:
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass  # Message already deleted or not found
                self.additional_task_messages = []        
                    
    
    def build_task_embed(self, tasks):
        """Create a formatted embed to display the list of tasks grouped by categories."""
        embeds = []
        max_embed_size = 6000
        current_embed = discord.Embed(title="Task List", description="Here are the current tasks:", color=discord.Color.blue())
        current_size = len(current_embed.title) + len(current_embed.description)

        for task in tasks:
            task_id, content, author, channel, timestamp, language = task
            field_value = f"**Author**: {author}\n**Channel**: {channel}\n**Timestamp**: {timestamp}\n**Language**: {language}"
            field_size = len(f"Task {task_id}: {content}") + len(field_value)

            # Check if adding this field will exceed the embed size limit
            if current_size + field_size > max_embed_size:
                # If so, start a new embed
                embeds.append(current_embed)
                current_embed = discord.Embed(title="Task List (Continued)", color=discord.Color.blue())
                current_size = len(current_embed.title)

            current_embed.add_field(
                name=f"Task {task_id}: {content}",
                value=field_value,
                inline=False
            )
            current_size += field_size

        # Append the last embed if it has fields
        if current_embed.fields:
            embeds.append(current_embed)

        return embeds


            

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        for guild in self.guilds:
            print(f"- {guild.name} (ID: {guild.id})")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Preprocess message content
        preprocessed_content = self.viewmodel.preprocess_content(message.content)
        if not preprocessed_content:
            print("Message content is empty after preprocessing. Skipping message.")
            return

        detected_language = self.viewmodel.detect_language(preprocessed_content)
        print(f"detected language in preprossed: {detected_language}")
        target_channels = ['général', 'back', 'front', 'database']

        # Check if the message should be treated as a task
        if (not message.content.startswith(f"<@{self.user.id}>") and not message.content.startswith("!") and
            message.channel.name in target_channels):
            # Store as a regular task if it doesn't start with a mention or command prefix
            self.model.store_task(preprocessed_content, str(message.author), message.channel.name, detected_language)
            print(f"Stored task: {preprocessed_content}")
            return
            if self.user in message.mentions:
                await self.handle_bot_mentions(message, preprocessed_content, detected_language)
                
        # Handle bot mentions or command messages
        if message.content.startswith("!") or self.user in message.mentions:
            await self.process_commands(message)        

    async def handle_bot_mentions(self, message, preprocessed_content, detected_language):
        """Handles all the cases where the bot is mentioned."""
        requested_date = self.viewmodel.extract_date_from_message(preprocessed_content)
        mentioned_user = next((user for user in message.mentions if user != self.user), None)

        if requested_date:
            if mentioned_user:
                # Specific user on a specific date or till a specific date
                if 'till' in preprocessed_content.lower():
                    await self.send_tasks_till_date(message, mentioned_user, requested_date, detected_language)
                else:
                    await self.send_tasks_on_date(message, mentioned_user, requested_date, detected_language)
            else:
                
                 # All users on a specific date or till a specific date
                if 'till' in preprocessed_content.lower():
                    await self.send_all_users_tasks_till_date(message, requested_date, detected_language)
                else:
                    # All users on a specific date
                    await self.send_all_users_tasks_on_date(message, requested_date, detected_language)
                

        elif 'today' or 'aujourd\'hui' in preprocessed_content.lower():
            if mentioned_user:
                await self.send_todays_tasks_for_user(message, mentioned_user, detected_language)
            else:
                await self.send_todays_tasks_for_all_users(message, detected_language)
                
        elif 'yesterday' or 'hier' in preprocessed_content.lower():
            if mentioned_user:
                await self.send_yesterdays_tasks_for_user(message, mentioned_user, detected_language)
            else:
                await self.send_yesterdays_tasks_for_all_users(message, detected_language)        
                
        elif mentioned_user:
            await self.send_all_tasks_for_user(message, mentioned_user, detected_language)

    async def send_all_users_tasks_on_date(self, message, requested_date, detected_language):
        tasks_by_date = self.model.get_tasks_by_date(requested_date)
        if tasks_by_date:
            final_report = self.build_task_summary(tasks_by_date)
            final_report = self.viewmodel.translate_if_needed(final_report, detect(final_report), detected_language)
            await self.send_long_message(message.channel, final_report)
        else:
            await message.channel.send(f"No tasks found for any user on {requested_date}.")
            
    async def send_all_users_tasks_till_date(self, message, requested_date, detected_language):
        """Retrieve tasks for all users till a specific date."""
        
        tasks_till_date = self.model.get_tasks_till_date(requested_date)
        
        final_report = self.build_task_summary(tasks_till_date, include_date=True)
        
        # Translate the report if necessary
        final_report = self.viewmodel.translate_if_needed(final_report, detect(final_report), detected_language)
        
        await self.send_long_message(message.channel, final_report)
        
                

    async def send_todays_tasks_for_all_users(self, message, detected_language):
        
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        await self.send_all_users_tasks_on_date(message, today_date, detected_language)
        
    async def send_yesterdays_tasks_for_all_users(self, message, detected_language):
        
        """Retrieve yesterday's tasks for all users."""
        
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        await self.send_all_users_tasks_on_date(message, yesterday_date, detected_language)
        
            

    async def send_tasks_on_date(self, message, mentioned_user, requested_date, detected_language):
        """Retrieve tasks for a specific user on a given date."""
        query_author = str(mentioned_user)
        tasks = self.model.get_tasks_by_author_and_date(query_author, requested_date)
        await self.send_user_report(message, tasks, query_author, requested_date, detected_language)

    async def send_tasks_till_date(self, message, mentioned_user, requested_date, detected_language):
        query_author = str(mentioned_user)
        tasks_till_date = self.model.get_tasks_by_author_till_date(query_author, requested_date)
        await self.send_user_report(message, tasks_till_date, query_author, requested_date, detected_language, till=True)

    async def send_todays_tasks_for_user(self, message, mentioned_user, detected_language):
        
        query_author = str(mentioned_user)
        tasks = self.model.get_todays_tasks_by_author(query_author)
        await self.send_user_report(message, tasks, query_author, 'today', detected_language) 
        
        
    async def send_yesterdays_tasks_for_user(self, message, mentioned_user, detected_language):
        """Retrieve yesterday's tasks for a specific user."""
        query_author = str(mentioned_user)
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        await self.send_user_report(message, self.model.get_tasks_by_author_and_date(query_author, yesterday_date), query_author, 'yesterday', detected_language)    

    async def send_all_tasks_for_user(self, message, mentioned_user, detected_language):
        query_author = str(mentioned_user)
        tasks = self.model.get_tasks_by_author(query_author)
        await self.send_user_report(message, tasks, query_author, 'all', detected_language)
        
        
    async def send_user_report(self, message, tasks, query_author, date_desc, detected_language, till=False):
        """Format and send the user-specific report."""
        if tasks:
            summary = self.viewmodel.format_task_summary(query_author, tasks, include_date=True)
            summary = self.viewmodel.translate_if_needed(summary, detect(summary), detected_language)
            report_type = f" till {date_desc}" if till else f" on {date_desc}"
            await message.channel.send(f"Here is the task summary for {query_author}{report_type}:\n{summary}")
        else:
            await message.channel.send(f"No tasks found for {query_author}{' till ' if till else ' on '}{date_desc}.")
            
            
    async def send_report(self, message, tasks_by_user, empty_msg, detected_language):
        """Format and send the report for multiple users."""
        if tasks_by_user:
            final_report = self.build_task_summary(tasks_by_user)
            final_report = self.viewmodel.translate_if_needed(final_report, detect(final_report), detected_language)
            await self.send_long_message(message.channel, final_report)
        else:
            await message.channel.send(empty_msg)            

    def build_task_summary(self, tasks_by_date,include_date=False):
        """Builds a summary of tasks for multiple users."""
        all_users_summary = [
            self.viewmodel.format_task_summary(author, tasks,include_date=include_date)
            for author, tasks in tasks_by_date.items()
        ]
        return "\n".join(all_users_summary)

    async def send_long_message(self, channel, content, max_length=2000):
        """Splits a long message into smaller chunks and sends them sequentially."""
        for i in range(0, len(content), max_length):
            await channel.send(content[i:i + max_length])
            
            
 
        

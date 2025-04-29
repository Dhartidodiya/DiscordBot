import os
import discord
import asyncio
from datetime import datetime, timedelta
from discord.ext import tasks,commands
from view.task_ui_componanets import AddTaskView, TaskListView
from viewmodel.conversation_viewmodel import ConversationViewModel
import re
from classify_model.classifier import classify_message
import requests


# Map predicted categories to actual Discord channel names
CATEGORY_TO_CHANNEL = {
    "front": "front",
    "back": "back",
    "database": "database",
    "general": "général"  # Optional fallback
}


class TaskView(commands.Bot):
    def __init__(self, model, viewmodel, report_channel_id, **options):
        intents = options.get("intents", discord.Intents.default())
        super().__init__(command_prefix="!", intents=intents)
        self.model = model
        self.viewmodel = viewmodel
        self.report_channel_id = report_channel_id  # Channel ID for daily reports
        self.task_display_message = None  # Store reference to the task display message
        self.additional_task_messages = []
        
        # ✅ Register all commands properly
        self.conversation_vm = ConversationViewModel()
        self.cache = {} 
        self.add_commands()
    
    
    async def on_ready(self):
        """Bot startup log."""
        print(f"✅ Logged in as {self.user}")
        
        
         
        
    def add_commands(self):
        """Register commands for the bot."""
        print("Registering commands...")

        @self.command()
        async def add_task(ctx, *, task_content: str = None):
            """ Adds a task directly if text is provided after !add_task, otherwise shows the 'Add Task' button. """
            if task_content:
                self.model.store_task(task_content, "No Description", str(ctx.author), ctx.channel.name)
                await self.update_task_display(ctx)
                await ctx.send(f"✅ Task '{task_content}' added successfully!", delete_after=5)
                return

            await ctx.send("Click below to add a task:", view=AddTaskView(self))

        @self.command()
        async def manage_tasks(ctx):
            """ Displays the task list. """
            tasks = self.model.get_all_tasks()
            if not tasks:
                await ctx.send("📌 No tasks available. Use `!add_task` to create a new task.")
                return

            if self.task_display_message:
                await self.task_display_message.edit(view=TaskListView(tasks, self))
            else:
                self.task_display_message = await ctx.send(view=TaskListView(tasks, self))
        
        @self.command(name="daily_report")
        async def daily_report(ctx):
            """Manually triggers the daily report for testing."""
            await self.send_daily_report(ctx.channel)

    async def send_daily_report(self, channel):
        """Generates and sends the daily task report with profile pictures."""
        tasks_today = self.model.get_tasks_for_today()

        if not tasks_today:
            await channel.send("📌 No tasks submitted today.")
            return

        for task_id, content, description, author_name, channel_name, status, timestamp in tasks_today:
            # Step 1: Handling timestamp parsing
            # If timestamp is a string, we attempt to parse it using multiple formats
            if isinstance(timestamp, str):
                print(f"⚠ Invalid timestamp format for task {task_id}. Timestamp: {timestamp}")  # Log the timestamp
                valid = False
                # List of formats to try parsing the timestamp
                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):  
                    try:
                        timestamp = datetime.strptime(timestamp, fmt)  # Try parsing using the current format
                        valid = True  # If successful, mark as valid
                        break  # Exit the loop once a valid format is found
                    except ValueError:
                        continue  # If parsing fails, try the next format
                
                # If no valid timestamp format is found, log the error and skip processing the task
                if not valid:
                    print(f"⚠ Invalid timestamp format for task {task_id}. Skipping...")
                    continue

            # Step 2: Fetching the user by author name
            # Fetch the user object based on author name
            user = await self.fetch_user_by_name(author_name)
            
             # Log the avatar URL for debugging
            if user and user.avatar:
                print(f"Avatar URL for {author_name}: {user.avatar.url}")
            else:
                print(f"No avatar found for {author_name}, using default avatar.")

            # Step 3: Creating the Embed for the task
            embed = discord.Embed(
                title="📊 Rapport Quotidien d'Activité",
                description=f"**Projet :** {content}\n\n{description if description else 'No description provided.'}",  # Add description or fallback text
                color=discord.Color.blue(),  # Set the color of the embed
                timestamp=timestamp  # Set the timestamp for when the report was created
            )

            # Step 4: Adding fields to the embed
            embed.add_field(name="🏷 Channel", value=channel_name, inline=True)  # Add channel name
            embed.add_field(name="📌 Status", value=status, inline=True)  # Add task status
            embed.add_field(name="📅 Date", value=timestamp.strftime('%d/%m/%Y %H:%M'), inline=False)  # Format and add the task's timestamp as date

            # Step 5: Adding the user's profile picture or default avatar
            if user:
                icon_url = user.avatar.url if user.avatar else user.default_avatar.url
                embed.set_author(name=author_name, icon_url=icon_url)
            else:
                embed.set_author(name=author_name, icon_url="https://example.com/default-avatar.png")  # Use a default avatar image
                    # Step 6: Add footer to the embed
            embed.set_footer(text="Rapport généré automatiquement")  # Set footer text

                    # Step 7: Send the embed to the specified channel
            await channel.send(embed=embed)

            
    async def fetch_user_by_name(self, name):
        """Fetch a user object by their name (case-insensitive search)."""
        for guild in self.guilds:
            for member in guild.members:
                if member.name.lower() == name.lower():
                    return member
        return None

    
    def format_daily_report(self, tasks):
        """Formats the daily report as plain text for fallback."""
        report_lines = []

        for task_id, content, description, author, channel, status, timestamp in tasks:
            task_details = (
                f"\n👤 **Author:** {author}\n"
                f"📅 **Date:** {timestamp.strftime('%d/%m/%Y %H:%M')}\n"
                f"🏷 **Channel:** {channel}\n"
                f"📌 **Status:** {status}\n"
                f"📊 **Project/Task:** {content}\n"
                f"✏️ **Description:** {description if description else 'No description provided'}\n"
                "------------------------------------"
            )
            report_lines.append(task_details)

        return "\n".join(report_lines)
   
    
    
    def seconds_until_5pm(self):
        """Calculates seconds until the next 5 PM."""
        now = datetime.now()
        five_pm = now.replace(hour=17, minute=0, second=0, microsecond=0)  # 5 PM today

        if now >= five_pm:
            # If it's already past 5 PM today, schedule for tomorrow
            five_pm += timedelta(days=1)

        return (five_pm - now).total_seconds()

    @tasks.loop(hours=24)
    async def schedule_daily_report(self):
        """Waits until 5 PM then sends the daily report."""
        await self.wait_until_ready()
        seconds_until_report = self.seconds_until_5pm()

        print(f"⏳ Waiting {seconds_until_report} seconds until 5 PM report...")
        await asyncio.sleep(seconds_until_report)  # Wait until 5 PM

        report_channel = self.get_channel(self.report_channel_id)
        if report_channel:
            await self.send_daily_report(report_channel)
        else:
            print("❌ Report channel not found. Check channel ID!")


    
    async def process_commands(self, message):
        """Ensures commands are processed correctly."""
        ctx = await self.get_context(message)
        if ctx.command is not None:
            await self.invoke(ctx)
                        
    async def on_message(self, message):
        """Handles message processing for task updates and filtering."""
        if message.author == self.user:
            return
        
        # ✅ Only allow classification in Dharti server
        ALLOWED_GUILD_ID = int(os.getenv("ALLOWED_GUILD_ID", 0))  
        if message.guild and message.guild.id != ALLOWED_GUILD_ID:
            return

        user_id = str(message.author.id)
        content = message.content.strip()
        
        # ✅ Store user message in conversation memory
        self.conversation_vm.store_user_message(user_id, message.author.name, content)
        classification = classify_message(content)

        # Route classified sentences to their respective channels
        if classification:
            payload = {
                "author": str(message.author),
                "results": classification
            }

            try:
                # 🛠 Use your Render API URL after deployment
                requests.post("http://localhost:5000/api/classify", json=payload)
            except Exception as e:
                print("❌ Failed to send to API:", e)

            # Optional: Send feedback in Discord
            for item in classification:
                await message.channel.send(
                    f"🔍 **Sentence**: `{item['sentence']}`\n📁 **Category**: `{item['category']}`"
                )

        
       # ✅ NLP-Based Discussion Retrieval (`!discuss <topic>`)
        if content.startswith("!discuss"):
            query = content.replace("!discuss", "").strip()

            if not query:
                await message.channel.send("❌ Veuillez spécifier un sujet. Exemple: `!discuss banque`")
                return

            # ✅ Check cache first
            if (user_id, query) in self.cache:
                response = self.cache[(user_id, query)]
            else:
                past_conversations = self.conversation_vm.get_past_messages(user_id, query)
                related_tasks = self.model.get_tasks_by_keyword(query)  # ✅ Fetch related tasks

                if past_conversations or related_tasks:
                    response = f"📌 Discussions et tâches précédentes sur '{query}':\n\n"
                    
                    # ✅ Display conversations
                    if past_conversations:
                        response += "**📜 Conversations:**\n"
                        for msg, timestamp in past_conversations:
                            response += f"📅 {timestamp}: {msg}\n"

                    # ✅ Display related tasks
                    if related_tasks:
                        response += "\n**✅ Tâches associées:**\n"
                        for task in related_tasks:
                            response += f"🔹 {task[1]} (Statut: {task[5]})\n"

                else:
                    response = f"❌ Aucune discussion ni tâche trouvée sur '{query}'."

                # ✅ Cache the result
                self.cache[(user_id, query)] = response  

            await message.channel.send(response)
            return

        # ✅ Detects task updates using the pattern: taskname -> status
        task_update_pattern = re.match(r"(.+)\s*->\s*(.+)", message.content.strip())
        if task_update_pattern:
            task_name, raw_status = task_update_pattern.groups()
            new_status = self.model.normalize_status(raw_status.strip())

            # ✅ Check if the task exists
            task = self.model.get_task_by_name(task_name.strip())
            if task:
                task_id = task[0]
                self.model.update_task_status(task_id, new_status)
                await message.channel.send(f"✅ Task **'{task_name}'** updated to **'{new_status}'**!")
                await self.update_task_display(message.channel)
            else:
                await message.channel.send(f"❌ Task **'{task_name}'** not found.")
            return

        # ✅ Task List Filtering with `!manage_list`
        # Detects the !manage_list command
        if message.content.lower().startswith("!manage_list"):
            filter_query = message.content.replace("!manage_list", "").strip()
            print(f"Filter query received: {filter_query}")  # Debugging log

            if not filter_query:
                tasks = list(self.model.get_all_tasks())  # Ensure tasks is a list
                print(f"All tasks found: {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send("📌 No tasks available.")
                    return

                await self.display_task_list(message.channel, tasks)
                return

            # Date variables for filtering
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

            # Check for mentions (author filter)
            if message.mentions:
                author_name = str(message.mentions[0])
                tasks = list(self.model.get_tasks_by_author(author_name))
                print(f"Tasks by {author_name}: {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send(f"❌ No tasks found for author: {author_name}")
                    return

                await self.display_task_list(message.channel, tasks, f"Tasks by {author_name}")
                return

            # Check for task by name
            task = self.model.get_task_by_name(filter_query)
            if task:
                print(f"Task found by name: {task}")  # Debugging log
                await self.display_task_list(message.channel, [task], f"Tasks for '{filter_query}'")
                return

            # Check for specific date keywords (today, yesterday, tomorrow)
            if filter_query.lower() in ["today", "yesterday", "tomorrow"]:
                date_map = {"today": today, "yesterday": yesterday, "tomorrow": tomorrow}
                tasks = list(self.model.get_tasks_by_date(date_map[filter_query.lower()]))
                print(f"Tasks for {filter_query.capitalize()}: {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send(f"📌 No tasks found for {filter_query.capitalize()}.")
                    return

                await self.display_task_list(message.channel, tasks, f"Tasks for {filter_query.capitalize()}")
                return

            # Check for a specific date pattern (e.g., 2025-02-13)
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filter_query)
            if date_match:
                specific_date = date_match.group(1)
                tasks = list(self.model.get_tasks_by_date(specific_date))
                print(f"Tasks for date {specific_date}: {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send(f"📌 No tasks found for date {specific_date}.")
                    return

                await self.display_task_list(message.channel, tasks, f"Tasks on {specific_date}")
                return

            # Check for status keywords (In Progress, On Hold, Completed)
            normalized_status = self.model.normalize_status(filter_query)
            if normalized_status in ["In Progress", "On Hold", "Completed"]:
                tasks = list(self.model.get_tasks_by_status(normalized_status))
                print(f"Tasks with status '{normalized_status}': {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send(f"📌 No tasks found with status '{normalized_status}'.")
                    return

                await self.display_task_list(message.channel, tasks, f"Tasks with status '{normalized_status}'")
                return

            # Check for date range (from YYYY-MM-DD till YYYY-MM-DD)
            date_range_match = re.search(r"(\d{2}/\d{2}/\d{4}) (\d{2}/\d{2}/\d{4})", filter_query.lower())
            if date_range_match:
                from_date_str, till_date_str = date_range_match.groups()
                
                # Convert DD/MM/YYYY to YYYY-MM-DD for SQL queries
                from_date = datetime.strptime(from_date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                till_date = datetime.strptime(till_date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                
                tasks = list(self.model.get_tasks_between_dates(from_date, till_date))
                print(f"Tasks from {from_date} to {till_date}: {len(tasks)}")  # Debugging log

                if not tasks:
                    await message.channel.send(f"📌 No tasks found from {from_date_str} to {till_date_str}.")
                    return

                await self.display_task_list(message.channel, tasks, f"Tasks from {from_date_str} to {till_date_str}")
                return


            # If no filter matches
            print("No matching filter found.")  # Debugging log
            await message.channel.send("❌ No tasks found with the specified filter.")
            
        await self.process_commands(message)

    async def display_task_list(self, channel, tasks, title="Task List"):
        """Displays task list with pagination."""
        if not tasks:
            await channel.send(f"📌 No tasks found for '{title}'.")
            return

        if self.task_display_message:
            try:
                await self.task_display_message.edit(view=TaskListView(tasks, self))
            except discord.NotFound:
                self.task_display_message = await channel.send(view=TaskListView(tasks, self))
        else:
            self.task_display_message = await channel.send(view=TaskListView(tasks, self))

    async def update_task_display(self, ctx):
        """Refreshes the task list UI."""
        tasks = self.model.get_all_tasks()
        if not tasks:
            await ctx.send("📌 No tasks available.", ephemeral=True)
            return

        if self.task_display_message:
            try:
                await self.task_display_message.edit(view=TaskListView(tasks, self))
            except discord.NotFound:
                self.task_display_message = await ctx.send(view=TaskListView(tasks, self))
        else:
            self.task_display_message = await ctx.send(view=TaskListView(tasks, self))

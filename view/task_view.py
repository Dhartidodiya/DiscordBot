import discord
import asyncio
from datetime import datetime, timedelta
from discord.ext import tasks,commands
from view.task_ui_componanets import AddTaskView, TaskListView
import re


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
        self.add_commands()
    
    
    async def on_ready(self):
        """Bot startup log."""
        print(f"✅ Logged in as {self.user}")
        self.schedule_daily_report.start()  # Start the automatic report scheduler
        
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
        """Generates and sends the daily task report."""
        tasks_today = self.model.get_tasks_for_today()

        if not tasks_today:
            await channel.send("📌 No tasks submitted today.")
            return

        report_message = self.format_daily_report(tasks_today)
        await channel.send(f"📊 **Daily Task Report - {datetime.now().strftime('%Y-%m-%d')}**\n\n{report_message}")
    
    def format_daily_report(self, tasks):
        """Formats the daily report from task list."""
        report = []
        for task_id, content, description, author, channel, status, timestamp in tasks:
            task_details = (
                f"🔹 **{content}** (Status: {status})\n"
                f"   📌 *{description if description else 'No description'}*\n"
                f"   👤 **{author}** | 🏷 **{channel}** | ⏰ {timestamp}\n"
            )
            report.append(task_details)

        return "\n".join(report)    
    
    
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
        if message.content.lower().startswith("!manage_list"):
            filter_query = message.content.replace("!manage_list", "").strip()

            if not filter_query:
                tasks = self.model.get_all_tasks()
                if not tasks:
                    await message.channel.send("📌 No tasks available.")
                    return
                await self.display_task_list(message.channel, tasks)
                return

            # ✅ Filter Logic
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

            if message.mentions:
                author_name = str(message.mentions[0])
                tasks = self.model.get_tasks_by_author(author_name)
                await self.display_task_list(message.channel, tasks, f"Tasks by {author_name}")
                return

            task = self.model.get_task_by_name(filter_query)
            if task:
                await self.display_task_list(message.channel, [task], f"Tasks for '{filter_query}'")
                return

            if filter_query.lower() in ["today", "yesterday", "tomorrow"]:
                date_map = {"today": today, "yesterday": yesterday, "tomorrow": tomorrow}
                tasks = self.model.get_tasks_by_date(date_map[filter_query.lower()])
                await self.display_task_list(message.channel, tasks, f"Tasks for {filter_query.capitalize()}")
                return

            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filter_query)
            if date_match:
                specific_date = date_match.group(1)
                tasks = self.model.get_tasks_by_date(specific_date)
                await self.display_task_list(message.channel, tasks, f"Tasks on {specific_date}")
                return

            normalized_status = self.model.normalize_status(filter_query)
            if normalized_status in ["In Progress", "On Hold", "Completed"]:
                tasks = self.model.get_tasks_by_status(normalized_status)
                await self.display_task_list(message.channel, tasks, f"Tasks with status '{normalized_status}'")
                return

            date_range_match = re.match(r"from (\d{4}-\d{2}-\d{2}) till (\d{4}-\d{2}-\d{2})", filter_query.lower())
            if date_range_match:
                from_date, till_date = date_range_match.groups()
                tasks = self.model.get_tasks_between_dates(from_date, till_date)
                await self.display_task_list(message.channel, tasks, f"Tasks from {from_date} to {till_date}")
                return

            await message.channel.send("❌ No tasks found with the specified filter.")
            return

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

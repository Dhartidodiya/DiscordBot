import discord
from discord.ui import View, Button, Modal, TextInput,Select
from functools import partial
from discord import SelectOption


def truncate_text(text, max_length=80):
    """Ensures text does not exceed max_length, truncates if necessary."""
    return text if len(text) <= max_length else text[:max_length - 3] + "..."

class AddTaskView(View):
    """UI View that shows an 'Add Task' button after using `!add_task`."""
    
    def __init__(self, task_view):
        super().__init__(timeout=None)
        self.task_view = task_view
        self.add_item(AddTaskButton(task_view))

 
        
class AddTaskButton(Button):
    """Button that opens the task creation modal."""
    
    def __init__(self, task_view):
        super().__init__(label="Add Task", style=discord.ButtonStyle.green, emoji="➕")
        self.task_view = task_view

    async def callback(self, interaction: discord.Interaction):
        """Opens the task creation modal."""
        await interaction.response.send_modal(AddTaskModal(self.task_view))       


class AddTaskModal(Modal):
    """🔥 Instantly adds task & updates task list."""

    def __init__(self, task_view):
        super().__init__(title="📝 Add a New Task")
        self.task_view = task_view
        self.task_name = TextInput(label="Task Name", placeholder="Enter task name...")
        self.task_description = TextInput(label="Task Description", style=discord.TextStyle.paragraph, placeholder="Enter task details...", required=False)
        self.add_item(self.task_name)
        self.add_item(self.task_description)

    async def on_submit(self, interaction: discord.Interaction):
        """Store the task and immediately update the task list UI."""
        task_name = self.task_name.value.strip()
        task_description  = self.task_description.value.strip()

        if not task_name:
            await interaction.response.send_message("⚠ Task name cannot be empty!", ephemeral=True)
            return

        # ✅ Store the task in the database
        self.task_view.model.store_task(task_name,task_description, str(interaction.user), interaction.channel.name)

        # ✅ Fetch the updated tasks
        tasks = self.task_view.model.get_all_tasks()

        # ✅ Update the task list UI immediately
        if self.task_view.task_display_message:
            try:
                await self.task_view.task_display_message.edit(view=TaskListView(tasks, self.task_view))
            except discord.NotFound:
                self.task_view.task_display_message = await interaction.channel.send(view=TaskListView(tasks, self.task_view))
        else:
            self.task_view.task_display_message = await interaction.channel.send(view=TaskListView(tasks, self.task_view))

        # ✅ Send confirmation
        await interaction.response.send_message(f"✅ Task '{task_name}' added!", ephemeral=True)


 
class TaskListView(View):
    """Displays Task List with Pagination, Status, and Edit/Delete Actions."""

    STATUS_COLORS = {
        "Completed": "🟢",  # Green
        "In Progress": "🟡",  # Yellow
        "On Hold": "🔴"  # Red
    }

    STATUS_OPTIONS = [
        discord.SelectOption(label="✅ Completed", value="Completed", emoji="🟢"),
        discord.SelectOption(label="⏳ In Progress", value="In Progress", emoji="🟡"),
        discord.SelectOption(label="⏹ On Hold", value="On Hold", emoji="🔴"),
    ]

    def __init__(self, tasks, task_view, page=0, tasks_per_page=5):
        super().__init__(timeout=None)
        self.task_view = task_view
        self.tasks = tasks
        self.page = page
        self.tasks_per_page = tasks_per_page
        self.total_pages = (len(tasks) // tasks_per_page) + (1 if len(tasks) % tasks_per_page > 0 else 0)
 

        start_idx = page * tasks_per_page
        end_idx = start_idx + tasks_per_page
        current_tasks = self.tasks[start_idx:end_idx]

        # ✅ Iterate through the current page's tasks
        for index, task in enumerate(current_tasks):
            if len(task) < 7:
                print(f"⚠ Unexpected task format: {task}")
                continue  # Skip incorrectly formatted tasks

            task_id, name,description, author, channel, status, timestamp = task
            status_emoji = self.STATUS_COLORS.get(status, "⚪")  # Default to ⚪ if unknown
            truncated_name = name[:50] + "..." if len(name) > 50 else name
            
            # ✅ Each Task on a Separate Row
            row = index  # Ensures a new row for each task

            # ✅ Task Name Button
            task_button = Button(
                label=f"{status_emoji} {truncated_name}",
                style=discord.ButtonStyle.primary,
                custom_id=f"task_{task_id}",
                row=row  # ✅ Each task gets a new row
            )
            task_button.callback = self.create_task_callback(task_id, name, description, author, status, timestamp)

            # ✅ Edit & Delete Buttons (Only for Author)
            edit_button = Button(emoji="🖊", style=discord.ButtonStyle.success, custom_id=f"edit_{task_id}", row=row)
            delete_button = Button(emoji="❌", style=discord.ButtonStyle.secondary, custom_id=f"delete_{task_id}", row=row)

            edit_button.callback = self.create_edit_callback(task_id, name, description,status)
            delete_button.callback = self.create_delete_callback(task_id, name)

            self.add_item(task_button)
            self.add_item(edit_button)
            self.add_item(delete_button)

        # ✅ Pagination Buttons (Only show if there are multiple pages)
        pagination_row = 4  
        if self.total_pages > 1:
            if self.page > 0:
                prev_button = Button(label="⬅", style=discord.ButtonStyle.blurple, custom_id="prev_page", row=pagination_row)
                prev_button.callback = lambda i: self.change_page(i, self.page - 1)
                self.add_item(prev_button)

            if self.page < self.total_pages - 1:
                next_button = Button(label="➡", style=discord.ButtonStyle.blurple, custom_id="next_page", row=pagination_row)
                next_button.callback = lambda i: self.change_page(i, self.page + 1)
                self.add_item(next_button)


    # ✅ Creates a callback for viewing task details
    def create_task_callback(self, task_id, task_name, description, author, status, timestamp):
        async def callback(interaction: discord.Interaction):
            embed = discord.Embed(title="📌 Task Details", color=discord.Color.blue())
            embed.add_field(name="📄 **Task Name**", value=f"```{task_name}```", inline=False)
            embed.add_field(name="👤 **Author**", value=f"```{author}```", inline=False)
            embed.add_field(name="📝 **Task Description**", value=f"```{description if description else 'No details provided'}```", inline=False)  # ✅ Added
            embed.add_field(name="📆 **Created At**", value=f"```{timestamp}```", inline=False)
            embed.add_field(name="📌 **Status**", value=f"```{status}```", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        return callback

    # ✅ Creates a callback for editing a task
    def create_edit_callback(self, task_id, task_name,task_description,task_status):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(EditTaskModal(task_id, task_name,task_description, task_status,self.task_view))

        return callback

    # ✅ Creates a callback for deleting a task
    def create_delete_callback(self, task_id, task_name):
        async def callback(interaction: discord.Interaction):
            self.task_view.model.delete_task_by_id(task_id)
            await interaction.response.send_message(f"🗑 Task '{task_name}' deleted!", ephemeral=True)
            await self.task_view.update_task_display(interaction)

        return callback

    # ✅ Handles pagination
    async def change_page(self, interaction, new_page):
        new_view = TaskListView(self.tasks, self.task_view, page=new_page)
        await interaction.response.edit_message(view=new_view)

  
class ViewTaskModal(Modal):
    """Modal that displays task details."""
    
    def __init__(self, task_id, task_name, task_description, author, status, timestamp):
        super().__init__(title="📄 Task Details")
        self.add_item(TextInput(label="Task Name", default=task_name, disabled=True))
        self.add_item(TextInput(label="Task Description", default=task_description or "No description", disabled=True))
        self.add_item(TextInput(label="Author", default=author, disabled=True))
        self.add_item(TextInput(label="Status", default=status or "Pending", disabled=True))
        self.add_item(TextInput(label="Created At", default=timestamp, disabled=True))
        
        
        
class EditTaskButton(Button):
    """Edit Button with Pencil Icon."""
    
    def __init__(self, task_id, task_name, task_details, task_view):
        super().__init__(emoji="✏", style=discord.ButtonStyle.blurple)
        self.task_id = task_id
        self.task_name = task_name
        self.task_details = task_details
        self.task_view = task_view

    async def callback(self, interaction):
        """Opens a modal to edit a task."""
        await interaction.response.send_modal(EditTaskModal(self.task_id, self.task_name, self.task_details, self.task_view))


 

 


class DeleteTaskButton(Button):
    """Delete Button with Trash Icon."""
    
    def __init__(self, task_id, task_name, task_view):
        super().__init__(emoji="🗑", style=discord.ButtonStyle.red)
        self.task_id = task_id
        self.task_name = task_name
        self.task_view = task_view

    async def callback(self, interaction):
        """Deletes a task and updates UI."""
        self.task_view.model.delete_task_by_id(self.task_id)
        await interaction.response.send_message(f"🗑 Task '{self.task_name}' deleted!", ephemeral=True)
        await self.task_view.update_task_display(interaction)
        
         

class EditTaskModal(Modal):
    """Modal to Edit an Existing Task with Name, Description, and Status (as TextInput)."""
    
    def __init__(self, task_id, task_name, task_description, task_status, task_view):
        super().__init__(title="✏ Edit Task")
        self.task_id = task_id
        self.task_view = task_view

        # ✅ Task Name Input
        self.task_name_input = TextInput(label="Task Name", default=task_name)
        
        # ✅ Task Description Input
        self.task_description_input = TextInput(label="Task Description", style=discord.TextStyle.paragraph, default=task_description, required=False)

        # ✅ Status Input (Instead of Dropdown)
        self.task_status_input = TextInput(label="Task Status", default=task_status, required=True)

        # ✅ Add inputs to modal
        self.add_item(self.task_name_input)
        self.add_item(self.task_description_input)
        self.add_item(self.task_status_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles task editing and updates the UI."""
        new_task_name = self.task_name_input.value.strip()
        new_task_description = self.task_description_input.value.strip()
        raw_status  = self.task_status_input.value.strip()  # ✅ Get status as text input
        
        # ✅ Normalize status before saving
        new_status = self.task_view.model.normalize_status(raw_status)  

        if not new_task_name:
            await interaction.response.send_message("⚠ Task name cannot be empty!", ephemeral=True)
            return
        
        # ✅ Update the database with normalized status
        self.task_view.model.update_task(self.task_id, new_task_name, new_task_description, new_status)
        await interaction.response.send_message(f"✅ Task '{new_task_name}' updated with status '{new_status}'!", ephemeral=True)

        # ✅ Refresh task display
        await self.task_view.update_task_display(interaction)

class TaskButtonsView(View):
    """Handles task action buttons with pagination support."""
    
    def __init__(self, tasks, task_view, page=0, tasks_per_page=5):
        super().__init__(timeout=None)
        self.task_view = task_view
        self.tasks = tasks
        self.page = page
        self.tasks_per_page = tasks_per_page

        # Pagination Variables
        self.total_pages = (len(tasks) // tasks_per_page) + (1 if len(tasks) % tasks_per_page > 0 else 0)

        # Show only a subset of tasks based on current page
        start_idx = page * tasks_per_page
        end_idx = start_idx + tasks_per_page
        current_tasks = tasks[start_idx:end_idx]

        for task in current_tasks:
            task_id, content, _, _, _, _ = task
            self.add_item(TaskButton(task_id, content, task_view))

        # Add Pagination Buttons If More Than One Page
        if self.total_pages > 1:
            if self.page > 0:
                prev_button = Button(label="⬅ Previous", style=discord.ButtonStyle.blurple, custom_id="prev_page")
                prev_button.callback = lambda i: self.change_page(i, self.page - 1)
                self.add_item(prev_button)

            if self.page < self.total_pages - 1:
                next_button = Button(label="Next ➡", style=discord.ButtonStyle.blurple, custom_id="next_page")
                next_button.callback = lambda i: self.change_page(i, self.page + 1)
                self.add_item(next_button)

    async def change_page(self, interaction: discord.Interaction, new_page):
        """Handles pagination and updates UI."""
        new_view = TaskButtonsView(self.tasks, self.task_view, page=new_page)
        await interaction.response.edit_message(view=new_view)


class TaskButton(Button):
    """Button that triggers task action options."""

    def __init__(self, task_id, task_name, task_view):
        # Ensure the button label is within Discord's 80-char limit
        max_label_length = 80 - len(f"Task {task_id}: ")  # Reserve space for "Task {id}: "
        
        truncated_name = truncate_text(task_name, max_label_length)  # ✅ Use the utility function

        super().__init__(label=f"Task {task_id}: {truncated_name}", style=discord.ButtonStyle.primary)
        self.task_id = task_id
        self.task_name = task_name  # Store full name for reference
        self.task_view = task_view

    async def callback(self, interaction: discord.Interaction):
        """Handle button clicks."""
        await interaction.response.send_message(
            f"Task Options for: {self.task_name}",  # ✅ Show full task name, not truncated version
            view=TaskActionButtons(self.task_id, self.task_name, self.task_view),
            ephemeral=True  # ✅ Private message to user
        )



class TaskActionButtons(View):
    """Task action buttons for modifying tasks."""
    def __init__(self, task_id, task_name, task_view):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.task_name = task_name
        self.task_view = task_view

    @discord.ui.button(label="✅ Mark Complete", style=discord.ButtonStyle.green)
    async def complete_task(self, interaction: discord.Interaction, button: Button):
        """Mark the task as completed."""
        self.task_view.model.mark_task_complete(self.task_id)
        await interaction.response.send_message(f"✅ Task '{self.task_name}' marked as completed!", ephemeral=True)
        await self.task_view.update_task_display(interaction)

    @discord.ui.button(label="✏️ Edit Task", style=discord.ButtonStyle.blurple)
    async def edit_task(self, interaction: discord.Interaction, button: Button):
        """Open a modal to edit the task name."""
        await interaction.response.send_modal(EditTaskModal(self.task_id, self.task_name, self.task_view))

    @discord.ui.button(label="🗑️ Delete Task", style=discord.ButtonStyle.red)
    async def delete_task(self, interaction: discord.Interaction, button: Button):
        """Delete the task."""
        self.task_view.model.delete_task_by_id(self.task_id)
        await interaction.response.send_message(f"🗑️ Task '{self.task_name}' deleted successfully!", ephemeral=True)
        await self.task_view.update_task_display(interaction)


 
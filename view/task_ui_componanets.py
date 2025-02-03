import discord
from discord.ui import View, Button, Modal, TextInput
from functools import partial


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
    """Modal UI for adding a task."""
    
    def __init__(self, task_view):
        super().__init__(title="📝 Add a New Task")
        self.task_view = task_view
        self.task_name = TextInput(label="Task Name", placeholder="Enter task name...")
        self.task_description = TextInput(label="Task Description", style=discord.TextStyle.paragraph, placeholder="Enter task details...", required=False)
        self.add_item(self.task_name)
        self.add_item(self.task_description)

    async def on_submit(self, interaction: discord.Interaction):
        """Store the task and refresh the task list UI."""
        task_name = self.task_name.value.strip()
        task_details = self.task_details.value.strip()

        if not task_name:
            await interaction.response.send_message("⚠ Task name cannot be empty!", ephemeral=True)
            return

        # Store the task in the database
        self.task_view.model.store_task(task_name, str(interaction.user), interaction.channel.name)

        # Fetch updated tasks
        tasks = self.task_view.model.get_all_tasks()
        
        # Send confirmation + updated task list
        await interaction.response.send_message(
            f"✅ Task '{task_name}' added!", ephemeral=True
        )
        
        # Display updated task list in the channel
        await interaction.channel.send(embed=self.task_view.build_task_embed(tasks)[0], view=TaskListView(tasks, self.task_view))


import discord
from discord.ui import View, Button
from functools import partial

class TaskListView(View):
    """Displays Task List where Task Name is Clickable with Edit & Delete Icons in One Row."""

    def __init__(self, tasks, task_view, page=0, tasks_per_page=3):  # 🔹 Decrease tasks per page
        super().__init__(timeout=None)
        self.task_view = task_view
        self.tasks = tasks
        self.page = page
        self.tasks_per_page = tasks_per_page

        self.total_pages = (len(tasks) // tasks_per_page) + (1 if len(tasks) % tasks_per_page > 0 else 0)

        start_idx = page * tasks_per_page
        end_idx = start_idx + tasks_per_page
        current_tasks = tasks[start_idx:end_idx]

        # ✅ Distribute buttons in rows
        for index, task in enumerate(current_tasks):
            task_id, name, details, author, status, timestamp = task
            truncated_name = name[:50] + "..." if len(name) > 50 else name

            row = index  # ✅ Ensure each task starts in a new row

            # ✅ Clickable Task Name Button
            task_button = Button(label=truncated_name, style=discord.ButtonStyle.primary, custom_id=f"task_{task_id}", row=row)
            task_button.callback = partial(self.show_task_details, task_id, name, details, author, status, timestamp)

            # ✅ Edit & Delete Buttons in the same row
            edit_button = Button(emoji="✍", style=discord.ButtonStyle.blurple, custom_id=f"edit_{task_id}", row=row)
            delete_button = Button(emoji="⛔", style=discord.ButtonStyle.grey, custom_id=f"delete_{task_id}", row=row)

            # ✅ Add buttons in the same row
            self.add_item(task_button)
            self.add_item(edit_button)
            self.add_item(delete_button)

        # ✅ Move Pagination Buttons to the Last Row (Row 3)
        pagination_row = 3  

        if self.total_pages > 1:
            if self.page > 0:
                prev_button = Button(label="⬅", style=discord.ButtonStyle.blurple, custom_id="prev_page", row=pagination_row)
                prev_button.callback = partial(self.change_page, new_page=self.page - 1)
                self.add_item(prev_button)  # ✅ Separate row for pagination

            if self.page < self.total_pages - 1:
                next_button = Button(label="➡", style=discord.ButtonStyle.blurple, custom_id="next_page", row=pagination_row)
                next_button.callback = partial(self.change_page, new_page=self.page + 1)
                self.add_item(next_button)  # ✅ Separate row for pagination

    async def show_task_details(self, interaction, task_id, task_name, task_details, author, status, timestamp):
        """Displays task details in a modal when clicking the task name."""
        await interaction.response.send_modal(TaskDetailsModal(task_id, task_name, task_details, author, status, timestamp))

    async def edit_task(self, interaction, task_id, task_name, task_details):
        """Handles editing a task."""
        await interaction.response.send_modal(EditTaskModal(task_id, task_name, task_details, self.task_view))

    async def delete_task(self, interaction, task_id, task_name):
        """Handles deleting a task."""
        self.task_view.model.delete_task_by_id(task_id)
        await interaction.response.send_message(f"🗑 Task '{task_name}' deleted!", ephemeral=True)
        await self.task_view.update_task_display(interaction)

    async def change_page(self, interaction, new_page):
        """Handles pagination and updates UI."""
        new_view = TaskListView(self.tasks, self.task_view, page=new_page)
        await interaction.response.edit_message(view=new_view)


class TaskDetailsModal(Modal):
    """Modal to Show Task Details."""

    def __init__(self, task_id, task_name, task_details, author, status, timestamp):
        super().__init__(title="📌 Task Details")
        
        self.add_item(TextInput(label="Task Name", default=task_name, disabled=True))
        self.add_item(TextInput(label="Description", default=task_details, style=discord.TextStyle.paragraph, disabled=True))
        self.add_item(TextInput(label="Author", default=author, disabled=True))
        self.add_item(TextInput(label="Status", default=status, disabled=True))
        self.add_item(TextInput(label="Timestamp", default=str(timestamp), disabled=True))

    async def on_submit(self, interaction):
        await interaction.response.defer()




class TaskRow(View):
    """A row containing a Task with Edit & Delete Icons."""
    
    def __init__(self, task_id, task_name, task_details, author, status, timestamp, task_view):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.task_name = task_name
        self.task_details = task_details
        self.author = author
        self.status = status
        self.timestamp = timestamp
        self.task_view = task_view

        self.add_item(Button(label=task_name, style=discord.ButtonStyle.secondary, disabled=True))
        self.add_item(EditTaskButton(task_id, task_name, task_details, task_view))
        self.add_item(DeleteTaskButton(task_id, task_name, task_view))


class TaskDetailsButton(Button):
    """Button that opens task details in a modal when clicked."""
    
    def __init__(self, task_id, task_name, task_description, author, status, timestamp, task_view):
        super().__init__(label=task_name, style=discord.ButtonStyle.secondary)
        self.task_id = task_id
        self.task_name = task_name
        self.task_description = task_description
        self.author = author
        self.status = status
        self.timestamp = timestamp
        self.task_view = task_view

    async def callback(self, interaction: discord.Interaction):
        """Opens a modal with task details."""
        await interaction.response.send_modal(ViewTaskModal(self.task_id, self.task_name, self.task_description, self.author, self.status, self.timestamp))

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


class EditTaskModal(Modal):
    """Modal to Edit an Existing Task."""
    
    def __init__(self, task_id, task_name, task_description, task_view):
        super().__init__(title="✏ Edit Task")
        self.task_id = task_id
        self.task_view = task_view
        self.task_name_input = TextInput(label="Task Name", default=task_name)
        self.task_description_input = TextInput(label="Task Description", style=discord.TextStyle.paragraph, default=task_description, required=False)
        self.add_item(self.task_name_input)
        self.add_item(self.task_description_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles task editing and updates the UI."""
        new_task_name = self.task_name_input.value.strip()
        new_task_description = self.task_description_input.value.strip()

        if not new_task_name:
            await interaction.response.send_message("⚠ Task name cannot be empty!", ephemeral=True)
            return
        
        self.task_view.model.update_task(self.task_id, new_task_name, new_task_description)
        await interaction.response.send_message(f"✏ Task updated to '{new_task_name}'!", ephemeral=True)
        await self.task_view.update_task_display(interaction)


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


class EditTaskModal(Modal):
    """Modal to Edit an Existing Task."""
    
    def __init__(self, task_id, task_name, task_details, task_view):
        super().__init__(title="✏ Edit Task")
        self.task_id = task_id
        self.task_view = task_view
        self.task_name_input = TextInput(label="Task Name", default=task_name)
        self.task_details_input = TextInput(label="Task Details", style=discord.TextStyle.paragraph, default=task_details, required=False)

        self.add_item(self.task_name_input)
        self.add_item(self.task_details_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles task editing and updates UI."""
        new_task_name = self.task_name_input.value.strip()
        new_task_details = self.task_details_input.value.strip()

        if not new_task_name:
            await interaction.response.send_message("⚠ Task name cannot be empty!", ephemeral=True)
            return
        
        self.task_view.model.update_task(self.task_id, new_task_name, new_task_details)
        await interaction.response.send_message(f"✏ Task updated to '{new_task_name}'!", ephemeral=True)
        await self.task_view.update_task_display(interaction)

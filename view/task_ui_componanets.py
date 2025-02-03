import discord
from discord.ui import View, Button, Modal, TextInput


class AddTaskView(View):
    """UI View to Add a New Task."""
    
    def __init__(self, task_view):
        super().__init__(timeout=None)
        self.task_view = task_view
        self.add_item(Button(label="Add Task", style=discord.ButtonStyle.green))

    @discord.ui.button(label="Add Task", style=discord.ButtonStyle.green)
    async def add_task(self, interaction: discord.Interaction, button: Button):
        """Open modal to add a task."""
        await interaction.response.send_modal(AddTaskModal(task_view=self.task_view))


class AddTaskModal(Modal):
    """Modal UI for adding a task."""
    
    def __init__(self, task_view):
        super().__init__(title="Add a New Task")
        self.task_view = task_view
        self.task_name = TextInput(label="Task Name", placeholder="Enter task name...")
        self.add_item(self.task_name)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle task submission and update the UI."""
        task_name = self.task_name.value.strip()
        if not task_name:
            await interaction.response.send_message("Task cannot be empty!", ephemeral=True)
            return
        
        self.task_view.model.store_task(task_name, str(interaction.user), interaction.channel.name)
        await interaction.response.send_message(f"✅ Task '{task_name}' added!", ephemeral=True)
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
        # Truncate task name if it's too long
        max_label_length = 50  # Keeping some space for "Task {id}: "
        truncated_name = (task_name[:max_label_length] + "...") if len(task_name) > max_label_length else task_name
        
        super().__init__(label=f"Task {task_id}: {truncated_name}", style=discord.ButtonStyle.primary)
        self.task_id = task_id
        self.task_name = truncated_name  
        self.task_view = task_view

    async def callback(self, interaction: discord.Interaction):
        """Handle button clicks."""
        await interaction.response.send_message(
            f"Task Options for: {self.task_name}",
            view=TaskActionButtons(self.task_id, self.task_name, self.task_view),
            ephemeral=True
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
    """Modal UI for editing a task."""
    
    def __init__(self, task_id, task_name, task_view):
        super().__init__(title="Edit Task")
        self.task_id = task_id
        self.task_view = task_view
        self.task_name_input = TextInput(label="New Task Name", default=task_name)
        self.add_item(self.task_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle task edit submission."""
        new_task_name = self.task_name_input.value.strip()
        if not new_task_name:
            await interaction.response.send_message("Task name cannot be empty!", ephemeral=True)
            return
        
        self.task_view.model.update_task(self.task_id, new_task_name)
        await interaction.response.send_message(f"✏️ Task updated to '{new_task_name}'!", ephemeral=True)
        await self.task_view.update_task_display(interaction)

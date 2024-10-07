# view/task_ui_components.py
import discord
from discord.ui import View, Button, Modal, TextInput

class AddTaskView(View):
    def __init__(self,task_view):
        super().__init__()
        self.task_view = task_view 
        self.add_item(Button(label="Add Task", style=discord.ButtonStyle.green))

    @discord.ui.button(label="Add Task", style=discord.ButtonStyle.green)
    async def add_task(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddTaskModal(task_view=self.task_view))

class AddTaskModal(Modal):
    def __init__(self, task_view):
        super().__init__(title="Add a New Task")
        self.task_view = task_view  # Pass reference to the main TaskView object
        self.task_name = TextInput(label="Task Name", placeholder="Enter the task name...")
        self.add_item(self.task_name)

    async def on_submit(self, interaction):
        """Handle the form submission and add the task to the database."""
        task_name = self.task_name.value
        self.task_view.model.store_task(task_name, str(interaction.user), interaction.channel.name)
        await interaction.response.send_message(f"Task '{task_name}' added successfully!", ephemeral=True)

        # Automatically update the task display after adding
        await self.update_task_display(interaction)

    async def update_task_display(self, interaction):
        """Update the task display after deletion or completion."""
        tasks = self.task_view.model.get_all_tasks()
        embeds = self.task_view.build_task_embed(tasks)
        
        # Handle empty embeds gracefully
        if not embeds:
            await interaction.response.send_message("No tasks to display.", ephemeral=True)
            return

        # Use only the first embed for editing the main message, if it exists
        if self.task_view.task_display_message:
            # If there are multiple embeds, handle them separately
            await self.task_view.task_display_message.edit(embed=embeds[0])

            # Remove any additional messages beyond the first one
            await self.delete_additional_task_messages(interaction)

            # Send new messages for additional embeds if they exist
            for embed in embeds[1:]:
                msg = await interaction.channel.send(embed=embed)
                self.task_view.additional_task_messages.append(msg)
        else:
            # If no main display message, create a new one
            self.task_view.task_display_message = await interaction.channel.send(embed=embeds[0])

            # Send additional embeds, if any, and store references
            for embed in embeds[1:]:
                msg = await interaction.channel.send(embed=embed)
                self.task_view.additional_task_messages.append(msg)

     


class TaskButtons(View):
    def __init__(self, task_id, task_name, task_view):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.task_name = task_name
        self.task_view = task_view

    @discord.ui.button(label="✅ Mark Complete", style=discord.ButtonStyle.green)
    async def complete_task(self, interaction: discord.Interaction, button: Button):
        """Mark the task as completed."""
        self.task_view.model.mark_task_complete(self.task_id)
        await interaction.response.send_message(f"Task '{self.task_name}' marked as completed!", ephemeral=True)
        await self.update_task_display(interaction)

    @discord.ui.button(label="🗑️ Delete Task", style=discord.ButtonStyle.red)
    async def delete_task(self, interaction: discord.Interaction, button: Button):
        """Delete the task."""
        self.task_view.model.delete_task(self.task_name)
        await interaction.response.send_message(f"Task '{self.task_name}' deleted successfully!", ephemeral=True)
        await self.update_task_display(interaction)

    async def update_task_display(self, interaction):
        """Update the task display after deletion or completion."""
        tasks = self.task_view.model.get_all_tasks()
        embed = self.task_view.build_task_embed(tasks)
        await interaction.message.edit(embed=embed)

            
class TaskViewButtons(View):
    def __init__(self, task_name, task_id, task_view):
        super().__init__(timeout=None)
        self.task_name = task_name
        self.task_id = task_id
        self.task_view = task_view

    @discord.ui.button(label="Delete Task", style=discord.ButtonStyle.red)
    async def delete_task(self, interaction: discord.Interaction, button: Button):
        """Delete the task and update the display."""
        self.task_view.model.delete_task(self.task_name)
        await interaction.response.send_message(f"Task '{self.task_name}' deleted successfully!", ephemeral=True)
        
        # Update the task display after deletion
        tasks = self.task_view.model.get_all_tasks()
        embeds = self.task_view.build_task_embed(tasks)  # Ensure we get the list of embeds

        if embeds:  # Check if the list of embeds is not empty
            # If task_display_message exists, edit it with the first embed
            if self.task_view.task_display_message:
                await self.task_view.task_display_message.edit(embed=embeds[0])  # Update with the first embed
                
                # For additional embeds, send them as new messages
                for embed in embeds[1:]:
                    await interaction.channel.send(embed=embed)
            else:
                # If no existing display message, send a new one with all embeds
                self.task_view.task_display_message = await interaction.channel.send(embed=embeds[0])
                for embed in embeds[1:]:
                    await interaction.channel.send(embed=embed)
        else:
            await interaction.channel.send("No tasks to display.")

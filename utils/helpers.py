import json

import discord

def get_display_name_from_author(author_field, guild):
    try:
        # If author_field is dict (API returns parsed JSON)
        if isinstance(author_field, dict):
            user_id = int(author_field.get("id"))
            name = author_field.get("name", "Unknown")
        else:
            # If author_field is JSON string, parse it
            author_obj = json.loads(author_field)
            user_id = int(author_obj.get("id"))
            name = author_obj.get("name", "Unknown")
    except Exception:
        # If parsing fails, treat as simple name string
        user_id = None
        name = author_field

    member = guild.get_member(user_id) if user_id else discord.utils.get(guild.members, name=name)
    display_name = member.display_name if member else name
    avatar_url = member.display_avatar.url if member else None

    return display_name, avatar_url

import asyncio
import discord
from typing import Optional, Callable, Any

async def ask(
    interaction: discord.Interaction,
    question: str,
    view: Optional[discord.ui.View] = None,
    followup: bool = False
) -> Optional[discord.Message]:
    """Sends a prompt and waits for a message response."""
    send = interaction.followup.send if followup else interaction.response.send_message
    
    if view:
        await send(question, view=view, ephemeral=True)
        return None # With a view, the interaction is handled by the view's callback

    await send(question, ephemeral=True)
    
    try:
        message = await interaction.client.wait_for(
            "message",
            timeout=300.0,  # 5 minutes
            check=lambda m: m.author == interaction.user and m.channel == interaction.channel
        )
        if message.content.lower() == "(exit)":
            await interaction.followup.send("Process cancelled.", ephemeral=True)
            return None
        return message
    except asyncio.TimeoutError:
        await interaction.followup.send("You took too long to respond. Process cancelled.", ephemeral=True)
        return None

async def get_input(
    interaction: discord.Interaction,
    question: str,
    parser: Callable[[discord.Message], Any],
    followup: bool = True
) -> Optional[Any]:
    """Asks a question, waits for a response, and parses it."""
    admin_cog = interaction.client.get_cog('Admin')
    if not admin_cog:
        # This is a safeguard in case the Admin cog isn't loaded.
        await interaction.followup.send("Critical error: Admin module not found. Cancelling process.", ephemeral=True)
        return None

    while True:
        # Security check: Ensure the user still has admin privileges at each step.
        if not await admin_cog.is_admin(interaction.user):
            await interaction.followup.send("Admin permissions lost. Process cancelled.", ephemeral=True)
            return None

        response_msg = await ask(interaction, question, followup=followup)
        if response_msg is None:
            return None
        
        try:
            parsed_value = await parser(response_msg)
            # Delete user's response message to keep channel clean
            try:
                await response_msg.delete()
            except discord.Forbidden:
                pass # Ignore if we can't delete messages
            return parsed_value
        except ValueError as e:
            await interaction.followup.send(f"Invalid input: {e}. Please try again or type `(Exit)` to cancel.", ephemeral=True)

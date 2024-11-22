import discord
from fpdf import FPDF
import os
from discord.ext import commands

async def to_pdf(channel: discord.TextChannel, output_file: str):
    messages = await channel.history(limit=None).flatten()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for message in messages:
        pdf.cell(200, 10, txt=f"{message.author}: {message.content}", ln=True)
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif')):
                attachment_path = f"/tmp/{attachment.filename}"
                await attachment.save(attachment_path)
                pdf.add_page()
                pdf.image(attachment_path, x=10, y=10, w=pdf.w - 20)
                os.remove(attachment_path)

    pdf.output(output_file)

@commands.command(name='create')
async def create_team(ctx, game_name, team_name, team_members):
    guild = ctx.guild
    # Get or create category
    category = discord.utils.get(guild.categories, name=game_name)
    if not category:
        category = await guild.create_category(game_name)
    
    # Create text channel
    channel = await guild.create_text_channel(team_name, category=category)
    
    # Create role
    role = await guild.create_role(name=team_name)
    
    # Assign role to members
    member_names = [name.strip() for name in team_members.split(',')]
    for name in member_names:
        member = discord.utils.get(guild.members, name=name)
        if member:
            await member.add_roles(role)
    
    # Set permissions for the role on the new channel
    await channel.set_permissions(role, read_messages=True, send_messages=True)
    
    # Set permissions on voice channels in the category
    for voice_channel in category.voice_channels:
        await voice_channel.set_permissions(role, connect=True, speak=True)
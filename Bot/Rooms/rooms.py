import discord
from discord import app_commands
from discord.ext import commands
from typing import List, cast
from utils.db import db
from Admin.admin import Admin


class Rooms(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _is_admin(self, interaction: discord.Interaction) -> bool:
        admin_cog = cast(Admin, self.bot.get_cog("Admin"))
        return (
            isinstance(interaction.user, discord.Member)
            and admin_cog is not None
            and await admin_cog.is_admin(interaction.user)
        )

    room = app_commands.Group(name="room", description="Room management commands")

    @room.command(name="add_room", description="(Admin) Add a reservable room.")
    @app_commands.describe(
        name="Room name",
        description="Optional description of the room",
    )
    async def add_room(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str = "",
    ):
        if not await self._is_admin(interaction):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            existing = await db.execute(
                "SELECT room_id FROM rooms WHERE room_name = $1", name
            )
            if existing:
                await interaction.followup.send(f"Room `{name}` already exists.")
                return
            await db.execute(
                "INSERT INTO rooms (room_name, description) VALUES ($1, $2)",
                name,
                description or None,
            )
            await interaction.followup.send(f"Room `{name}` added.")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @room.command(name="add_slot", description="(Admin) Add an available time slot to a room.")
    @app_commands.describe(
        room_name="Name of the room",
        start_time="Start time (YYYY-MM-DD HH:MM)",
        end_time="End time (YYYY-MM-DD HH:MM)",
    )
    async def add_slot(
        self,
        interaction: discord.Interaction,
        room_name: str,
        start_time: str,
        end_time: str,
    ):
        if not await self._is_admin(interaction):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
        except ValueError:
            await interaction.followup.send(
                "Invalid time format. Use `YYYY-MM-DD HH:MM`."
            )
            return

        if end_dt <= start_dt:
            await interaction.followup.send("End time must be after start time.")
            return

        try:
            room = await db.execute(
                "SELECT room_id FROM rooms WHERE room_name = $1", room_name
            )
            if not room:
                await interaction.followup.send(f"Room `{room_name}` not found.")
                return

            room_id = room[0]["room_id"]
            result = await db.execute(
                "INSERT INTO room_slots (room_id, start_time, end_time) VALUES ($1, $2, $3) RETURNING slot_id",
                room_id,
                start_dt,
                end_dt,
            )
            slot_id = result[0]["slot_id"]
            await interaction.followup.send(
                f"Slot `#{slot_id}` added to `{room_name}`: {start_time} — {end_time}"
            )
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @room.command(name="remove_slot", description="(Admin) Remove a time slot (and its reservation if any).")
    @app_commands.describe(slot_id="Slot ID to remove")
    async def remove_slot(self, interaction: discord.Interaction, slot_id: int):
        if not await self._is_admin(interaction):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            slot = await db.execute(
                "SELECT slot_id FROM room_slots WHERE slot_id = $1", slot_id
            )
            if not slot:
                await interaction.followup.send(f"Slot `#{slot_id}` not found.")
                return
            # Cascades to room_reservations automatically
            await db.execute("DELETE FROM room_slots WHERE slot_id = $1", slot_id)
            await interaction.followup.send(f"Slot `#{slot_id}` removed.")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @add_slot.autocomplete("room_name")
    async def room_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        records = await db.execute(
            "SELECT room_name FROM rooms WHERE room_name ILIKE $1 LIMIT 25",
            f"%{current}%",
        )
        return [
            app_commands.Choice(name=r["room_name"], value=r["room_name"])
            for r in records
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Rooms(bot))

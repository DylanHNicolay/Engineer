import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from utils.db import db


class Reservations(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_captain_team(self, user_id: int):
        """Return the active team record for which this user is captain, or None."""
        teams = await db.execute(
            "SELECT team_id, team_nick FROM teams WHERE captain_discord_id = $1 AND archived = FALSE",
            user_id,
        )
        return teams[0] if teams else None

    @app_commands.command(name="reserve", description="Reserve a room slot for your team (captains only).")
    @app_commands.describe(slot_id="Slot ID to reserve")
    async def reserve(self, interaction: discord.Interaction, slot_id: int):
        await interaction.response.defer(ephemeral=True)

        team = await self._get_captain_team(interaction.user.id)
        if team is None:
            await interaction.followup.send(
                "You are not a captain of any active team.", ephemeral=True
            )
            return

        try:
            slot = await db.execute(
                """
                SELECT rs.slot_id, r.room_name, rs.start_time, rs.end_time
                FROM room_slots rs
                JOIN rooms r ON r.room_id = rs.room_id
                WHERE rs.slot_id = $1
                """,
                slot_id,
            )
            if not slot:
                await interaction.followup.send(f"Slot `#{slot_id}` not found.")
                return

            slot = slot[0]

            existing = await db.execute(
                "SELECT reservation_id FROM room_reservations WHERE slot_id = $1", slot_id
            )
            if existing:
                await interaction.followup.send(
                    f"Slot `#{slot_id}` is already reserved."
                )
                return

            await db.execute(
                "INSERT INTO room_reservations (slot_id, team_id) VALUES ($1, $2)",
                slot_id,
                team["team_id"],
            )
            start = slot["start_time"].strftime("%Y-%m-%d %H:%M")
            end = slot["end_time"].strftime("%H:%M")
            await interaction.followup.send(
                f"Reserved `{slot['room_name']}` slot `#{slot_id}` ({start} — {end}) for **{team['team_nick']}**."
            )
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @app_commands.command(name="cancel_reservation", description="Cancel your team's room reservation (captains only).")
    @app_commands.describe(slot_id="Slot ID to cancel")
    async def cancel_reservation(self, interaction: discord.Interaction, slot_id: int):
        await interaction.response.defer(ephemeral=True)

        team = await self._get_captain_team(interaction.user.id)
        if team is None:
            await interaction.followup.send(
                "You are not a captain of any active team.", ephemeral=True
            )
            return

        try:
            reservation = await db.execute(
                "SELECT reservation_id, team_id FROM room_reservations WHERE slot_id = $1",
                slot_id,
            )
            if not reservation:
                await interaction.followup.send(f"No reservation found for slot `#{slot_id}`.")
                return

            if reservation[0]["team_id"] != team["team_id"]:
                await interaction.followup.send(
                    "You can only cancel reservations made by your own team."
                )
                return

            await db.execute(
                "DELETE FROM room_reservations WHERE slot_id = $1", slot_id
            )
            await interaction.followup.send(
                f"Reservation for slot `#{slot_id}` cancelled."
            )
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @app_commands.command(name="list_rooms", description="View all available (unreserved) room slots.")
    @app_commands.describe(room_name="Filter by room name (optional)")
    async def list_rooms(self, interaction: discord.Interaction, room_name: str = ""):
        await interaction.response.defer()

        try:
            if room_name:
                records = await db.execute(
                    """
                    SELECT rs.slot_id, r.room_name, rs.start_time, rs.end_time
                    FROM room_slots rs
                    JOIN rooms r ON r.room_id = rs.room_id
                    LEFT JOIN room_reservations rr ON rr.slot_id = rs.slot_id
                    WHERE rr.slot_id IS NULL AND r.room_name ILIKE $1
                    ORDER BY rs.start_time
                    """,
                    f"%{room_name}%",
                )
            else:
                records = await db.execute(
                    """
                    SELECT rs.slot_id, r.room_name, rs.start_time, rs.end_time
                    FROM room_slots rs
                    JOIN rooms r ON r.room_id = rs.room_id
                    LEFT JOIN room_reservations rr ON rr.slot_id = rs.slot_id
                    WHERE rr.slot_id IS NULL
                    ORDER BY rs.start_time
                    """
                )

            if not records:
                msg = "No available slots"
                msg += f" for `{room_name}`." if room_name else "."
                await interaction.followup.send(msg)
                return

            lines = ["**Available Room Slots**", "```"]
            lines.append(f"{'#':<6} {'Room':<20} {'Start':<18} {'End':<10}")
            lines.append("-" * 56)
            for r in records:
                start = r["start_time"].strftime("%Y-%m-%d %H:%M")
                end = r["end_time"].strftime("%H:%M")
                lines.append(f"{r['slot_id']:<6} {r['room_name']:<20} {start:<18} {end:<10}")
            lines.append("```")

            await interaction.followup.send("\n".join(lines))
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @list_rooms.autocomplete("room_name")
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
    await bot.add_cog(Reservations(bot))

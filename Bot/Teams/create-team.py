import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db import db

EXIT_KEYWORDS = {"exit", "(exit)"}


@dataclass
class TeamCreationData:
    team_nick: Optional[str] = None
    role: Optional[discord.Role] = None
    category: Optional[discord.CategoryChannel] = None
    channel: Optional[discord.TextChannel] = None
    captain: Optional[discord.Member] = None
    starters: List[discord.Member] = field(default_factory=list)
    substitutes: List[discord.Member] = field(default_factory=list)
    year: Optional[int] = None
    semester: Optional[str] = None


class ValidationError(Exception):
    pass


class ConversationCancelled(Exception):
    pass


class TeamCreationError(Exception):
    pass


class SemesterSelect(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.value: Optional[str] = None

    @discord.ui.select(
        placeholder="Choose a semester",
        options=[
            discord.SelectOption(label="Fall"),
            discord.SelectOption(label="Summer"),
            discord.SelectOption(label="Spring"),
        ],
        min_values=1,
        max_values=1,
    )
    async def _select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This selection is not for you.", ephemeral=True)
            return
        self.value = select.values[0]
        await interaction.response.send_message(f"Semester set to {self.value}.", ephemeral=True)
        self.stop()


class create_team(commands.Cog):
    REPLY_TIMEOUT = 180

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="create_team", description="Walk through creating a new team interactively.")
    async def create_team(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        admin_cog = interaction.client.get_cog("Admin")
        if admin_cog is None or not await admin_cog.is_admin(interaction.user):  # type: ignore[attr-defined]
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(
            "Starting team creation. Reply in this channel. Type `(Exit)` at any time to cancel.",
            ephemeral=True,
        )

        try:
            draft = await self._collect_team_data(interaction)
        except ConversationCancelled as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        except Exception as exc:
            await interaction.followup.send(f"An unexpected error occurred while collecting data: {exc}", ephemeral=True)
            return

        try:
            warnings = await self._finalize_team(interaction, draft)
        except TeamCreationError as exc:
            await interaction.followup.send(f"Team creation blocked: {exc}", ephemeral=True)
            return
        except Exception as exc:
            await interaction.followup.send(f"Team creation failed: {exc}", ephemeral=True)
            return

        summary = self._format_summary(draft)
        if warnings:
            warning_lines = "\n".join(f"- {msg}" for msg in warnings)
            summary = f"{summary}\n\nWarnings:\n{warning_lines}"
        await interaction.followup.send(summary, ephemeral=True)

    async def _collect_team_data(self, interaction: discord.Interaction) -> TeamCreationData:
        draft = TeamCreationData()
        draft.team_nick = await self._prompt_team_nick(interaction)
        draft.role = await self._prompt_role(interaction)
        draft.category = await self._prompt_category(interaction)
        draft.channel = await self._prompt_channel(interaction, draft.category)
        draft.captain = await self._prompt_member(interaction, "captain")
        draft.starters = await self._prompt_member_group(interaction, "starter", require_entry=True)
        draft.substitutes = await self._prompt_member_group(interaction, "substitute", require_entry=False)
        draft.starters = self._dedupe_members(draft.starters)
        draft.substitutes = self._dedupe_members(draft.substitutes)
        await self._ensure_captain_assignment(interaction, draft)
        draft.year = await self._prompt_year(interaction)
        draft.semester = await self._prompt_semester(interaction)
        await self._review_answers(interaction, draft)
        return draft

    async def _prompt_team_nick(self, interaction: discord.Interaction) -> Optional[str]:
        def normalize(value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            cleaned = value.strip()
            return cleaned or None

        nick = await self._ask_question(
            interaction,
            "Provide a team nickname (short label players recognize). Type `N/A` to skip.",
            allow_na=True,
        )
        return normalize(nick)

    async def _prompt_role(self, interaction: discord.Interaction) -> discord.Role:
        guild = interaction.guild
        assert guild is not None

        async def parser(content: str, message: discord.Message) -> discord.Role:
            if message.role_mentions:
                role = message.role_mentions[0]
                if await self._confirm(interaction, f"Use existing role {role.mention}? (yes/no)"):
                    return role
                raise ValidationError("Role selection cancelled. Provide another role.")

            role_name = content.strip()
            if not role_name:
                raise ValidationError("Please provide a role name or mention.")

            existing = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
            if existing:
                if await self._confirm(interaction, f"Assign existing role {existing.mention}? (yes/no)"):
                    return existing
                raise ValidationError("Role selection cancelled. Provide another role.")

            if not await self._confirm(interaction, f"No role named `{role_name}` exists. Create it now? (yes/no)"):
                raise ValidationError("Role creation aborted. Provide another role.")

            try:
                return await guild.create_role(name=role_name, reason="Team creation wizard role")
            except discord.Forbidden as exc:
                raise ValidationError(f"Missing permissions to create the `{role_name}` role: {exc}")
            except discord.HTTPException as exc:
                raise ValidationError(f"Discord rejected the role creation: {exc}")

        role = await self._ask_question(
            interaction,
            "Mention the role to use or type a new role name.",
            parser=parser,
        )
        assert isinstance(role, discord.Role)
        return role

    async def _prompt_category(self, interaction: discord.Interaction) -> discord.CategoryChannel:
        guild = interaction.guild
        assert guild is not None

        async def parser(content: str, _: discord.Message) -> discord.CategoryChannel:
            cleaned = content.strip()
            target: Optional[discord.CategoryChannel] = None
            if cleaned.isdigit():
                target = discord.utils.get(guild.categories, id=int(cleaned))
            if target is None:
                target = discord.utils.find(lambda c: c.name.lower() == cleaned.lower(), guild.categories)

            if target:
                if await self._confirm(interaction, f"Use existing category `{target.name}`? (yes/no)"):
                    return target
                raise ValidationError("Category selection cancelled. Provide another category.")

            if not await self._confirm(interaction, f"Create a new category named `{cleaned}`? (yes/no)"):
                raise ValidationError("Category creation aborted. Provide another category.")

            try:
                return await guild.create_category(name=cleaned, reason="Team creation wizard category")
            except discord.Forbidden as exc:
                raise ValidationError(f"Missing permissions to create category `{cleaned}`: {exc}")
            except discord.HTTPException as exc:
                raise ValidationError(f"Discord rejected the category creation: {exc}")

        category = await self._ask_question(
            interaction,
            "Provide the category name or ID to house the team channel.",
            parser=parser,
        )
        assert isinstance(category, discord.CategoryChannel)
        return category

    async def _prompt_channel(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> discord.TextChannel:
        guild = interaction.guild
        assert guild is not None

        async def parser(content: str, message: discord.Message) -> discord.TextChannel:
            if message.channel_mentions:
                channel = message.channel_mentions[0]
                if isinstance(channel, discord.TextChannel):
                    if await self._confirm(interaction, f"Use existing channel {channel.mention}? (yes/no)"):
                        return channel
                    raise ValidationError("Channel selection cancelled. Provide another channel.")
                raise ValidationError("Only text channels are supported. Mention a text channel or provide a name.")

            cleaned = content.strip()
            target: Optional[discord.TextChannel] = None
            if cleaned.isdigit():
                maybe_channel = guild.get_channel(int(cleaned))
                if isinstance(maybe_channel, discord.TextChannel):
                    target = maybe_channel
            if target is None:
                target = discord.utils.find(lambda ch: isinstance(ch, discord.TextChannel) and ch.name.lower() == cleaned.lower(), guild.text_channels)

            if target:
                if await self._confirm(interaction, f"Use existing channel {target.mention}? (yes/no)"):
                    return target
                raise ValidationError("Channel selection cancelled. Provide another channel.")

            if not await self._confirm(interaction, f"Create a new text channel named `{cleaned}`? (yes/no)"):
                raise ValidationError("Channel creation aborted. Provide another channel.")

            try:
                return await guild.create_text_channel(
                    name=cleaned,
                    category=category,
                    reason="Team creation wizard channel",
                )
            except discord.Forbidden as exc:
                raise ValidationError(f"Missing permissions to create channel `{cleaned}`: {exc}")
            except discord.HTTPException as exc:
                raise ValidationError(f"Discord rejected the channel creation: {exc}")

        channel = await self._ask_question(
            interaction,
            "Mention the team channel, supply its ID, or type a new channel name.",
            parser=parser,
        )
        assert isinstance(channel, discord.TextChannel)
        return channel

    async def _prompt_member(self, interaction: discord.Interaction, label: str) -> discord.Member:
        guild = interaction.guild
        assert guild is not None

        async def parser(content: str, message: discord.Message) -> discord.Member:
            member: Optional[discord.Member] = None
            if message.mentions:
                member = message.mentions[0]
            elif content.strip().isdigit():
                member = guild.get_member(int(content.strip()))
                if member is None:
                    try:
                        member = await guild.fetch_member(int(content.strip()))
                    except discord.NotFound:
                        member = None
                    except discord.HTTPException as exc:
                        raise ValidationError(f"Could not fetch member: {exc}")

            if member is None:
                raise ValidationError("Could not resolve that user. Mention them or provide their ID.")

            if await self._confirm(interaction, f"Use {member.mention} as the {label}? (yes/no)"):
                return member
            raise ValidationError("Selection cancelled. Provide another user.")

        member = await self._ask_question(
            interaction,
            f"Mention the {label} or provide their user ID.",
            parser=parser,
        )
        assert isinstance(member, discord.Member)
        return member

    async def _prompt_member_group(
        self,
        interaction: discord.Interaction,
        label: str,
        *,
        require_entry: bool,
    ) -> List[discord.Member]:
        guild = interaction.guild
        assert guild is not None

        async def parser(content: str, message: discord.Message) -> List[discord.Member]:
            entries: List[discord.Member] = []
            seen = set()

            def add_member(member: Optional[discord.Member]):
                if member and member.id not in seen:
                    entries.append(member)
                    seen.add(member.id)

            for member in message.mentions:
                add_member(member)

            tokens = [tok for tok in re.split(r"[\s,]+", content.strip()) if tok]
            for token in tokens:
                if token.isdigit():
                    discord_id = int(token)
                    member = guild.get_member(discord_id)
                    if member is None:
                        try:
                            member = await guild.fetch_member(discord_id)
                        except discord.NotFound:
                            member = None
                        except discord.HTTPException as exc:
                            raise ValidationError(f"Failed to fetch member {discord_id}: {exc}")
                    add_member(member)

            if not entries:
                raise ValidationError("No valid members were provided.")

            names = ", ".join(member.display_name for member in entries)
            if await self._confirm(interaction, f"Use [{names}] as {label}s? (yes/no)"):
                return entries
            raise ValidationError("Selection cancelled. Provide the list again.")

        prompt = (
            f"Mention every {label} or provide a list of IDs separated by spaces/commas."
            + (" Type `N/A` if there are no substitutes." if not require_entry else "")
        )

        result = await self._ask_question(
            interaction,
            prompt,
            allow_na=not require_entry,
            parser=parser,
        )

        if result is None:
            return []

        return result

    async def _prompt_year(self, interaction: discord.Interaction) -> int:
        async def parser(content: str, _: discord.Message) -> int:
            if not content.isdigit():
                raise ValidationError("Please provide a numeric year (e.g., 2025).")
            year = int(content)
            if year < 2000 or year > 2100:
                raise ValidationError("Year must be between 2000 and 2100.")
            return year

        year = await self._ask_question(interaction, "Enter the competition year (e.g., 2025).", parser=parser)
        assert isinstance(year, int)
        return year

    async def _prompt_semester(self, interaction: discord.Interaction) -> str:
        view = SemesterSelect(interaction.user.id)
        message = await interaction.followup.send("Select the semester.", view=view, ephemeral=True)

        exit_task = asyncio.create_task(self._wait_for_exit_signal(interaction))
        view_task = asyncio.create_task(view.wait())
        done, pending = await asyncio.wait({exit_task, view_task}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

        # detach the view regardless of outcome
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass

        if exit_task in done and exit_task.result():
            raise ConversationCancelled("Process cancelled by user.")

        if view.value is None:
            raise ConversationCancelled("Semester selection timed out.")

        return view.value

    async def _review_answers(self, interaction: discord.Interaction, draft: TeamCreationData) -> None:
        field_map = {
            "team_nick": self._prompt_team_nick,
            "role": self._prompt_role,
            "category": self._prompt_category,
            "channel": lambda i: self._prompt_channel(i, draft.category),
            "captain": lambda i: self._prompt_member(i, "captain"),
            "starters": lambda i: self._prompt_member_group(i, "starter", require_entry=True),
            "substitutes": lambda i: self._prompt_member_group(i, "substitute", require_entry=False),
            "year": self._prompt_year,
            "semester": self._prompt_semester,
        }

        while True:
            summary = self._format_summary(draft)
            instructions = (
                "Type the field name to edit (team_nick, role, category, channel, captain, starters, substitutes, year, semester)"
                " or `confirm` to continue."
            )
            await interaction.followup.send(f"{summary}\n\n{instructions}", ephemeral=True)

            message = await self._wait_for_reply(interaction)
            content = message.content.strip()
            if self._should_exit(content):
                raise ConversationCancelled("Process cancelled by user.")

            if content.lower() == "confirm":
                return

            handler = field_map.get(content.lower())
            if handler is None:
                await interaction.followup.send("Unknown field. Please try again.", ephemeral=True)
                continue

            result = await handler(interaction)
            if content.lower() == "team_nick":
                draft.team_nick = result
            elif content.lower() == "role":
                draft.role = result
            elif content.lower() == "category":
                draft.category = result
            elif content.lower() == "channel":
                draft.channel = result
            elif content.lower() == "captain":
                draft.captain = result
            elif content.lower() == "starters":
                draft.starters = result
            elif content.lower() == "substitutes":
                draft.substitutes = result
            elif content.lower() == "year":
                draft.year = result
            elif content.lower() == "semester":
                draft.semester = result

    async def _finalize_team(self, interaction: discord.Interaction, draft: TeamCreationData) -> List[str]:
        assert draft.role and draft.channel and draft.category and draft.captain and draft.year and draft.semester
        warnings: List[str] = []

        conflict = await db.execute(
            """
            SELECT team_id
            FROM teams
            WHERE role_id = $1 AND category_id = $2 AND channel_id = $3 AND archived IS NOT TRUE
            """,
            draft.role.id,
            draft.category.id,
            draft.channel.id,
        )
        if conflict:
            raise TeamCreationError(
                "Another active team already uses this role, category, and channel. Archive it before creating a new one."
            )

        team_rows = await db.execute(
            """
            INSERT INTO teams (team_nick, role_id, channel_id, category_id, captain_discord_id, year, semester)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING team_id
            """,
            draft.team_nick,
            draft.role.id,
            draft.channel.id,
            draft.category.id,
            draft.captain.id,
            draft.year,
            draft.semester,
        )
        if not team_rows:
            raise TeamCreationError("Failed to insert the team record.")
        team_id = team_rows[0]["team_id"]

        async def upsert_player(discord_id: int) -> None:
            await db.execute(
                "INSERT INTO players (player_discord_id) VALUES ($1) ON CONFLICT (player_discord_id) DO NOTHING",
                discord_id,
            )

        async def upsert_member(discord_id: int, status: str) -> None:
            await db.execute(
                """
                INSERT INTO team_members (team_id, player_discord_id, member_status)
                VALUES ($1, $2, $3)
                ON CONFLICT (team_id, player_discord_id)
                DO UPDATE SET member_status = EXCLUDED.member_status
                """,
                team_id,
                discord_id,
                status,
            )

        for member in draft.starters + draft.substitutes:
            await upsert_player(member.id)

        await upsert_player(draft.captain.id)

        for member in draft.starters:
            await upsert_member(member.id, "starter")
        for member in draft.substitutes:
            await upsert_member(member.id, "sub")

        # Assign the team role to everyone involved.
        involved_members = {draft.captain, *draft.starters, *draft.substitutes}
        for member in involved_members:
            if member is None:
                continue
            try:
                await member.add_roles(draft.role, reason="Team creation assignment")
            except discord.Forbidden:
                warnings.append(f"Missing permission to assign role to {member.display_name}.")
            except discord.HTTPException as exc:
                warnings.append(f"Failed to assign role to {member.display_name}: {exc}")

        return warnings

    async def _ask_question(
        self,
        interaction: discord.Interaction,
        prompt: str,
        *,
        allow_na: bool = False,
        parser: Optional[Callable[[str, discord.Message], Awaitable[Any]]] = None,
    ):
        await interaction.followup.send(prompt, ephemeral=True)
        while True:
            message = await self._wait_for_reply(interaction)
            content = message.content.strip()
            if self._should_exit(content):
                raise ConversationCancelled("Process cancelled by user.")
            if allow_na and content.lower() in {"n/a", "na"}:
                return None
            if parser is None:
                if content:
                    return content
                await interaction.followup.send("Please provide a response or type N/A.", ephemeral=True)
                continue
            try:
                return await parser(content, message)
            except ValidationError as exc:
                await interaction.followup.send(str(exc), ephemeral=True)

    async def _confirm(self, interaction: discord.Interaction, prompt: str) -> bool:
        await interaction.followup.send(prompt, ephemeral=True)
        while True:
            message = await self._wait_for_reply(interaction)
            content = message.content.strip().lower()
            if self._should_exit(content):
                raise ConversationCancelled("Process cancelled by user.")
            if content in {"yes", "y"}:
                return True
            if content in {"no", "n"}:
                return False
            await interaction.followup.send("Reply with yes or no (or type `(Exit)` to cancel).", ephemeral=True)

    async def _wait_for_reply(self, interaction: discord.Interaction) -> discord.Message:
        def check(message: discord.Message) -> bool:
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel_id

        try:
            return await self.bot.wait_for("message", timeout=self.REPLY_TIMEOUT, check=check)
        except asyncio.TimeoutError:
            raise ConversationCancelled("Timed out waiting for a response.")

    async def _wait_for_exit_signal(self, interaction: discord.Interaction) -> bool:
        def check(message: discord.Message) -> bool:
            return (
                message.author.id == interaction.user.id
                and message.channel.id == interaction.channel_id
                and self._should_exit(message.content)
            )

        try:
            await self.bot.wait_for("message", timeout=self.REPLY_TIMEOUT, check=check)
            return True
        except asyncio.TimeoutError:
            return False

    def _should_exit(self, content: str) -> bool:
        return content.strip().lower() in EXIT_KEYWORDS

    def _format_summary(self, draft: TeamCreationData) -> str:
        starters = ", ".join(member.display_name for member in draft.starters) or "None"
        substitutes = ", ".join(member.display_name for member in draft.substitutes) or "None"
        return (
            "**Team Creation Summary**\n"
            f"- Team Nick: {draft.team_nick or 'N/A'}\n"
            f"- Role: {draft.role.mention if draft.role else 'Not set'}\n"
            f"- Category: {draft.category.name if draft.category else 'Not set'}\n"
            f"- Channel: {draft.channel.mention if draft.channel else 'Not set'}\n"
            f"- Captain: {draft.captain.mention if draft.captain else 'Not set'}\n"
            f"- Starters: {starters}\n"
            f"- Substitutes: {substitutes}\n"
            f"- Year: {draft.year or 'Not set'}\n"
            f"- Semester: {draft.semester or 'Not set'}"
        )

    def _dedupe_members(self, members: Iterable[discord.Member]) -> List[discord.Member]:
        seen = set()
        unique: List[discord.Member] = []
        for member in members:
            if member.id in seen:
                continue
            seen.add(member.id)
            unique.append(member)
        return unique

    async def _ensure_captain_assignment(self, interaction: discord.Interaction, draft: TeamCreationData) -> None:
        if draft.captain is None:
            return
        captain_id = draft.captain.id
        if any(member.id == captain_id for member in draft.substitutes):
            return
        if any(member.id == captain_id for member in draft.starters):
            return
        draft.starters.append(draft.captain)
        await interaction.followup.send(
            f"{draft.captain.display_name} is the captain and has been added to starters by default."
            " Use the review step if they should be a substitute instead.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(create_team(bot))

import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import random
from typing import List, Optional

# Helper function to check if user has manager role or is admin
async def check_tryout_manager_perms(interaction: discord.Interaction) -> bool:
    """Checks if the user is an admin or has the defined tryout manager role."""
    if interaction.user.guild_permissions.administrator:
        return True
    guild_data = await interaction.client.db_interface.fetchrow("SELECT tryout_manager_role_id FROM guilds WHERE guild_id = $1", interaction.guild_id)
    if guild_data and guild_data['tryout_manager_role_id']:
        manager_role_id = guild_data['tryout_manager_role_id']
        if discord.utils.get(interaction.user.roles, id=manager_role_id):
            return True
    await interaction.response.send_message("You do not have permission to manage tryouts.", ephemeral=True)
    return False

# Helper function to check if user is a student
async def check_is_student(interaction: discord.Interaction) -> bool:
    """Checks if the user has the student role defined for the guild."""
    guild_data = await interaction.client.db_interface.fetchrow("SELECT student_role_id FROM guilds WHERE guild_id = $1", interaction.guild_id)
    if guild_data and guild_data['student_role_id']:
        student_role_id = guild_data['student_role_id']
        if discord.utils.get(interaction.user.roles, id=student_role_id):
            return True
    await interaction.response.send_message("This command can only be used by verified students.", ephemeral=True)
    return False

class Team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @app_commands.command(name="tryouts_define_role", description="Define the role allowed to manage tryouts.")
    @app_commands.describe(role="The role that can manage tryouts.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tryouts_define_role(self, interaction: discord.Interaction, role: discord.Role):
        """Admins: Define the role that can manage tryouts."""
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.db_interface.execute(
                "UPDATE guilds SET tryout_manager_role_id = $1 WHERE guild_id = $2",
                role.id, interaction.guild_id
            )
            await interaction.followup.send(f"Successfully set {role.mention} as the tryout manager role.")
        except Exception as e:
            self.logger.error(f"Error setting tryout manager role for guild {interaction.guild_id}: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="tryouts_create", description="Create a new tryout process for a game category.")
    @app_commands.describe(
        video_game_category="The category where tryout channels will be created.",
        role_name="The name of the role to create for tryout participants.",
        team_size="The number of players per team (e.g., 5 for Overwatch).",
        google_form_link="Link to the Google Form for sign-ups."
    )
    @app_commands.check(check_tryout_manager_perms)
    async def tryouts_create(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel, role_name: str, team_size: app_commands.Range[int, 1, None], google_form_link: str):
        """Managers: Create a new tryout configuration."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Extract Google Form ID
        form_id = None
        match = re.search(r'/forms/d/e/([a-zA-Z0-9_-]+)/viewform', google_form_link)
        if not match:
            match = re.search(r'/forms/d/([a-zA-Z0-9_-]+)/edit', google_form_link)
        if match:
            form_id = match.group(1)
        else:
            # Basic check if it's just the ID
             if re.match(r'^[a-zA-Z0-9_-]+$', google_form_link):
                 form_id = google_form_link
             else:
                await interaction.followup.send("Could not extract a valid Google Form ID from the link. Please provide a standard Google Form link or just the Form ID.", ephemeral=True)
                return

        # TODO: Test the form ID using Google Forms API (requires setup and credentials)
        # If the form ID leads to an error, display the error in the same channel in which the command was executed.
        # If it is because there is no API access for the form ID, give specific instructions on how to enable it.
        # Example:
        # try:
        #     # Hypothetical function to check form access
        #     is_accessible = await check_google_form_access(form_id)
        #     if not is_accessible:
        #          await interaction.channel.send(f"Warning: Could not access Google Form ({form_id}). Ensure API access is enabled and the form is shared correctly.")
        # except GoogleFormNotFoundError:
        #     await interaction.channel.send(f"Error: Google Form with ID '{form_id}' not found.")
        #     return
        # except GoogleAPIAccessError:
        #      await interaction.channel.send(f"Error: API access denied for Google Form '{form_id}'. Please ensure the Google Forms API is enabled for your project and appropriate permissions are granted.")
        #      return
        # except Exception as form_error:
        #      await interaction.channel.send(f"An unexpected error occurred while checking the Google Form: {form_error}")
        #      # Decide if you want to proceed or stop
        self.logger.warning(f"TODO: Implement Google Form ID validation for {form_id}")


        # Check if role already exists
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            role_to_use = existing_role
            await interaction.followup.send(f"Using existing role: {role_to_use.mention}", ephemeral=True)
        else:
            # Create the role
            try:
                role_to_use = await guild.create_role(name=role_name, reason=f"Tryout role for {video_game_category.name}")
                await interaction.followup.send(f"Created tryout role: {role_to_use.mention}", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to create roles.", ephemeral=True)
                return
            except Exception as e:
                self.logger.error(f"Failed to create role '{role_name}' in guild {guild.id}: {e}")
                await interaction.followup.send(f"Failed to create role: {e}", ephemeral=True)
                return

        # Store tryout configuration in the database
        try:
            await self.bot.db_interface.execute(
                """
                INSERT INTO tryouts (guild_id, category_id, category_name, role_id, role_name, team_size, google_form_link, google_form_id, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
                ON CONFLICT (guild_id, category_id) DO UPDATE SET
                    role_id = EXCLUDED.role_id,
                    role_name = EXCLUDED.role_name,
                    team_size = EXCLUDED.team_size,
                    google_form_link = EXCLUDED.google_form_link,
                    google_form_id = EXCLUDED.google_form_id,
                    is_active = TRUE
                """,
                guild.id, video_game_category.id, video_game_category.name, role_to_use.id, role_to_use.name,
                team_size, google_form_link, form_id
            )
            await interaction.followup.send(f"Tryouts created/updated for category '{video_game_category.name}' with role {role_to_use.mention}, team size {team_size}, and form ID '{form_id}'.")
        except Exception as e:
            self.logger.error(f"Failed to save tryout config for guild {guild.id}, category {video_game_category.id}: {e}")
            await interaction.followup.send(f"Database error: {e}", ephemeral=True)


    @app_commands.command(name="tryouts_join", description="Join the tryouts for a specific game category.")
    @app_commands.describe(video_game_category="The category for the game you want to try out for.")
    @app_commands.check(check_is_student)
    async def tryouts_join(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel):
        """Students: Join the tryouts for a game."""
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        db = self.bot.db_interface

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT * FROM tryouts WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            guild.id, video_game_category.id
        )

        if not tryout_config:
            await interaction.followup.send(f"No active tryouts found for the category '{video_game_category.name}'.", ephemeral=True)
            return

        tryout_id = tryout_config['tryout_id']
        role_id = tryout_config['role_id']
        form_link = tryout_config['google_form_link']
        form_id = tryout_config['google_form_id']
        tryout_role = guild.get_role(role_id)

        if not tryout_role:
            await interaction.followup.send("The tryout role for this category seems to be missing. Please contact a manager.", ephemeral=True)
            return

        # Check if user already has the role or is registered
        if tryout_role in user.roles:
             await interaction.followup.send("You are already part of these tryouts.", ephemeral=True)
             return

        existing_participant = await db.fetchrow(
            "SELECT participant_id FROM tryout_participants WHERE tryout_id = $1 AND discord_id = $2",
            tryout_id, user.id
        )
        if existing_participant:
             await interaction.followup.send("You are already registered for these tryouts.", ephemeral=True)
             # Ensure role is assigned just in case
             if tryout_role not in user.roles:
                 try:
                     await user.add_roles(tryout_role, reason="Re-syncing tryout join")
                 except Exception as e:
                     self.logger.warning(f"Failed to re-assign tryout role {tryout_role.id} to user {user.id}: {e}")
             return

        # TODO: Check if the user has submitted the Google Form.
        # Requires Google Forms API access.
        # 1. Use the form_id to access the form responses.
        # 2. Look for a column named "Discord Username" (or similar).
        # 3. Check if interaction.user.name or interaction.user.display_name exists in that column.
        # Example:
        # try:
        #     form_responses = await get_google_form_responses(form_id)
        #     discord_username_column = find_column(form_responses, "Discord Username") # Find the relevant column index/header
        #     user_submitted = False
        #     for response in form_responses:
        #         if response[discord_username_column] == user.name or response[discord_username_column] == user.display_name: # Adjust matching logic as needed
        #             user_submitted = True
        #             # TODO: Extract seeding information from the form response here
        #             # seeding_data = extract_seeding(response)
        #             break
        # except Exception as form_error:
        #      self.logger.error(f"Error checking Google Form {form_id} for user {user.id}: {form_error}")
        #      await interaction.followup.send("Could not verify form submission due to an error. Please try again later or contact a manager.", ephemeral=True)
        #      return
        user_submitted = True # Placeholder - REMOVE THIS LINE WHEN FORM CHECK IS IMPLEMENTED
        seeding_data = None # Placeholder

        if user_submitted:
            # Add participant to database
            try:
                await db.execute(
                    """
                    INSERT INTO tryout_participants (tryout_id, discord_id)
                    VALUES ($1, $2)
                    ON CONFLICT (tryout_id, discord_id) DO NOTHING
                    """,
                    tryout_id, user.id
                    # TODO: Add seeding data to the insert/update query when available
                )

                # Grant the role
                await user.add_roles(tryout_role, reason=f"Joined {video_game_category.name} tryouts")
                await interaction.followup.send(f"You have successfully joined the tryouts for '{video_game_category.name}' and received the {tryout_role.mention} role!", ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to assign roles.", ephemeral=True)
            except Exception as e:
                self.logger.error(f"Failed to add participant or role for user {user.id}, tryout {tryout_id}: {e}")
                await interaction.followup.send(f"An error occurred while joining: {e}", ephemeral=True)
        else:
            # User hasn't completed the form
            try:
                await user.send(f"Please complete the sign-up form before joining the tryouts for '{video_game_category.name}':\n{form_link}")
                await interaction.followup.send("You need to complete the sign-up form first. I've sent you a link in DMs.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(f"You need to complete the sign-up form first: {form_link}\n(I couldn't DM you the link, please enable DMs).", ephemeral=True)
            except Exception as e:
                 await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


    @app_commands.command(name="tryouts_begin", description="Create channels for the tryout process.")
    @app_commands.describe(video_game_category="The category where tryouts are configured.")
    @app_commands.check(check_tryout_manager_perms)
    async def tryouts_begin(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel):
        """Managers: Create the necessary text and voice channels for tryouts."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        db = self.bot.db_interface

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT * FROM tryouts WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            guild.id, video_game_category.id
        )
        if not tryout_config:
            await interaction.followup.send(f"No active tryouts found for the category '{video_game_category.name}'.", ephemeral=True)
            return

        role_id = tryout_config['role_id']
        team_size = tryout_config['team_size']
        tryout_role = guild.get_role(role_id)
        if not tryout_role:
            await interaction.followup.send("The tryout role for this category is missing. Cannot begin.", ephemeral=True)
            return

        # Permissions for the new channels (only tryout role and bot)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_permissions=True, connect=True, speak=True, move_members=True),
            tryout_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True) # Basic perms for participants
        }

        created_channels = []
        try:
            # Create #tryouts text channel
            tc_name = "tryouts"
            existing_tc = discord.utils.get(video_game_category.text_channels, name=tc_name)
            if not existing_tc:
                tc = await video_game_category.create_text_channel(name=tc_name, overwrites=overwrites, reason="Tryout setup")
                created_channels.append(tc.mention)
            else:
                 await existing_tc.edit(overwrites=overwrites, reason="Updating tryout channel permissions") # Ensure perms are correct
                 created_channels.append(existing_tc.mention + " (updated)")


            # Create Lobby voice channel
            lobby_vc_name = "Lobby"
            existing_lobby_vc = discord.utils.get(video_game_category.voice_channels, name=lobby_vc_name)
            if not existing_lobby_vc:
                lobby_vc = await video_game_category.create_voice_channel(name=lobby_vc_name, overwrites=overwrites, reason="Tryout setup")
                created_channels.append(lobby_vc.mention)
            else:
                 await existing_lobby_vc.edit(overwrites=overwrites, reason="Updating tryout channel permissions")
                 created_channels.append(existing_lobby_vc.mention + " (updated)")


            # Get number of participants
            participants = await db.fetch(
                "SELECT discord_id FROM tryout_participants WHERE tryout_id = $1",
                tryout_config['tryout_id']
            )
            num_participants = len(participants)

            # Calculate number of voice channels needed (2 teams per channel pair)
            num_voice_channels = (num_participants // (team_size * 2)) * 2 # Ensure even number, round down pairs

            if num_voice_channels <= 0 and num_participants > 0:
                 num_voice_channels = 2 # Create at least 2 if there are any participants

            # Create Tryouts X voice channels
            for i in range(1, num_voice_channels + 1):
                vc_name = f"Tryouts {i}"
                existing_vc = discord.utils.get(video_game_category.voice_channels, name=vc_name)
                if not existing_vc:
                    vc = await video_game_category.create_voice_channel(name=vc_name, overwrites=overwrites, reason="Tryout setup")
                    created_channels.append(vc.mention)
                else:
                    await existing_vc.edit(overwrites=overwrites, reason="Updating tryout channel permissions")
                    created_channels.append(vc_name + " (updated)")


            await interaction.followup.send(f"Tryout channels created/updated in '{video_game_category.name}':\n" + "\n".join(created_channels))

        except discord.Forbidden:
            await interaction.followup.send("I lack permissions to create/manage channels in that category.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error creating tryout channels for guild {guild.id}, category {video_game_category.id}: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


    @app_commands.command(name="tryouts_matchmake", description="Matchmake players for a tryout game.")
    @app_commands.describe(video_game_category="The category where tryouts are happening.")
    @app_commands.check(check_tryout_manager_perms)
    async def tryouts_matchmake(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel):
        """Managers: Initiate matchmaking for the current players in the Lobby."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        db = self.bot.db_interface

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT * FROM tryouts WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            guild.id, video_game_category.id
        )
        if not tryout_config:
            await interaction.followup.send(f"No active tryouts found for the category '{video_game_category.name}'.", ephemeral=True)
            return

        team_size = tryout_config['team_size']
        tryout_id = tryout_config['tryout_id']

        # Find Lobby and Tryout VCs
        lobby_vc = discord.utils.get(video_game_category.voice_channels, name="Lobby")
        tryout_vcs = sorted(
            [vc for vc in video_game_category.voice_channels if vc.name.startswith("Tryouts ")],
            key=lambda vc: int(vc.name.split(" ")[-1])
        )

        if not lobby_vc:
            await interaction.followup.send("Lobby voice channel not found.", ephemeral=True)
            return
        if not tryout_vcs or len(tryout_vcs) < 2:
             await interaction.followup.send("Not enough 'Tryouts X' voice channels found.", ephemeral=True)
             return

        # Get players in Lobby
        players_in_lobby = lobby_vc.members
        if len(players_in_lobby) < team_size * 2:
            await interaction.followup.send(f"Not enough players in the Lobby channel ({len(players_in_lobby)}/{team_size*2}).", ephemeral=True)
            return

        # Get participant data (for seeding/winrate later)
        player_ids = [p.id for p in players_in_lobby]
        participants_data = await db.fetch(
             f"SELECT discord_id, wins, losses FROM tryout_participants WHERE tryout_id = $1 AND discord_id = ANY($2::bigint[])",
             tryout_id, player_ids
        )
        # Create a map for easy lookup
        participant_stats = {p['discord_id']: p for p in participants_data}

        # TODO: Implement matchmaking based on seeding/winrate.
        # For now, just shuffle randomly.
        # 1. Fetch seeding/winrate data from tryout_participants table.
        # 2. Sort players based on the chosen metric.
        # 3. Create balanced teams (e.g., snake draft, ELO-based).
        random.shuffle(players_in_lobby)
        self.logger.warning(f"TODO: Implement proper matchmaking for tryout {tryout_id}. Using random shuffle.")

        # Find two unoccupied tryout VCs
        target_vc1 = None
        target_vc2 = None
        for i in range(0, len(tryout_vcs), 2):
            vc1 = tryout_vcs[i]
            vc2 = tryout_vcs[i+1] if (i+1) < len(tryout_vcs) else None
            if vc2 and not vc1.members and not vc2.members: # Check if both are empty
                 target_vc1 = vc1
                 target_vc2 = vc2
                 break

        if not target_vc1 or not target_vc2:
             await interaction.followup.send("Could not find a pair of unoccupied 'Tryouts X' voice channels.", ephemeral=True)
             return

        # Divide players into two teams
        team1_players = players_in_lobby[:team_size]
        team2_players = players_in_lobby[team_size:team_size*2]

        # Move players
        moved_count = 0
        errors = []
        try:
            self.logger.info(f"Moving Team 1 ({[p.name for p in team1_players]}) to {target_vc1.name}")
            for player in team1_players:
                try:
                    await player.move_to(target_vc1, reason="Tryout matchmaking")
                    moved_count += 1
                except Exception as move_error:
                    errors.append(f"Failed to move {player.name}: {move_error}")

            self.logger.info(f"Moving Team 2 ({[p.name for p in team2_players]}) to {target_vc2.name}")
            for player in team2_players:
                try:
                    await player.move_to(target_vc2, reason="Tryout matchmaking")
                    moved_count += 1
                except Exception as move_error:
                    errors.append(f"Failed to move {player.name}: {move_error}")

            result_message = f"Matchmaking complete! Moved {moved_count} players.\nTeam 1 ({target_vc1.name}): {', '.join([p.mention for p in team1_players])}\nTeam 2 ({target_vc2.name}): {', '.join([p.mention for p in team2_players])}"
            if errors:
                result_message += "\nErrors:\n" + "\n".join(errors)
            await interaction.followup.send(result_message)

            # Optionally send message to #tryouts channel
            tryouts_tc = discord.utils.get(video_game_category.text_channels, name="tryouts")
            if tryouts_tc:
                 await tryouts_tc.send(f"New match started!\n{target_vc1.mention}: {', '.join([p.mention for p in team1_players])}\n{target_vc2.mention}: {', '.join([p.mention for p in team2_players])}")

        except discord.Forbidden:
            await interaction.followup.send("I lack permissions to move members.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error during matchmaking/moving players for guild {guild.id}: {e}")
            await interaction.followup.send(f"An error occurred during matchmaking: {e}", ephemeral=True)


    @app_commands.command(name="match_complete", description="Record the results of a completed tryout match.")
    @app_commands.describe(
        video_game_category="The category where the match took place.",
        winning_vc="The voice channel of the winning team.",
        losing_vc="The voice channel of the losing team."
        # TODO: Add parameters for specifying player lists instead of VCs
    )
    @app_commands.check(check_tryout_manager_perms)
    async def match_complete(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel, winning_vc: discord.VoiceChannel, losing_vc: discord.VoiceChannel):
        """Managers: Record the results of a match based on players in VCs."""
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db_interface

        # Basic validation
        if winning_vc.category != video_game_category or losing_vc.category != video_game_category:
            await interaction.followup.send("Winning and losing VCs must be within the specified category.", ephemeral=True)
            return
        if winning_vc == losing_vc:
             await interaction.followup.send("Winning and losing VCs cannot be the same.", ephemeral=True)
             return

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT tryout_id FROM tryouts WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            interaction.guild_id, video_game_category.id
        )
        if not tryout_config:
            await interaction.followup.send(f"No active tryouts found for the category '{video_game_category.name}'.", ephemeral=True)
            return
        tryout_id = tryout_config['tryout_id']

        winners = winning_vc.members
        losers = losing_vc.members
        winner_ids = [p.id for p in winners]
        loser_ids = [p.id for p in losers]

        if not winners or not losers:
             await interaction.followup.send("One or both specified voice channels are empty.", ephemeral=True)
             return

        # Update stats in database
        try:
            async with db.pool.acquire() as conn:
                 async with conn.transaction():
                    # Increment wins for winners
                    await conn.execute(
                        f"UPDATE tryout_participants SET wins = wins + 1 WHERE tryout_id = $1 AND discord_id = ANY($2::bigint[])",
                        tryout_id, winner_ids
                    )
                    # Increment losses for losers
                    await conn.execute(
                        f"UPDATE tryout_participants SET losses = losses + 1 WHERE tryout_id = $1 AND discord_id = ANY($2::bigint[])",
                        tryout_id, loser_ids
                    )
                    # Log the match (optional)
                    await conn.execute(
                         """
                         INSERT INTO tryout_matches (tryout_id, winning_team_discord_ids, losing_team_discord_ids)
                         VALUES ($1, $2, $3)
                         """,
                         tryout_id, winner_ids, loser_ids
                    )
            await interaction.followup.send(f"Match result recorded: {winning_vc.name} (Win) vs {losing_vc.name} (Loss). Stats updated.")

            # Optionally move players back to Lobby
            lobby_vc = discord.utils.get(video_game_category.voice_channels, name="Lobby")
            if lobby_vc:
                 for player in winners + losers:
                     try:
                         await player.move_to(lobby_vc, reason="Match complete")
                     except Exception: pass # Ignore errors moving back

        except Exception as e:
            self.logger.error(f"Failed to record match results for tryout {tryout_id}: {e}")
            await interaction.followup.send(f"Database error while recording match: {e}", ephemeral=True)


    @app_commands.command(name="winrate_list", description="Display win rates for tryout participants.")
    @app_commands.describe(video_game_category="The category for the tryouts.")
    async def winrate_list(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel):
        """View the win rates of participants in a tryout."""
        await interaction.response.defer()
        db = self.bot.db_interface
        guild = interaction.guild

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT tryout_id FROM tryouts WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            guild.id, video_game_category.id
        )
        if not tryout_config:
            await interaction.followup.send(f"No active tryouts found for the category '{video_game_category.name}'.")
            return
        tryout_id = tryout_config['tryout_id']

        participants = await db.fetch(
            "SELECT discord_id, wins, losses FROM tryout_participants WHERE tryout_id = $1 ORDER BY (wins::float / GREATEST(wins + losses, 1)) DESC, wins DESC",
            tryout_id
        )

        if not participants:
            await interaction.followup.send("No participants found for these tryouts.")
            return

        embed = discord.Embed(title=f"Tryout Win Rates - {video_game_category.name}", color=discord.Color.blue())
        description = ""
        for i, p in enumerate(participants):
            member = guild.get_member(p['discord_id'])
            name = member.display_name if member else f"ID: {p['discord_id']}"
            wins = p['wins']
            losses = p['losses']
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            description += f"{i+1}. {name}: {wins}W - {losses}L ({win_rate:.1f}%)\n"
            if len(description) > 3800: # Keep embed description under limit
                 description += "\n*List truncated...*"
                 break

        embed.description = description
        await interaction.followup.send(embed=embed)


    @app_commands.command(name="team_add", description="Add selected players to a final team role.")
    @app_commands.describe(
        role="The final team role to assign.",
        player1="Player 1 to add.", player2="Player 2", player3="Player 3", player4="Player 4", player5="Player 5",
        player6="Player 6 (Optional)", player7="Player 7 (Optional)", player8="Player 8 (Optional)" # Add more if needed
    )
    @app_commands.check(check_tryout_manager_perms)
    async def team_add(self, interaction: discord.Interaction, role: discord.Role,
                       player1: discord.Member, player2: discord.Member, player3: discord.Member,
                       player4: discord.Member, player5: discord.Member,
                       player6: Optional[discord.Member] = None, player7: Optional[discord.Member] = None, player8: Optional[discord.Member] = None):
        """Managers: Assign a list of players to a specific team role."""
        await interaction.response.defer(ephemeral=True)
        players_to_add = [p for p in [player1, player2, player3, player4, player5, player6, player7, player8] if p is not None]

        added_players = []
        errors = []
        for player in players_to_add:
            try:
                if role not in player.roles:
                    await player.add_roles(role, reason=f"Added to team {role.name}")
                    added_players.append(player.mention)
            except discord.Forbidden:
                errors.append(f"Cannot assign role to {player.mention} (Permissions missing).")
            except Exception as e:
                 errors.append(f"Error adding role to {player.mention}: {e}")

        response = f"Assigned {role.mention} to: {', '.join(added_players) if added_players else 'No one (check errors/already assigned)'}."
        if errors:
            response += "\nErrors:\n" + "\n".join(errors)
        await interaction.followup.send(response)


    @app_commands.command(name="team_reset", description="Remove the tryout-specific role from all participants in a category.")
    @app_commands.describe(video_game_category="The category whose tryout roles should be reset.")
    @app_commands.check(check_tryout_manager_perms)
    async def team_reset(self, interaction: discord.Interaction, video_game_category: discord.CategoryChannel):
        """Managers: Remove the tryout role from everyone in that category."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        db = self.bot.db_interface

        # Find the tryout configuration
        tryout_config = await db.fetchrow(
            "SELECT tryout_id, role_id FROM tryouts WHERE guild_id = $1 AND category_id = $2", # Don't require is_active=TRUE for reset
            guild.id, video_game_category.id
        )
        if not tryout_config:
            await interaction.followup.send(f"No tryout configuration found for the category '{video_game_category.name}'.", ephemeral=True)
            return

        role_id = tryout_config['role_id']
        tryout_role = guild.get_role(role_id)
        if not tryout_role:
            await interaction.followup.send("The tryout role for this category seems to be missing already.", ephemeral=True)
            # Optionally clear participant data here if role is gone?
            return

        participants = await db.fetch(
            "SELECT discord_id FROM tryout_participants WHERE tryout_id = $1",
            tryout_config['tryout_id']
        )

        removed_count = 0
        errors = []
        for p_record in participants:
            member = guild.get_member(p_record['discord_id'])
            if member and tryout_role in member.roles:
                try:
                    await member.remove_roles(tryout_role, reason="Tryout reset")
                    removed_count += 1
                except discord.Forbidden:
                    errors.append(f"Cannot remove role from {member.mention} (Permissions missing).")
                except Exception as e:
                    errors.append(f"Error removing role from {member.mention}: {e}")

        # Optionally clear participant data after removing roles
        # await db.execute("DELETE FROM tryout_participants WHERE tryout_id = $1", tryout_config['tryout_id'])
        # await db.execute("DELETE FROM tryout_matches WHERE tryout_id = $1", tryout_config['tryout_id'])
        # self.logger.info(f"Cleared participant and match data for tryout {tryout_config['tryout_id']}")

        response = f"Removed {tryout_role.mention} from {removed_count} participant(s) in '{video_game_category.name}'."
        if errors:
             response += "\nErrors:\n" + "\n".join(errors)
        await interaction.followup.send(response)


async def setup(bot):
    await bot.add_cog(Team(bot))


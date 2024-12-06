import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import asyncio
from database import *
from database import insert_election_candidate, increment_vote, get_election_results  # Import new database functions

class Elections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_election = {}

    @commands.command(name='election')
    @commands.has_permissions(administrator=True)
    async def election(self, ctx):
        await ctx.send("Enter what the election is for:")
        election_for = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        
        await ctx.send("Enter duration in days:")
        duration_msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        duration = int(duration_msg.content.strip())
        
        await ctx.send("Enter space separated list of candidates:")
        candidates_msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        candidates = candidates_msg.content.strip().split()
        
        speeches = {}
        for candidate in candidates:
            await ctx.send(f"Enter a short paragraph for {candidate}:")
            speech_msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            speeches[candidate] = speech_msg.content.strip()
        
        # Insert candidates into the database with initial votes
        for candidate in candidates:
            insert_election_candidate(election_for.content.strip(), candidate)
        
        election_message = f"**Election For:** {election_for.content.strip()}\n\n"
        for idx, (candidate, speech) in enumerate(speeches.items(), start=1):
            election_message += f"({idx}): **{candidate}**: {speech}\n"
        
        view = View()
        view.add_item(VoteButton(self, candidates))  # Pass candidates to VoteButton
        election_msg = await ctx.send(election_message, view=view)
        
        self.active_election['message_id'] = election_msg.id
        self.active_election['candidates'] = candidates
        self.active_election['voters'] = {}
        self.active_election['name'] = election_for.content.strip()
        
        await asyncio.sleep(duration * 86400)  # Duration in seconds
        
        # Tally votes and announce winner
        await self.conclude_election(ctx)

    # Modify election conclusion to use database results
    async def conclude_election(self, ctx):
        results = get_election_results(self.active_election['name'])
        if results:
            winner, votes = max(results.items(), key=lambda item: item[1])
            await ctx.send(f"The winner is {winner} with {votes} votes!")
        else:
            await ctx.send("No votes were cast.")
        self.active_election = {}

class VoteButton(discord.ui.Button):
    def __init__(self, cog, candidates):
        super().__init__(label="Vote", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.candidates = candidates  # Store candidates list

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user

        if self.cog.active_election is None:
            await interaction.response.send_message("There is no active election at the moment.", ephemeral=True)
            return

        if user.id in self.cog.active_election['voters']:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
            return

        try:
            # Send a DM to the user with voting options
            await user.send(
                "Which person would you like to vote for (type the number):\n" +
                "\n".join([f"({i+1}): {candidate}" for i, candidate in enumerate(self.candidates)])
            )
            # Inform the user in the channel that a DM has been sent
            await interaction.response.send_message("I've sent you a DM with the voting options.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't send you a DM. Please check your privacy settings.",
                ephemeral=True
            )
            return

        try:
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)

            vote_msg = await self.cog.bot.wait_for('message', timeout=60.0, check=check)
            vote_number = int(vote_msg.content.strip())

            if 1 <= vote_number <= len(self.candidates):
                selected_candidate = self.candidates[vote_number - 1]
                increment_vote(self.cog.active_election['name'], selected_candidate)
                self.cog.active_election['voters'][user.id] = selected_candidate
                await user.send(f"You voted for {selected_candidate}.")
                await interaction.followup.send("Your vote has been recorded.", ephemeral=True)
            else:
                await user.send("Invalid selection.")
                await interaction.followup.send("Your selection was invalid and was not recorded.", ephemeral=True)

        except asyncio.TimeoutError:
            await user.send("Vote timed out.")
            await interaction.followup.send("You did not vote in time.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't send you a DM. Please check your privacy settings.",
                ephemeral=True
            )
        except Exception as e:
            await user.send("An error occurred while processing your vote.")
            await interaction.followup.send(
                "An error occurred while processing your vote.",
                ephemeral=True
            )
            print(f"Error handling vote from {user}: {e}")

async def setup(bot):
    await bot.add_cog(Elections(bot))

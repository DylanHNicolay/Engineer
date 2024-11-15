import discord

async def initialize_roles(ctx, guild):
    student_role = discord.utils.get(guild.roles, name="Student")
    alumni_role = discord.utils.get(guild.roles, name="Alumni")

    if student_role is None:
        await ctx.send("The 'Student' role does not exist.")
        return None, None
    if alumni_role is None:
        # Create the "Alumni" role if it doesn't exist
        alumni_role = await guild.create_role(name="Alumni")
        await ctx.send("The 'Alumni' role was created.")

    return student_role, alumni_role

async def update_member_roles(guild, student_role, alumni_role):
    updated_members = 0

    for member in guild.members:
        if student_role in member.roles:
            try:
                # Remove the "Student" role and add the "Alumni" role
                await member.remove_roles(student_role, reason="Reverification required: Moving from Student to Alumni")
                await member.add_roles(alumni_role, reason="Reverification required: Assigned Alumni role")

                # DM the user for reverification
                await member.send(
                    "Hello, please reverify your student status in the RPI Esports Discord Server.\n"
                    "https://discord.gg/8tzMdZxBh4"
                )

                updated_members += 1
            except discord.Forbidden:
                await ctx.send(f"Permission error: Could not update roles for {member.display_name}.")
            except Exception as e:
                await ctx.send(f"An error occurred while updating {member.display_name}: {e}")

    return updated_members
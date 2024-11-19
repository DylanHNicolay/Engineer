import discord  # Import discord

async def reduce_years_in_db(cursor, conn, guild):
    try:
        # Reduce years remaining for students and update roles if necessary
        reduce_years_query = '''
        UPDATE user_info
        SET years_remaining = years_remaining - 1
        WHERE is_student = TRUE AND years_remaining > 0;
        '''
        cursor.execute(reduce_years_query)

        # Get students with 0 years remaining
        cursor.execute('SELECT discord_id FROM user_info WHERE years_remaining = 0 AND is_student = TRUE;')
        students_to_update = cursor.fetchall()

        # Update students with 0 years remaining to alumni in the database
        update_to_alumni_query = '''
        UPDATE user_info
        SET is_student = FALSE, is_alumni = TRUE
        WHERE years_remaining = 0;
        '''
        cursor.execute(update_to_alumni_query)

        conn.commit()

        # Update roles in Discord
        student_role = discord.utils.get(guild.roles, name="Student")
        alumni_role = discord.utils.get(guild.roles, name="Alumni")

        for student in students_to_update:
            member = guild.get_member(int(student[0]))
            if member:
                await member.remove_roles(student_role)
                await member.add_roles(alumni_role)
    except Exception as e:
        conn.rollback()
        raise e
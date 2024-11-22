import psycopg2
import os
import schedule
from datetime import datetime

def connect_to_db():
    try:
        # Establish the connection
        conn = psycopg2.connect(
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=os.getenv("POSTGRES_PORT")
        )
        print(f"{os.getenv('POSTGRES_DB')} database connected")  # Print the database name
        cursor = conn.cursor()
        print("Connection to PostgreSQL DB successful")
        return conn, cursor
    except Exception as e:
        print(f"Error connecting to PostgreSQL DB: {e}")
        return None, None

def create_user_info_table(cursor, conn):
    try:
        # Create the table with the specified columns
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS user_info (
            RCSID VARCHAR(255) NOT NULL,
            discord_id VARCHAR(255) NOT NULL UNIQUE,
            discord_username VARCHAR(255) NOT NULL,
            discord_server_username VARCHAR(255),
            is_student BOOLEAN DEFAULT FALSE,
            years_remaining INT CHECK (years_remaining >= 1 AND years_remaining <= 8),
            is_alumni BOOLEAN DEFAULT FALSE,
            is_verified BOOLEAN DEFAULT FALSE,
            verification_code INT
        );
        '''
        # Execute the query
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'user_info' created successfully (if not exists already)")
    except Exception as e:
        print(f"Error creating table: {e}")

def insert_user_data(cursor, conn, members):
    try:
        # Iterate through all members
        for member in members:
            print(f"Inserting or updating user data for {member}")
            discord_id = str(member.id)
            discord_username = str(member.name)
            discord_server_username = str(member.display_name)

            # Insert or update user data in the database
            insert_user_query = '''
            INSERT INTO user_info (RCSID, discord_id, discord_username, discord_server_username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (discord_id) DO UPDATE
            SET discord_username = EXCLUDED.discord_username,
                discord_server_username = EXCLUDED.discord_server_username;
            '''
            cursor.execute(insert_user_query, ("", discord_id, discord_username, discord_server_username))

            # Update additional user data
            update_user_data(cursor, conn, member)

        # Commit changes
        conn.commit()
        print("User data inserted or updated successfully")
    except Exception as e:
        print(f"Error inserting or updating user data in PostgreSQL DB: {e}")

# updates the data of a singular user
def update_user_data(cursor, conn, member, rcsid=""):
    try:
        discord_id = str(member.id)
        discord_username = str(member.name)
        discord_server_username = str(member.display_name)

        # Determine if the user has the "Student", "Alumni", or "Verified" role
        is_student = any(role.name == "Student" for role in member.roles)
        is_alumni = any(role.name == "Alumni" for role in member.roles)
        is_verified = any(role.name == "Verified" for role in member.roles)

        # Update the user data in the database
        update_user_query = '''
        INSERT INTO user_info (RCSID, discord_id, discord_username, discord_server_username, is_student, is_alumni, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (discord_id) DO UPDATE
        SET RCSID = EXCLUDED.RCSID,
            discord_username = EXCLUDED.discord_username,
            discord_server_username = EXCLUDED.discord_server_username,
            is_student = EXCLUDED.is_student,
            is_alumni = EXCLUDED.is_alumni,
            is_verified = EXCLUDED.is_verified;
        '''
        cursor.execute(update_user_query, (rcsid, discord_id, discord_username, discord_server_username, is_student, is_alumni, is_verified))
        conn.commit()
        print(f"User data for {discord_id} updated successfully")

    except Exception as e:
        conn.rollback()  # Roll back the transaction on error
        print(f"Error updating user data in PostgreSQL DB: {e}")

# updates the data of all the users in the database
def update_all_users_data(cursor, conn, members):
    try:
        for member in members:
            update_user_data(cursor, conn, member)
        print("All user data updated successfully")
    except Exception as e:
        print(f"Error updating all user data in PostgreSQL DB: {e}")
        
def daily_update_task():
    """Task that runs daily at 4:30 AM to update the database."""
    print(f"Daily update started at {datetime.now()}")
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        print("Failed to connect to the database for the daily update.")
        return

    try:
        # Fetch all users from the database
        fetch_query = "SELECT discord_id, discord_username, discord_server_username FROM user_info;"
        cursor.execute(fetch_query)
        users = cursor.fetchall()

        # Get the Discord guild
        guild = bot.get_guild(int(os.getenv("SERVER_ID")))
        if not guild:
            print("Guild not found. Skipping user synchronization.")
            return

        # Iterate over each user in the database
        for user in users:
            discord_id, db_username, db_display_name = user

            # Fetch the member information from the Discord server
            member = guild.get_member(int(discord_id))

            if not member:
                # If the user is not found in the server, delete their entry from the database
                delete_query = "DELETE FROM user_info WHERE discord_id = %s;"
                cursor.execute(delete_query, (discord_id,))
                print(f"Deleted user {discord_id} from the database (not found in the server).")
                continue

            # Check for mismatches and update the database if necessary
            if member.name != db_username or member.display_name != db_display_name:
                update_query = """
                UPDATE user_info
                SET discord_username = %s, discord_server_username = %s
                WHERE discord_id = %s;
                """
                cursor.execute(update_query, (member.name, member.display_name, discord_id))
                print(f"Updated user {discord_id}: Username='{member.name}', Display Name='{member.display_name}'")

        conn.commit()
        print("Daily update task completed successfully.")

    except Exception as e:
        print(f"Error during daily update task: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Schedule the daily update task
schedule.every().day.at("04:30").do(daily_update_task)

if __name__ == "__main__":
    print("Scheduler for daily database updates started.")
    while True:
        schedule.run_pending()
        time.sleep(1)
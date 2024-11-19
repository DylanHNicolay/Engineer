import psycopg2
import os

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
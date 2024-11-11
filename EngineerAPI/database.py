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
            years_remaining INT CHECK (years_remaining >= 0 AND years_remaining <= 8),
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
            print(f"Inserting user data for {member}")
            discord_id = str(member.id)
            discord_username = str(member.name)
            discord_server_username = str(member.display_name)

            # Insert user data into the database
            insert_user_query = '''
            INSERT INTO user_info (RCSID, discord_id, discord_username, discord_server_username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (discord_id) DO NOTHING;
            '''
            cursor.execute(insert_user_query, ("", discord_id, discord_username, discord_server_username))

        # Commit changes
        conn.commit()
        print("User data inserted successfully")
    except Exception as e:
        print(f"Error inserting user data into PostgreSQL DB: {e}")

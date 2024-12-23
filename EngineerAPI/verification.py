import psycopg2
import os
import random
from email_utils import send_verification_email  # Import from new file
from database import connect_to_db  # Import the unified function

# Generate verification code
def generate_verification_code():
    return random.randint(100000, 999999)

# Insert or update user information in the database
def update_user_info(cursor, rcsid, discord_id, discord_username, discord_server_username, verification_code):
    try:
        # Step 1: Check if discord_id exists
        check_query = """
            SELECT is_verified
            FROM user_info
            WHERE discord_id = %s
        """
        cursor.execute(check_query, (discord_id,))
        result = cursor.fetchone()

        if result is None:
            # Step 2: Insert new user
            insert_query = """
                INSERT INTO user_info (
                    RCSID,
                    discord_id,
                    discord_username,
                    discord_server_username,
                    verification_code,
                    is_student,
                    is_alumni,
                    is_verified
                )
                VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, FALSE)
            """
            cursor.execute(insert_query, (
                rcsid,
                discord_id,
                discord_username,
                discord_server_username,
                verification_code
            ))
            return "inserted"
        else:
            is_verified = result[0]
            if not is_verified:
                # Step 3: Update existing user
                update_query = """
                    UPDATE user_info
                    SET
                        RCSID = %s,
                        discord_username = %s,
                        discord_server_username = %s,
                        verification_code = %s,
                        is_verified = FALSE
                    WHERE discord_id = %s
                """
                cursor.execute(update_query, (
                    rcsid,
                    discord_username,
                    discord_server_username,
                    verification_code,
                    discord_id
                ))
                return "updated"
            else:
                # Step 4: User is already verified
                return "already_verified"

    except psycopg2.Error as e:
        # Handle database errors
        print(f"Database error occurred: {e}")
        raise
    except Exception as e:
        # Handle other possible errors
        print(f"An error occurred: {e}")
        raise

# Verify code and update user information
def verify_code_and_update_user(cursor, discord_id, entered_code):
    select_query = '''
    SELECT RCSID FROM user_info WHERE discord_id = %s AND verification_code = %s AND is_verified = FALSE;
    '''
    cursor.execute(select_query, (discord_id, entered_code))
    result = cursor.fetchone()
    return result

# Update verification status and years remaining
def update_verification_status(cursor, rcsid, years_remaining):
    update_query = '''
    UPDATE user_info
    SET is_verified = TRUE, is_student = TRUE, years_remaining = %s, verification_code = NULL
    WHERE RCSID = %s;
    '''
    cursor.execute(update_query, (years_remaining, rcsid))

# Handle verification timeout
def handle_verification_timeout(cursor, discord_id):
    update_query = '''
    UPDATE user_info
    SET verification_code = NULL
    WHERE discord_id = %s;
    '''
    cursor.execute(update_query, (discord_id,))

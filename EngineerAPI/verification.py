import psycopg2
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Database connection helper
def connect_to_db_verification():
    return psycopg2.connect(
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )

# Generate verification code
def generate_verification_code():
    return random.randint(100000, 999999)

# Send verification email
def send_verification_email(rcsid, verification_code):
    email = f"{rcsid}@rpi.edu"
    message = MIMEMultipart()
    message['From'] = os.getenv("GMAIL")
    message['To'] = email
    message["Subject"] = "Verification Code"
    message.attach(MIMEText(f'Your verification code is: {verification_code}', "plain"))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("GMAIL"), os.getenv("GMAIL_PASS"))
        server.sendmail(os.getenv("GMAIL"), email, message.as_string())
        print(f"Email successfully sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    finally:
        try:
            server.quit()
        except Exception as quit_error:
            print(f"Failed to close the connection properly: {quit_error}")
    return True

# Insert or update user information in the database
def upsert_user_info(cursor, rcsid, discord_id, discord_username, discord_server_username, verification_code):
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
                        verification_code = %s
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
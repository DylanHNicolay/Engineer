import random
import time
from typing import Optional, Tuple
import re
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import asyncio 

logger = logging.getLogger(__name__)

async def send_verification_email(rcsid, verification_code, sw=1):
    if sw == 1:
        email = f"{rcsid}@rpi.edu"
    else:
        email = f"{rcsid}"
    message = MIMEMultipart()
    message['From'] = os.getenv("GMAIL")
    message['To'] = email
    message["Subject"] = "Verification Code"
    message.attach(MIMEText(f'Your verification code is: {verification_code}', "plain"))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("GMAIL"), os.getenv("GMAIL_PASSWORD"))
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

def generate_verification_code() -> int:
    """Generate a 6-digit verification code"""
    return random.randint(100000, 999999)

def is_valid_rcsid(rcsid: str) -> bool:
    """Check if a string looks like a valid RCS ID"""
    # RCS IDs are typically 3-8 alphanumeric characters
    pattern = re.compile(r'^[a-zA-Z0-9]{3,8}$')
    return bool(pattern.match(rcsid))

def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    # This is a basic check - you might want to use a library like email-validator for production
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))

async def start_student_verification(db, user_id: int, rcsid: str) -> Tuple[bool, str]:
    """
    Start the student verification process
    
    Args:
        db: Database interface
        user_id: Discord user ID
        rcsid: RCS ID to verify
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Validate RCS ID format
        if not is_valid_rcsid(rcsid):
            return False, "Invalid RCS ID format. Please try again."
            
        # Generate verification code
        code = generate_verification_code()
        current_time = int(time.time())
        
        # Update database with verification attempt
        await db.execute('''
            UPDATE users 
            SET verification_code = $1,
                verification_type = 'student',
                rcsid = $2,
                verification_attempt_count = verification_attempt_count + 1,
                last_verification_attempt = $3
            WHERE discord_id = $4
        ''', code, rcsid, current_time, user_id)
        
        # Send verification email
        if await send_verification_email(rcsid, code, sw=1):
            return True, f"A verification code has been sent to {rcsid}@rpi.edu"
        else:
            return False, "Failed to send verification email. Please try again later."
            
    except Exception as e:
        logger.error(f"Error in start_student_verification: {e}")
        return False, "An error occurred. Please try again later."

async def start_prospective_verification(db, user_id: int, email: str) -> Tuple[bool, str]:
    """
    Start the prospective student verification process
    
    Args:
        db: Database interface
        user_id: Discord user ID
        email: Email address to verify
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Validate email format
        if not is_valid_email(email):
            return False, "Invalid email format. Please try again."
            
        # Generate verification code
        code = generate_verification_code()
        current_time = int(time.time())
        
        # Update database with verification attempt
        await db.execute('''
            UPDATE users 
            SET verification_code = $1,
                verification_type = 'prospective',
                verification_email = $2,
                verification_attempt_count = verification_attempt_count + 1,
                last_verification_attempt = $3
            WHERE discord_id = $4
        ''', code, email, current_time, user_id)
        
        # Send verification email
        if await send_verification_email(email, code):
            return True, f"A verification code has been sent to {email}"
        else:
            return False, "Failed to send verification email. Please try again later."
            
    except Exception as e:
        logger.error(f"Error in start_prospective_verification: {e}")
        return False, "An error occurred. Please try again later."

async def verify_code(db, user_id: int, entered_code: int) -> Tuple[bool, str, Optional[str]]:
    """
    Verify a user's entered code
    
    Args:
        db: Database interface
        user_id: Discord user ID
        entered_code: Code entered by user
        
    Returns:
        Tuple[bool, str, Optional[str]]: (success, message, verification_type if successful)
    """
    try:
        # Get current verification data
        user_data = await db.fetchrow('''
            SELECT verification_code, verification_type, last_verification_attempt
            FROM users WHERE discord_id = $1
        ''', user_id)
        
        if not user_data or not user_data['verification_code']:
            return False, "No verification in progress. Please start verification first.", None
            
        # Check if verification has expired (5 minutes)
        current_time = int(time.time())
        if current_time - user_data['last_verification_attempt'] > 300:
            await db.execute('''
                UPDATE users 
                SET verification_code = NULL 
                WHERE discord_id = $1
            ''', user_id)
            return False, "Verification code has expired. Please request a new code.", None
            
        # Check code
        if entered_code != user_data['verification_code']:
            return False, "Incorrect verification code. Please try again.", None
            
        # Clear verification code
        await db.execute('''
            UPDATE users 
            SET verification_code = NULL 
            WHERE discord_id = $1
        ''', user_id)
        
        return True, "Code verified successfully!", user_data['verification_type']
        
    except Exception as e:
        logger.error(f"Error in verify_code: {e}")
        return False, "An error occurred. Please try again later.", None

async def update_verification_status(db, user_id: int, guild_id: int, 
                                  verification_type: str, years: Optional[int] = None) -> bool:
    """
    Update a user's verification status
    
    Args:
        db: Database interface
        user_id: Discord user ID
        guild_id: Discord guild ID
        verification_type: Type of verification ('student', 'alumni', etc)
        years: Number of years remaining (for students)
        
    Returns:
        bool: Success status
    """
    try:
        # Start a transaction
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                # Reset all verification flags first
                await conn.execute('''
                    UPDATE users 
                    SET student = FALSE,
                        alumni = FALSE,
                        prospective = FALSE,
                        friend = FALSE,
                        rpi_admin = FALSE
                    WHERE discord_id = $1
                ''', user_id)
                
                # Set the appropriate flag and verified status
                if verification_type == 'student':
                    await conn.execute('''
                        UPDATE users 
                        SET verified = TRUE,
                            student = TRUE,
                            years_remaining = $1
                        WHERE discord_id = $2
                    ''', years, user_id)
                else:
                    await conn.execute(f'''
                        UPDATE users 
                        SET verified = TRUE,
                            {verification_type} = TRUE
                        WHERE discord_id = $1
                    ''', user_id)
                    
                # Ensure user is in user_guilds table
                await conn.execute('''
                    INSERT INTO user_guilds (discord_id, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (discord_id, guild_id) DO NOTHING
                ''', user_id, guild_id)
                
        return True
        
    except Exception as e:
        logger.error(f"Error in update_verification_status: {e}")
        return False
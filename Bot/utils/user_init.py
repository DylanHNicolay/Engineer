from .db import db

async def add_user(user_id: int, years_remaining: int = None):
    """
    Adds or updates a user in the database.

    Args:
        user_id (int): The Discord ID of the user.
        years_remaining (int, optional): The number of years remaining for the user. Defaults to None.
    """
    await db.execute(
        """
        INSERT INTO users (discord_id, years_remaining)
        VALUES ($1, $2)
        ON CONFLICT (discord_id) DO UPDATE SET
        years_remaining = EXCLUDED.years_remaining;
        """,
        user_id,
        years_remaining
    )

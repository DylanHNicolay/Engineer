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
        print(f"{os.getenv('POSTGRES_DB')} database connected") # Print the database name
        cursor = conn.cursor()
        print("Connection to PostgreSQL DB successful")
    except Exception as e:
        print(f"Error connecting to PostgreSQL DB: {e}")
        return None, None
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

connection = psycopg2.connect(
    host="aws-0-us-west-2.pooler.supabase.com",
    port=5432,
    database="postgres",
    user="postgres.nawgocxwoxmuwshkfbue",
    password=os.getenv("SUPABASE_DB_PASSWORD")
)

cursor = connection.cursor()

cursor.execute("""
    INSERT INTO users (telegram_id, name, email, phone, password)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
""", (
    999999999,
    "Aether Test",
    "aether@test.com",
    "08000000000",
    "test123"
))

user_id = cursor.fetchone()[0]

connection.commit()

print("Test user created successfully!")
print("User ID:", user_id)

cursor.close()
connection.close()
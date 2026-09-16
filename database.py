import os

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DB_CONFIG = {
    "host": "aws-0-us-west-2.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.nawgocxwoxmuwshkfbue",
    "password": os.getenv("SUPABASE_DB_PASSWORD"),
    "sslmode": "require",
}


# --------------------------------------------------
# DATABASE CONNECTION POOL
# --------------------------------------------------

DB_POOL = ThreadedConnectionPool(
    minconn=1,
    maxconn=5,
    **DB_CONFIG
)


def get_connection():
    return DB_POOL.getconn()


def release_connection(connection):
    try:
        if connection.closed == 0:
            connection.rollback()
    except Exception:
        pass

    DB_POOL.putconn(connection)


# --------------------------------------------------
# TEST DATABASE CONNECTION
# --------------------------------------------------

def test_connection():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

            print("Database connection successful:", result)

    finally:
        release_connection(connection)


# --------------------------------------------------
# GET USER BY TELEGRAM ID
# --------------------------------------------------

def get_user_by_telegram_id(telegram_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    telegram_id,
                    name,
                    email,
                    phone,
                    wallet_status
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "telegram_id": row[1],
                "name": row[2],
                "email": row[3],
                "phone": row[4],
                "wallet_status": row[5],
            }

    finally:
        release_connection(connection)


# --------------------------------------------------
# LOGIN USER
# --------------------------------------------------

def get_user_by_email_and_password(email, password):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    telegram_id,
                    name,
                    email,
                    phone,
                    wallet_status
                FROM users
                WHERE email = %s
                AND password = %s
                """,
                (email, password)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "telegram_id": row[1],
                "name": row[2],
                "email": row[3],
                "phone": row[4],
                "wallet_status": row[5],
            }

    finally:
        release_connection(connection)


# --------------------------------------------------
# CREATE USER
# --------------------------------------------------

def create_user(telegram_id, name, email, phone, password):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (
                    telegram_id,
                    name,
                    email,
                    phone,
                    password
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    telegram_id,
                    name,
                    email,
                    phone,
                    password,
                )
            )

            user_id = cursor.fetchone()[0]

        connection.commit()

        return user_id

    finally:
        release_connection(connection)


# --------------------------------------------------
# GET WALLET STATUS
# --------------------------------------------------

def get_wallet_status(user_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT wallet_status
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return row[0]

    finally:
        release_connection(connection)


# --------------------------------------------------
# SET WALLET STATUS
# --------------------------------------------------

def set_wallet_status(user_id, status):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET wallet_status = %s
                WHERE id = %s
                """,
                (status, user_id)
            )

        connection.commit()

    finally:
        release_connection(connection)


# --------------------------------------------------
# GET WALLET
# --------------------------------------------------

def get_wallet(user_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    solana_address,
                    solana_balance,
                    ethereum_address,
                    ethereum_balance,
                    bitcoin_address,
                    bitcoin_balance
                FROM wallets
                WHERE user_id = %s
                """,
                (user_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "solana_address": row[0],
                "solana_balance": row[1],
                "ethereum_address": row[2],
                "ethereum_balance": row[3],
                "bitcoin_address": row[4],
                "bitcoin_balance": row[5],
            }

    finally:
        release_connection(connection)


# --------------------------------------------------
# CREATE WALLET
# --------------------------------------------------

def create_wallet(user_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wallets (
                    user_id
                )
                VALUES (%s)
                RETURNING id
                """,
                (user_id,)
            )

            wallet_id = cursor.fetchone()[0]

        connection.commit()

        return wallet_id

    finally:
        release_connection(connection)


# --------------------------------------------------
# TEST DATABASE WHEN RUN DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":
    test_connection()

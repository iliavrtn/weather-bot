from psycopg2 import pool
from config import *

# Connection pool configuration
POOL_MIN_CONNECTIONS = 1
POOL_MAX_CONNECTIONS = 5

# Database initialization function
def init_database():
    return pool.SimpleConnectionPool(
        POOL_MIN_CONNECTIONS,
        POOL_MAX_CONNECTIONS,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# Global variable to store the connection pool
db_pool = init_database()

def execute_query(query, params=None) -> list:
    """
    Execute a SQL query.

    Parameters:
    - query (str): The SQL query to execute
    - params (tuple): The parameters to bind to the query

    Returns:
    - result (list or None): The result of the query
    """
    connection = db_pool.getconn()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)

            # Check if the query is an UPDATE, INSERT, DELETE, etc.
            if query.strip().upper().startswith("UPDATE") or query.strip().upper().startswith("INSERT") or query.strip().upper().startswith("DELETE"):
                # For non-select queries, commit the changes and return None
                connection.commit()
                return None
            else:
                # For SELECT queries, fetch and return the results
                result = cursor.fetchall()
                return result if result else None

    except Exception as e:
        # Handle exceptions, print an error message, or raise an exception as needed
        print(f"Error executing query: {e}")

    finally:
        db_pool.putconn(connection)

def get_users_with_daily_updates() -> list:
    """
    Retrieve a list of users with daily updates.

    Returns:
    - result (list): The list of users with daily updates
    """
    query = "SELECT * FROM telegram_users.users"
    result = execute_query(query)
    return result

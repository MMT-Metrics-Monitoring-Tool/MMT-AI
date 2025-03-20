from mysql.connector import Error
from dotenv import load_dotenv
import mysql.connector
import os


class DatabaseConnector:
    def __init__(self):
        load_dotenv()
        # Defaults to MMT database testing defaults.
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = os.getenv("DB_PORT", "3306")
        self.user = os.getenv("DB_USER", "test_myapp")
        self.password = os.getenv("DB_PASSWORD", "secret")
        self.database = os.getenv("DB_NAME", "test_myapp")
        self.connection = None
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                print("MariaDB connection established.")
        except Error as e:
            print(f"Error establishing MariaDB connection: {e}")
            self.connection = None

    def query(self, query: str, params=None):
        if self.connection is None:
            self.connect()
        if not self.connection:
            print(f"Query failed due to connection error.")
            return None
        if "SELECT" in query:
            return select_query(query, params)
        elif any(op in query for op in ["INSERT", "UPDATE", "DELETE"]):
            return execute_query(query, params)
        # If both conditions above were false, the query is erroneous.
        print(f"Erroneous query: {query}")
        return None
    
    # For SELECT queries.
    def select_query(self, query: str, params=None):
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"Error executing query: {e}")
            return None
    
    # For INSERT/UPDATE/DELETE queries.
    def execute_query(self, query: str, params=None):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor.rowcount()
        except Error as e:
            print(f"Error executing query: {e}")
            return None
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MariaDB connection closed.")


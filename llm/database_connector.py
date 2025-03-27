from mysql.connector import Error
from dotenv import load_dotenv
import mysql.connector
import os


class DatabaseConnector:
    def __init__(self):
        """Initialises database parameters.

        Parameters are fetched as environment variables. Set by using a .env file in the project directory.
        DB_HOST: Hostname or address of the server that the target database runs on.
        DB_PORT: Port number for the database connection.
        DB_USER: Database user to use the database as.
        DB_PASS: Database password for the selected user.
        DB_NAME: Name of the database schema to connect to.

        If any of the parameters are missing, it is assumed that an MMT instance started with "make run" is
        running locally and default parameters are used.
        """
        load_dotenv()
        # Defaults to MMT database testing defaults.
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = os.getenv("DB_PORT", "3306")
        self.user = os.getenv("DB_USER", "my_app")
        self.password = os.getenv("DB_PASS", "secret")
        self.database = os.getenv("DB_NAME", "my_app")
        self.connection = None
    
    def connect(self):
        """Creates a database connection.

        Connection parameters must be defined into the object beforehand.
        """
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
        """General purpose database query function.
        
        Performs any database query.
        Attempts to establish the database connection automatically if it does not exist.
        Routes queries to ~llm.database_connector.DatabaseConnector.select_query or ~llm.database_connector.DatabaseConnector.execute_query.
        """

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
    
    def select_query(self, query: str, params=None):
        """Database query function for queries which do not alter the database.
        
        Should not be called directly as ~llm.database_connector.DatabaseConnector.query handles the connection.
        """

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"Error executing query: {e}")
            return None
    
    def execute_query(self, query: str, params=None):
        """Database query function fro queries which have an effect on the database state.
        
        Should not be called directly as ~llm.database_connector.DatabaseConnector.query handles the connection.
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor.rowcount()
        except Error as e:
            print(f"Error executing query: {e}")
            return None
    
    def close(self):
        """Closes the database connection."""

        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MariaDB connection closed.")


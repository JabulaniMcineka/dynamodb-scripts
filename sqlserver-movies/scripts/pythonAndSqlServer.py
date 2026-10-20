# pyodbc lets Python talk to SQL Server through an ODBC driver
import pyodbc
# json is imported for loading the movie data later (not used yet in this version)
import json


# The SQL Server instance to connect to; the r"" raw string keeps the backslash literal
server = r"localhost\SQLDEV"
# The name of the database this script will create and work in
database = "MoviesBD"

json_file = "data/02_05_data.json"  # Path to the JSON file containing movie data


# Define a function that opens a connection to SQL Server
# database is optional: if you leave it out, you land in the default database (master)
# autocommit=True makes every statement save immediately (needed for CREATE DATABASE)
def connect_to_sql_server(server, database=None, autocommit=False):
    """Connect to the instance; if a database is given, connect to it, otherwise land in master."""
    # try/except catches connection errors so the script prints a message instead of crashing
    try:
        # Build the connection string in pieces; the driver name needs doubled braces {{ }} inside an f-string
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            # Which SQL Server instance to connect to
            f"SERVER={server};"
            # Use your Windows login, so no username or password is stored in the code
            f"Trusted_Connection=yes;"
        )
        # Only add the DATABASE part if a database name was passed in
        if database:
            connection_string += f"DATABASE={database};"
        # Open the connection using the string above
        connection = pyodbc.connect(connection_string, autocommit=autocommit)
        # Tell the user where we connected; "database or ..." falls back to the text if database is None
        print(f"Connected to {database or 'the instance (master)'}.")
        # Hand the open connection back to the caller
        return connection
    # Catch any error, such as wrong instance name, missing database or login failure
    except Exception as e:
        # Print the error so you can read what went wrong
        print(f"Error connecting to SQL Server: {e}")
        # Return None so the caller can check "if connection:" and skip the rest
        return None

# Define a function that creates the database if it is missing
def create_database(server, database):
    """Create the database if it doesn't already exist."""
    # Start as None so the finally block can safely check it even if connecting fails
    connection = None

    try:
        # Connect to the instance only (master), because the new database doesn't exist yet
        # autocommit=True is required: CREATE DATABASE cannot run inside a transaction
        connection = connect_to_sql_server(server, autocommit=True)
        # If the connection failed, stop here; the error was already printed
        if connection is None:
            return
        # A cursor is the object that sends SQL commands to the server
        cursor = connection.cursor()
        # DB_ID returns NULL when the database doesn't exist, so it is only created when missing
        cursor.execute(f"IF DB_ID('{database}') IS NULL CREATE DATABASE {database}")
        # Confirm to the user that the database exists now
        print(f"Database '{database}' is ready.")


    # Catch any error raised while creating the database
    except Exception as e:
        # Print the error with the database name for context
        print(f"Error creating database '{database}': {e}")
    # finally always runs, whether or not an error happened
    finally:
        # Close the connection if one was opened, to free the resource
        if connection:
            connection.close()



# Define a function that creates the Movies table inside the connected database
def create_table(connection):
    # Get a cursor to send the SQL command
    cursor = connection.cursor()
    # Run the SQL; triple quotes allow a multi-line string
    cursor.execute("""
        -- OBJECT_ID returns NULL when the table doesn't exist, so it is only created when missing
        IF OBJECT_ID('dbo.Movies') IS NULL
        CREATE TABLE dbo.Movies (
            -- year is a whole number and can't be empty
            year  INT           NOT NULL,
            -- title is text (up to 400 characters, Unicode) and can't be empty
            title NVARCHAR(400) NOT NULL,
            -- year + title together must be unique, like the key in the DynamoDB table
            PRIMARY KEY (year, title)
        )
    """)
    # Save the change (this connection is not in autocommit mode)
    connection.commit()
    # Confirm to the user
    print("Table ready.")

def load_data(connection, json_file):
    """Load movie data from a JSON file into the Movies table."""

    try:
        # with closes the file automatically; json.load turns the JSON into a list of dictionaries
        with open(json_file, "r", encoding="utf-8") as f:
            movies = json.load(f)

        # Build a list of (year, title) tuples from the first 100 movies only
        rows = [(int(m["year"]), m["title"]) for m in movies[:100]]

        # One cursor for the whole load
        cursor = connection.cursor()
        # Send the rows in one batch instead of one INSERT per movie (much faster)
        cursor.fast_executemany = True
        cursor.executemany("INSERT INTO dbo.Movies (year, title) VALUES (?, ?)", rows)

        # Commit once, after every row has been inserted
        connection.commit()
        print(f"Loaded {len(rows)} movies into the database.")
    except KeyError as e:
        print(f"A movie is missing the field: {e}")
    except pyodbc.Error as e:
        connection.rollback()
        print(f"Database error during load: {e}")
    except FileNotFoundError:
        print(f"File not found: {json_file}")
    except json.JSONDecodeError:
        print(f"Invalid JSON in file: {json_file}")
    except pyodbc.IntegrityError as e:
        # Duplicate (year, title): undo the partial insert
        connection.rollback()
        print(f"Integrity error occurred: {e}")


def query_movies(connection, year):
    cursor = connection.cursor()
    cursor.execute("SELECT year, title FROM dbo.Movies WHERE year = ? ORDER BY title", year)
    return cursor.fetchall()


def delete_database(server, database):
    conn = connect_to_sql_server(server, "master", autocommit=True)
    if conn is None:
        return
    conn.execute(f"""
        IF DB_ID('{database}') IS NOT NULL
        BEGIN
            ALTER DATABASE {database} SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
            DROP DATABASE {database};
        END
    """)
    conn.close()
    print("Database deleted.")


def clear_table_if_loaded(connection):
    """Delete all rows from dbo.Movies if data has already been loaded."""
    cursor = connection.cursor()
    # COUNT(*) tells us how many rows are in the table right now
    cursor.execute("SELECT COUNT(*) FROM dbo.Movies")
    # fetchone returns a single row; [0] is the count
    row_count = cursor.fetchone()[0]

    if row_count > 0:
        # Remove every row but keep the table itself
        cursor.execute("DELETE FROM dbo.Movies")
        connection.commit()
        print(f"Data was already loaded, deleted {row_count} existing rows.")
    else:
        print("Table is empty, nothing to delete.")



# This block only runs when you execute the file directly, not when it is imported
if __name__ == "__main__":
    # Step 1: make sure the database exists (connects to master internally)
    create_database(server, database)
    # Step 2: connect to the new database itself
    connection = connect_to_sql_server(server, database)
    # Only continue if the connection succeeded (None is falsy)
    if connection:
        # Step 3: create the Movies table inside MoviesBD
        create_table(connection)
        # Step 4: clear any rows left from a previous run
        clear_table_if_loaded(connection)
        # Step 5: load data into the table
        load_data(connection, json_file)
        # Step 6: query and print the 2013 movies
        for year, title in query_movies(connection, 2013):
            print(year, ":", title)
        # Step 7: close the connection when finished
        connection.close()
        # delete_database(server, database)   # uncomment for a clean slate each run
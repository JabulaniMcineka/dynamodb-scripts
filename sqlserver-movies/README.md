# SQL Server Movies: Python Practice Project

A small Python project that creates a SQL Server database, loads a movie dataset into it, queries it, and can delete it again. It covers the full create, load, query, delete cycle using `pyodbc`, and it is safe to rerun.

I built it to practise Python and SQL Server basics locally (no cloud costs) after working through the DynamoDB version of the same exercise from the LinkedIn Learning *Data Engineering with AWS* course.

## What it does

1. Connects to a local SQL Server instance using Windows authentication.
2. Creates the `MoviesBD` database if it doesn't exist.
3. Creates a `dbo.Movies` table with a composite primary key (`year`, `title`).
4. Deletes any rows already in the table, so a rerun never hits duplicate keys.
5. Loads the first 100 movies from a JSON file in one batch.
6. Queries the movies for a given year (2013 by default) and prints them.
7. Optionally drops the database when finished (off by default, see below).

## Project structure

```
sqlserver-movies/
├── scripts/
│   └── pythonAndSqlServer.py   # the main script
├── data/
│   └── 02_05_data.json         # dataset (not included, see below)
└── README.md
```

## Prerequisites

- Python 3.9 or later
- A SQL Server instance you can log in to with your Windows account (the script uses `localhost\SQLDEV`)
- [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- The `pyodbc` package

## Setup

1. Install the dependency:

   ```cmd
   pip install pyodbc
   ```

2. Check that the ODBC driver is installed:

   ```cmd
   python -c "import pyodbc; print(pyodbc.drivers())"
   ```

   `ODBC Driver 17 for SQL Server` should be in the list. If you only have Driver 18, change the driver name in `connect_to_sql_server` and add `TrustServerCertificate=yes;` to the connection string.

3. Check the settings at the top of `scripts/pythonAndSqlServer.py`:

   ```python
   server = r"localhost\SQLDEV"   # your SQL Server instance
   database = "MoviesBD"          # database the script creates and works in
   json_file = "data/02_05_data.json"
   ```

## Dataset

The data file is **not included** in this repository. It comes from the LinkedIn Learning course *Data Engineering with AWS Part 1* ([LinkedInLearning/data-engineering-AWS-1-3010976](https://github.com/LinkedInLearning/data-engineering-AWS-1-3010976), branch `02_05`), which is licensed for learners. To run the project:

1. Get `02_05_data.json` from that branch.
2. Save it as `data/02_05_data.json` inside this project.

The script expects a JSON list of objects that each have at least a `year` and a `title`. Any other fields are ignored.

## Running it

Run the script from the project root (`sqlserver-movies`), because the data path is relative:

```cmd
cd sqlserver-movies
python scripts/pythonAndSqlServer.py
```

### Expected output

First run:

```
Connected to the instance (master).
Database 'MoviesBD' is ready.
Connected to MoviesBD.
Table ready.
Table is empty, nothing to delete.
Loaded 100 movies into the database.
2013 : <movie title>
```

Second and later runs differ in one line, because the existing rows are cleared first:

```
Data was already loaded, deleted 100 existing rows.
```

The number of 2013 lines depends on which movies are in the first 100, so there may be none.

## How it works

| Function | Purpose |
|---|---|
| `connect_to_sql_server(server, database=None, autocommit=False)` | Opens a connection. With no database it lands in `master`. Returns `None` and prints the error if the connection fails. |
| `create_database(server, database)` | Connects to `master` with autocommit on (required for `CREATE DATABASE`) and creates the database only if `DB_ID` shows it is missing. |
| `create_table(connection)` | Creates `dbo.Movies` only if it doesn't already exist. |
| `clear_table_if_loaded(connection)` | Counts the rows in `dbo.Movies`. If there are any, it deletes them all (keeping the table) and reports how many were removed. |
| `load_data(connection, json_file)` | Reads the JSON file and inserts the first 100 movies in one batch (`fast_executemany`) with a single commit. Handles a missing file, invalid JSON and duplicate keys (with rollback). |
| `query_movies(connection, year)` | Returns all movies for a year, ordered by title, using a parameterised query. |
| `delete_database(server, database)` | Switches the database to single-user mode to drop open connections, then drops it. |

### Design notes

- **Two connections.** A database can't be connected to before it exists, so database creation happens through a connection to `master`, then the script opens a second connection to `MoviesBD`.
- **Clear before load.** `clear_table_if_loaded` runs after `create_table` (the count would fail if the table didn't exist) and before `load_data`. This is what makes reruns safe.
- **Windows authentication.** `Trusted_Connection=yes` means no username or password appears in the code.
- **Parameterised queries.** Values are passed with `?` placeholders instead of being formatted into the SQL, which prevents SQL injection.
- **Composite primary key.** `(year, title)` mirrors the partition and sort key from the DynamoDB version of this exercise.
- **Single commit.** All 100 rows are inserted and committed together, so a failed load doesn't leave partial data.

## Keeping or deleting the database

By default the database **stays** after the script finishes, so you can open it in SSMS and explore the data. The call at the end of the main block is commented out:

```python
# delete_database(server, database)
```

Uncomment it if you want a clean slate after every run. Note that with it active, the table is always empty at the start of the next run, so `clear_table_if_loaded` will just report "Table is empty".

Only ever point `delete_database` at a database you created for this project. It drops whatever name it is given.

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| `08001` / `Error Locating Server/Instance Specified` | Wrong instance name, or the SQL Server service is not running | Check the instance name in SSMS and the service in SQL Server Configuration Manager |
| `28000` / `Cannot open database` | The database doesn't exist yet | Let `create_database` run first, or create it manually |
| `Data source name not found` | The driver name doesn't match an installed driver | Use the exact name printed by `pyodbc.drivers()` |
| `certificate chain was issued by an authority that is not trusted` | ODBC Driver 18 enforces encryption | Add `TrustServerCertificate=yes;` (local development only) |
| `File not found` | Wrong working directory or missing data file | Run from the project root and check `data/02_05_data.json` exists |
| `Invalid object name 'dbo.Movies'` | `clear_table_if_loaded` ran before the table existed | Call `create_table` first, as in the main block |
| `Integrity error occurred` | The dataset contains duplicate (year, title) pairs | Remove the duplicates, or check the file is the expected dataset |

## Possible next steps

- Load the whole dataset instead of 100 movies by changing `movies[:100]` to `movies` in `load_data`.
- Add `UPDATE` and single-row `DELETE` functions.
- Add a query with `GROUP BY` to count movies per year.
- Use `TRUNCATE TABLE` instead of `DELETE` in `clear_table_if_loaded` for larger tables (it fails if another table has a foreign key to it).
- Move the connection settings into environment variables or a `.env` file.
- Rebuild the same exercise with a dataset of your own.

## Acknowledgements

The dataset and original exercise come from the LinkedIn Learning course *Data Engineering with AWS Part 1*.

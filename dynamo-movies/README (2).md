# DynamoDB Movies: Python Practice Project

A small Python project that creates an Amazon DynamoDB table, loads a movie dataset into it, queries it, and can delete it again, using `boto3`. It is safe to rerun.

This is the DynamoDB twin of my [SQL Server movies project](../sqlserver-movies/). The two scripts follow the same steps, so the differences between a relational database and a NoSQL key-value store are easy to compare.

## What it does

1. Connects to DynamoDB in `us-east-1` and checks the AWS credentials work.
2. Creates the `Movies` table if it doesn't exist (partition key `year`, sort key `title`).
3. Deletes any items already in the table, so a rerun starts clean.
4. Loads the first 100 movies from a JSON file in batches.
5. Queries the movies for a given year (2013 by default) and prints them.
6. Optionally deletes the table when finished (off by default, see below).

## Project structure

```
dynamodb-movies/
├── scripts/
│   └── pythonAndDynamoDB.py   # the main script
├── data/
│   └── 02_05_data.json        # dataset (not included, see below)
└── README.md
```

## Prerequisites

- Python 3.9 or later
- An AWS account and credentials configured on your machine (`aws configure`)
- The `boto3` package
- IAM permissions to create tables and read, write and delete items in DynamoDB

## Setup

1. Install the dependency:

   ```cmd
   pip install boto3
   ```

2. Check your credentials and region:

   ```cmd
   aws sts get-caller-identity
   aws configure list
   ```

3. Check the settings at the top of `scripts/pythonAndDynamoDB.py`:

   ```python
   region = "us-east-1"
   table_name = "Movies"
   json_file = "data/02_05_data.json"
   ```

   DynamoDB tables belong to one region, so the script and the AWS console must use the same one.

## Dataset

The data file is **not included** in this repository. It comes from the LinkedIn Learning course *Data Engineering with AWS Part 1* ([LinkedInLearning/data-engineering-AWS-1-3010976](https://github.com/LinkedInLearning/data-engineering-AWS-1-3010976), branch `02_05`), which is licensed for learners. To run the project:

1. Get `02_05_data.json` from that branch.
2. Save it as `data/02_05_data.json` inside this project.

The script expects a JSON list of objects that each have at least a `year` and a `title`. Any other fields are stored as extra attributes on the item.

## Running it

Run the script from the project root (`dynamodb-movies`), because the data path is relative:

```cmd
cd dynamodb-movies
python scripts/pythonAndDynamoDB.py
```

### Expected output

First run:

```
Connected to DynamoDB in us-east-1.
Table 'Movies' created.
Table is empty, nothing to delete.
Loaded 100 movies into the database.
2013 : <movie title>
```

Second and later runs say `Table 'Movies' already exists.` and `Data was already loaded, deleted 100 existing items.` instead. The number of 2013 lines depends on which movies are in the first 100, so there may be none.

## How it works

| Function | Purpose |
|---|---|
| `connect_to_dynamodb(region)` | Creates the DynamoDB resource and makes a cheap `list_tables` call to prove the credentials and region work. Returns `None` and prints a message if not. |
| `create_table(dynamodb, table_name)` | Creates the table if it is missing, with on-demand billing, then waits until it is `ACTIVE`. |
| `clear_table_if_loaded(table)` | Scans the keys page by page and deletes every item in batches, keeping the table. Reports how many were removed. |
| `load_data(table, json_file)` | Reads the JSON, converts floats to `Decimal`, and writes the first 100 movies with a batch writer. |
| `query_movies(table, year)` | Returns all movies for a year using a key condition, following pagination if needed. |
| `delete_table(dynamodb, table_name)` | Deletes the whole table and waits until it is gone. |

### Design notes

- **Composite key.** `year` is the partition key and `title` is the sort key. A query by `year` returns that year's movies already sorted by title, so no `ORDER BY` is needed.
- **Decimal, not float.** DynamoDB rejects Python floats, so the JSON is loaded with `parse_float=Decimal`.
- **Reserved words.** `year` is a reserved word in DynamoDB, so the scan uses placeholders (`#y`, `#t`) for attribute names.
- **Consistent reads.** Reads are eventually consistent by default, so queries and scans use `ConsistentRead=True` to see items written a moment earlier.
- **On-demand billing.** `PAY_PER_REQUEST` means no provisioned capacity is charged while the table sits idle.
- **No delete-all.** DynamoDB has no `DELETE FROM`. Clearing a table means scanning the keys and deleting each item.

## SQL Server vs DynamoDB

| | SQL Server version | DynamoDB version |
|---|---|---|
| Library | `pyodbc` | `boto3` |
| Connection | Windows login to a local instance | AWS credentials and a region |
| Container | Database, then table | Table only |
| Key | `PRIMARY KEY (year, title)` | Partition key `year`, sort key `title` |
| Query | `SELECT ... WHERE year = ?` | `table.query(KeyConditionExpression=Key("year").eq(year))` |
| Clear data | `DELETE FROM dbo.Movies` | Scan keys, then batch delete |
| Duplicate keys | `IntegrityError` | Silently overwritten |
| Cost | Free (local) | Pay per request on a real AWS account |

## Keeping or deleting the table

By default the table **stays** after the script finishes, so you can look at the items in the AWS console. The call at the end of the main block is commented out:

```python
# delete_table(dynamodb, table_name)
```

Uncomment it to delete the table at the end of every run. An idle on-demand table with a few items costs almost nothing, but delete it when you've finished practising.

Only run `delete_table` on a table you created for this project. If a table named `Movies` already existed in the region, the script reuses it, and the clear step will delete its items.

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| `No AWS credentials found` | No access keys configured | Run `aws configure` |
| `The security token included in the request is invalid` or `expired` | Wrong or expired keys | Create new access keys, or refresh your session, and reconfigure |
| `AccessDeniedException` | The IAM user lacks DynamoDB permissions | Attach a policy that allows the DynamoDB actions used |
| `ResourceNotFoundException` | The table is in a different region, or doesn't exist yet | Check `region` matches the console, and that `create_table` ran |
| `File not found` | Wrong working directory or missing data file | Run from the project root and check `data/02_05_data.json` exists |
| `Float types are not supported` | Floats reached DynamoDB | Load the JSON with `parse_float=Decimal` |
| No 2013 movies printed | None of the first 100 movies is from 2013 | Query another year, or load the whole file |

## Possible next steps

- Load the whole dataset instead of 100 movies by changing `movies[:100]` to `movies` in `load_data`.
- Add a `FilterExpression` to the query, for example only movies above a rating.
- Add single-item `get`, `update` and `delete` functions.
- Create the same table with CloudFormation, Terraform or the CDK instead of Python.
- Run the code against DynamoDB Local or `moto` to practise without touching AWS.

## Acknowledgements

The dataset and original exercise come from the LinkedIn Learning course *Data Engineering with AWS Part 1*.

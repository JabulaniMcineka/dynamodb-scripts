import json
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


# One region for every call, so the table is created and loaded in the same place
region = "us-east-1"
table_name = "Movies"
json_file = "data/02_05_data.json"


def create_movie_table(table_name):
    dynamodb = boto3.client("dynamodb", region_name=region)
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "year", "KeyType": "HASH"},    # Partition key
                {"AttributeName": "title", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "year", "AttributeType": "N"},
                {"AttributeName": "title", "AttributeType": "S"},
            ],
            # On-demand billing: no provisioned capacity to pay for while idle
            BillingMode="PAY_PER_REQUEST",
        )
        print("Table status:", response["TableDescription"]["TableStatus"])
        dynamodb.get_waiter("table_exists").wait(TableName=table_name)
        print("Table is now ACTIVE")
    except ClientError as e:
        # The table is already there, which is fine on a rerun
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{table_name}' already exists.")
        else:
            print(f"Error creating table: {e.response['Error']['Message']}")


def load_data(json_file):
    """Load the first 100 movies from a JSON file into the Movies table."""
    try:
        # Reading the file here means the handlers below can catch its errors
        with open(json_file, "r", encoding="utf-8") as f:
            movies = json.load(f, parse_float=Decimal)

        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)

        for item in movies[:100]:
            item["year"] = int(item["year"])
            print("Adding movie:", item["year"], item["title"])
            table.put_item(Item=item)

    except KeyError as e:
        print(f"A movie is missing the field: {e}")
    except FileNotFoundError:
        print(f"File not found: {json_file}")
    except json.JSONDecodeError:
        print(f"Invalid JSON in file: {json_file}")
    except ClientError as e:
        print(f"Database error during load: {e.response['Error']['Message']}")


def query_movies(year):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    response = table.query(
        KeyConditionExpression=Key("year").eq(year)
    )
    return response["Items"]



def clear_table_if_loaded(connection):
    """Delete all rows from dbo.Movies if data has already been loaded."""\

    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.table(table_name)
    table.delete()



if __name__ == "__main__":

    create_movie_table(table_name)

    load_data(json_file)

    movies = query_movies(2013)
    for movie in movies:
        print(movie["year"], ":", movie["title"])
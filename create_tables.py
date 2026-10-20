# Import the boto3 library, the AWS SDK for Python
import boto3


# Define a function that creates a DynamoDB table; table_name is the name you want to give it
def create_movie_table(table_name):

    # Create a low-level DynamoDB client; region_name says which AWS region to talk to
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    # Ask DynamoDB to create the table; the reply (a dictionary) is stored in response
    response = dynamodb.create_table(
        
        # The name of the new table, taken from the function argument
        TableName=table_name,
        
        # KeySchema defines which attributes make up the table's primary key
        KeySchema=[
            # 'year' is the partition key: DynamoDB uses it to decide where data is stored
            {"AttributeName": "year", "KeyType": "HASH"},    # Partition key
            # 'title' is the sort key: items with the same year are ordered by title
            {"AttributeName": "title", "KeyType": "RANGE"},  # Sort key
        ],
        
        # AttributeDefinitions declares the data types of the key attributes only
        AttributeDefinitions=[
            # 'year' is a Number ("N")
            {"AttributeName": "year", "AttributeType": "N"},
            # 'title' is a String ("S")
            {"AttributeName": "title", "AttributeType": "S"},
        ],
        # ProvisionedThroughput reserves a fixed amount of read/write capacity (billed hourly)
        ProvisionedThroughput={
            # Up to 10 strongly consistent reads per second (4 KB each)
            "ReadCapacityUnits": 10,
            # Up to 10 writes per second (1 KB each)
            "WriteCapacityUnits": 10,
        },
    )  # End of the create_table call

    # Print the status DynamoDB reports right after creation (normally "CREATING")
    print("Table status:", response["TableDescription"]["TableStatus"])

    # Get a "waiter", a helper that polls AWS until the table exists and is ready, then pause until then
    dynamodb.get_waiter("table_exists").wait(TableName=table_name)
    # Confirm to the user that the table is ready to use
    print("Table is now ACTIVE")


# This block only runs when you execute the file directly (not when it is imported elsewhere)
if __name__ == "__main__":
    table_name = "Movies"
    # Call the function to create a table named "Movies"
    create_movie_table(table_name=table_name)
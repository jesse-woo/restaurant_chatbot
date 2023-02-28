import boto3
import json
from decimal import Decimal
# a script to read json records from a file and load them into dynamoDB

JSON = "yelp-restaurants.json"

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yelp-restaurants')


if __name__ == '__main__':

    with table.batch_writer() as batch:
        with open(JSON) as fp:
            Lines = fp.readlines()
            for line in Lines:
                data = json.loads(line, parse_float=Decimal)
                data["address"] = data["location"]['display_address']

                batch.put_item(Item=data)
                # print(data)

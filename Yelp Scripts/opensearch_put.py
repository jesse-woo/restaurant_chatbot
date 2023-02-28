import boto3
import requests
import json
from decimal import Decimal
# a script to read yelp restaurants in from file and put them into opensearch restaurants

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yelp-restaurants')
url = "https://search-restaurants-gqte3jllekfwqmmccsc5eglb74.us-east-1.es.amazonaws.com"
headers = {"Content-Type": "application/json"}
JSON = "yelp-restaurants.json"

if __name__ == "__main__":
    records = table.scan()
    num = 1

    with open(JSON) as fp:
        lines = fp.readlines()
        with open("yelp-opensearch.json", 'a') as outfile:
            for line in lines:
                record = json.loads(line, parse_float=Decimal)
                idx_str = '{"index": {"_index": "restaurants", "_id": %d}}' % num
                #idx = json.loads(idx_str)
                #json.dump(idx_str, outfile)
                outfile.write(idx_str)
                outfile.write("\n")
                to_write = {"restaurant_id": record['id'], "Cuisine": record['cuisine']}
                json.dump(to_write, outfile)
                outfile.write("\n")
                # req = requests.post(url, data=json.dumps(to_send).encode("utf-8"), headers=headers)
                num += 1

    print("num records written", num)
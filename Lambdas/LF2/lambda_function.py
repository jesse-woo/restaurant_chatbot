import json
import os
import boto3
import random
import operator
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from datetime import datetime
from time import time

REGION = 'us-east-1'
HOST = 'search-restaurants-gqte3jllekfwqmmccsc5eglb74.us-east-1.es.amazonaws.com'
INDEX = 'restaurants'
Q_URL = "https://sqs.us-east-1.amazonaws.com/438427517041/restaurant_queue"

session = boto3.Session()

    
def get_msg():
    sqs_client = boto3.client('sqs', region_name=REGION)
    
    q_rsp = sqs_client.receive_message(
        QueueUrl=Q_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )
    
    if "Messages" in q_rsp:
        msg = q_rsp['Messages'][0]
        msg_body = msg["Body"]
        msg_receipt_handle = msg['ReceiptHandle']
        sqs_client.delete_message(QueueUrl = Q_URL, ReceiptHandle=msg_receipt_handle)
        # make this a list
        return msg_body
    else:
        exit("No messages in the queue")

def query(term):
    q = {'size': 5, 'query': {'multi_match': {'query': term}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)
    print(res)

    hits = res['hits']['hits']
    results = []
    for hit in hits:
        results.append(hit['_source']['restaurant'])

    return results


def get_awsauth(region, service):
    cred = session.get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)
                    
                    
def parse_dynamo(rest):
    # json_result = {"restaurants": []}
    
    addr_line1 = str(rest['address']["L"][0]["S"])
    addr_line2 = str(rest['address']["L"][1]["S"])
    addr_full = addr_line1 + "\n" + addr_line2
    rest_name = str(rest['name']["S"])
    rating = str(rest["rating"]["N"])
    rev_cnt = str(rest["review_count"]["N"])
    
    res = {"address": addr_full, "name": rest_name, "rating": rating, "review count": rev_cnt}
    # json_result["restaurants"].append(res)
    # return res or json_result?
    return res
                    
                    
def format_email(dyno_json, msg):
    address = dyno_json["address"]
    rest_name = dyno_json["name"]
    rating = dyno_json["rating"]
    review_count = dyno_json["review count"]
    email = ""
    email += ("Hi,\nHere is the suggestion from Chatbot Concierge for a " 
    + str(msg['cuisine'].capitalize()) 
    + " restaurant suitable for " + str(msg["party_size"]) + " people,"
    + " on " + str(msg["date"]) + " at " + str(msg["time"]) + '.\n\n'
    + rest_name +"\n"
    + "address:\n"
    + address + "\n"
    + "it's Yelp rating is " + rating + ", and it has " + review_count + " reviews."
    + "\n\nThank you,\nPlease use Chatbot Concierge again.")
    
    return email
                    
def dynamodb_lookup(id):
    dynamodb = session.client('dynamodb')
    response = dynamodb.get_item(
        TableName='yelp-restaurants',
        Key={
            'id': {
                'S' : id
            }
        },
        ProjectionExpression='#restaurantName, #restaurantLocation, phone, price, rating, review_count',
        ExpressionAttributeNames={
            "#restaurantName": "name",
            "#restaurantLocation": "address"
        }
    )
    return parse_dynamo(response['Item'])
    

def lambda_handler(event, context):
    ses_client = session.client('ses')
    
    while True:
        
        try:
            message = json.loads(get_msg())
            # print("the message is", message)
            cuisine = message['cuisine']
            restaurant_ids = query(cuisine)
            #restaurant_ids = query('chinese')
            
            recommendations = []
            #for result in results, check dynamo and give more details on the restaurant
            rand_idx = random.randrange(0,5)
            '''
            for id in restaurant_ids:
                recommendations.append(dynamodb_lookup(id))
            '''
            recommendation = dynamodb_lookup(restaurant_ids[rand_idx])
        
            #print("recommendation is", recommendation)
            
            to_send = format_email(recommendation, message)
            print("email is", to_send)
            
            res = ses_client.send_email(
                        Source="jw4202@columbia.edu",
                        Destination={"ToAddresses": [message['email']]},
                        Message={
                            "Subject": {"Data": "Restaurant recommendation from Chatbot Concierge"},
                            "Body": {
                                "Text": {
                                    "Data": to_send
                                }
                            },
                        },
            )
        
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*',
                },
                # 'body': json.dumps({'results': restaurant_ids})
                'body': json.dumps({'results': recommendation})
            }
        
        except Exception as e:
            print(e)
            return {
                'statusCode' : 666,
                'body': json.dumps('Something went wrong fuck you')
            }
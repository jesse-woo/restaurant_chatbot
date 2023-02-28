Jesse Woo, jw4202@columbia.edu
No partner

chatbot url: https://s3.amazonaws.com/coms6998-006-hw1-jw4202.com/chat.html

Chatbot to give restaurant recommendations using AWS Lex, Opensearch, and
DynamoDB, along with various helper functions and modules.

Yelp Scripts file contains a notebook used to download and format data 
from the yelp API, along with the data in a JSON format and a format
readable by opensearch. yelp_put.py sends JSON formatted data to DynamoDB,
whereas opensearch_put.py sends indices to opensearch. 
# pip install boto3
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from decouple import config

def create_table(dynamodb, date):
    '''
    table이 생성되는데 시간이 꽤 소요됨
    table 생성하는 동안 크롤링하고 요약하면 될듯함.
    '''
    table = dynamodb.create_table(
        TableName = date,
        KeySchema = [
            {
                'AttributeName': 'keyword',
                'KeyType': 'HASH' # Partition key
            },
            {
                'AttributeName': 'newstitle',
                'KeyType': 'RANGE' # Sort key
            }
        ],
        AttributeDefinitions = [
            {
                'AttributeName': 'keyword',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'newstitle',
                'AttributeType': 'S'
            }
        ],
        BillingMode = 'PAY_PER_REQUEST'
    )

    return table

def put_news(table, keyword, title, article):
    response = table.put_item(
        Item = {
            'keyword': keyword,
            'newstitle': title,
            'article': article
        }
    )

    return response

def get_news(table, keyword):
    response = table.query(
        KeyConditionExpression = Key('keyword').eq(keyword)
    )

    return response

if __name__=="__main__":
    AWS_ACCESS_KEY_ID     = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    REGION_NAME           = config("REGION_NAME")

    dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = REGION_NAME
)
    # response = create_table(dynamodb, "2022-03-31")

    table = dynamodb.Table("2022-03-31")
    # response = put_news(table, "손흥민", "손흥민넣었음", "블라블라")
    # print(response['ResponseMetadata']['HTTPStatusCode'])

    # response = put_news(table, "손흥민", "넣었음", "블라블라")
    # print(response['ResponseMetadata']['HTTPStatusCode'])

    response = get_news(table, '손흥민')
    print(response['ResponseMetadata']['HTTPStatusCode'])
    # print(response['Item']['keyword'])
    # print(response['Item']['newstitle'])
    # print(response['Item']['article'])
    if len(response['Items']) != 0:
        print(response['Items'])

    response = get_news(table, '유재석')
    print(response['ResponseMetadata']['HTTPStatusCode'])
    if len(response['Items']) != 0:
        print(response['Items'])

    table = dynamodb.Table("2022-03")
    print(table.table_status)
from datetime import datetime, timedelta
from textwrap import dedent

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.hooks.S3_hook import S3Hook

default_args = {"start_date": datetime(2021, 1, 1)}


def _read_keywords(**kwargs):
    """
    MysqlConnection을 이용, 키워드 리스트를 가져온다.
    output = [keyword1, keyword2 ..]
    """
    sql = "SELECT keyword FROM keyword_table"
    curs = MySqlHook(mysql_conn_id="get_keywords").get_conn().cursor()
    curs.execute(sql)
    keywords = [i[0] for i in list(curs.fetchall())]
    return ["손흥민", "우크라이나"]  # keywords  # [keyword1, keyword2...]


def _request_news_url_API(**kwargs):
    """
    mySQL로부터 받아온 키워드 리스트[keyword1, keywor2..]에서 title과 link 가져오기
    Input: 키워드리스트 [] (mysql)
    Output:{
        keyword1{
            title1: link1,
            title2: link2,
            ..
        },
        keyword2{
            title1: link1,
            title2: link2,
            ..
        },
        ..
    }
    """
    import requests

    ti = kwargs["ti"]

    # get keywords list
    keywords = ti.xcom_pull(task_ids="read_keywords")

    class naverNews:
        def __init__(self, client_id, client_secret, num_display, type_sort="sim"):
            self.client_id = client_id
            self.client_secret = client_secret
            self.num_display = num_display  # default: 10
            self.sort_type = type_sort  # default: date

        # 기사제목의 html 태그 제거
        def remove_tag(self, title):
            control_character = ["<b>", "</b>", "&quot"]
            for cc in control_character:
                title = title.replace(cc, "")
            return title

        def get_url(self, keyword):

            """
            네이버 api를 이용해 기사 제목과 해당 기사 url 받아오기
            Input: 키워드 (사용자 입력)
            Output: {기사제목: url}
            """
            url = "https://openapi.naver.com/v1/search/news.json"

            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            }

            params = {
                "query": keyword,
                "display": self.num_display,
                "start": 1,
                "sort": self.sort_type,
            }

            respond = requests.get(url, params=params, headers=headers)

            full_article = {}  # "title": news_link

            if respond.status_code == 200:
                for news in respond.json()["items"]:
                    news["title"] = self.remove_tag(news["title"])
                    full_article[news["title"]] = news["link"]
                return full_article
            else:
                raise Exception(f"네이버 API 요청 실패: {respond.status_code}")

    naver = naverNews("D6Zkh_3UA5nBd8rZaF5y", "mQh_izoDfa", 3, "sim")

    keywords_article_links = {}
    for keyword in keywords:
        keywords_article_links[keyword] = naver.get_url(keyword)

    return keywords_article_links  # structure : {keyword1:{title:link..},keyword2:{title:link..}..}


def _crawling_article(**kwargs):
    """
    link에 있는 기사를 크롤링해서 본문 내용을 가져온다.
    Input:{
        keyword1{
            title1: link1,
            title2: link2,
            ..
        },
        keyword2{
            title1: link1,
            title2: link2,
            ..
        },
        ..
    }
    Output:{
        keyword1{
            title1: content1,
            title2: content2,
            ..
        },
        keyword2{
            title1: content1,
            title2: content2,
            ..
        },
        ..
    }
    """

    import requests
    import pickle
    import subprocess
    import sys

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "bs4"])
    finally:
        from bs4 import BeautifulSoup
    ti = kwargs["ti"]

    keywords_article_links = ti.xcom_pull(task_ids="request_news_url_API")

    div_list = ["div#articleBodyContents", "div#newsEndContents", "div#articeBody"]

    for keyword, article_link in keywords_article_links.items():
        for title in article_link.keys():
            url = article_link[title]
            respond = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

            if respond.status_code == 200:
                html = BeautifulSoup(respond.text, features="html.parser")
                for div in div_list:
                    try:
                        article = html.select_one(div).text.strip()
                        break
                    except:
                        pass
                keywords_article_links[keyword][title] = article
            else:
                raise Exception(f"네이버 기사 크롤링 실패: {respond.status_code}")

    with open(file="/opt/airflow/dags/temp/temp.pickle", mode="wb") as f:
        pickle.dump(keywords_article_links, f, pickle.HIGHEST_PROTOCOL)
        # structure : {keyword1:{title:content..},keyword2:{title:content..}..}

    return keywords_article_links


def _contents_local_to_s3(**kwargs):
    import pickle

    ds = kwargs["ds_nodash"]
    bucket = "keywords-contents"
    s3_hook = S3Hook(aws_conn_id="s3_conn")
    s3_hook.load_file(
        filename="/opt/airflow/dags/temp/temp.pickle",
        key=f"contents/{ds}.pickle",
        bucket_name=bucket,
        replace=True,
    )
    return


def _summarize_article(**kwargs):
    """
    content에 있는 기사를 요약해서 본문 내용을 가져온다.
    Input:{
        keyword1{
            title1: content1,
            title2: content2,
            ..
        },
        keyword2{
            title1: content1,
            title2: content2,
            ..
        },
        ..
    }
    Output:{
        keyword1{
            title1: content1_summarize,
            title2: content2_summarize,
            ..
        },
        keyword2{
            title1: content1_summarize,
            title2: content2_summarize,
            ..
        },
        ..
    }
    """
    import subprocess
    import sys
    import pickle

    try:
        import torch
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "torch"]
        )
    finally:
        import torch

    try:
        from transformers import PreTrainedTokenizerFast
        from transformers import BartForConditionalGeneration
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "transformers"])
    finally:
        from transformers import PreTrainedTokenizerFast
        from transformers import BartForConditionalGeneration
    
    
    ti = kwargs["ti"]
    keywords_article_contents = ti.xcom_pull(task_ids="crawling_article")
    
    # with open("/opt/airflow/dags/temp/temp.pickle","rb") as fr:
    #     keywords_article_contents = pickle.load(fr)
    

    tokenizer = PreTrainedTokenizerFast.from_pretrained("digit82/kobart-summarization")
    model = BartForConditionalGeneration.from_pretrained("digit82/kobart-summarization")

    for keyword, article_contents in keywords_article_contents.items():
        for title in article_contents.keys():
            content = article_contents[title].replace("\n", " ")
            
            try:
                raw_input_ids = tokenizer.encode(content)
                input_ids = (
                    [tokenizer.bos_token_id] + raw_input_ids + [tokenizer.eos_token_id]
                )
                summary_ids = model.generate(
                    torch.tensor([input_ids]), num_beams=4, max_length=512, eos_token_id=1
                )
    
                keywords_article_contents[keyword][title] = tokenizer.decode(
                    summary_ids.squeeze().tolist(), skip_special_tokens=True
                )
            except:
                keywords_article_contents[keyword][title] = "불건전 내용 검열"
                

    return keywords_article_contents

def _summarize_article_to_dynamodb(**kwargs):
    import env
    import boto3
    import time

    ti = kwargs["ti"]
    keywords_article_contents = ti.xcom_pull(task_ids="summarize_article")
    ds = kwargs["ds_nodash"]
    
    def create_table(dynamodb, date):
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
    
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id = env.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = env.AWS_SECRET_ACCESS_KEY,
        region_name = env.REGION_NAME
    )
    
    client = boto3.client(
        'dynamodb',
        aws_access_key_id = env.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = env.AWS_SECRET_ACCESS_KEY,
        region_name = env.REGION_NAME)
    
    try:
        create_table(dynamodb, ds)
    except: # 에러네임 가져오기
        print("already table")
        
    
    waiter = client.get_waiter('table_exists')
    waiter.wait(
        TableName=ds,
        WaiterConfig={
            'Delay': 20,
            'MaxAttempts': 20
        }
    )

    table = dynamodb.Table(ds)
    
    for keyword, article_contents in keywords_article_contents.items():
        for title in article_contents.keys():
            put_news(table, keyword, title, article_contents[title])            
    
    return "f"
     
    

with DAG(
    "test",
    schedule_interval="@daily",
    start_date=datetime(2021, 1, 1),
    catchup=False,
) as dag:

    read_keywords = PythonOperator(
        task_id="read_keywords", python_callable=_read_keywords
    )

    request_news_url_API = PythonOperator(
        task_id="request_news_url_API", python_callable=_request_news_url_API
    )

    crawling_article = PythonOperator(
        task_id="crawling_article", python_callable=_crawling_article
    )
    
    contents_local_to_s3 = PythonOperator(
        task_id="contents_local_to_s3", python_callable=_contents_local_to_s3
    )

    summarize_article = PythonOperator(
        task_id="summarize_article", python_callable=_summarize_article
    )
    
    summarize_article_to_dynamodb = PythonOperator(
        task_id="summarize_article_to_dynamodb", python_callable = _summarize_article_to_dynamodb)


    
(
    read_keywords
    >> request_news_url_API
    >> crawling_article
    >> contents_local_to_s3
    >> summarize_article
    >> summarize_article_to_dynamodb
)

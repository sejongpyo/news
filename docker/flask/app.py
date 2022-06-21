from flask import Flask, request, jsonify
from decouple import config
import boto3

from naver_news import naverNews
import dynamodb_handler as dynamodb

app = Flask(__name__)

# naver api & crawling
client_id = config("NAVER_ID")
client_secret = config("NAVER_SECRET")
num_display = 3 # default: 10
type_sort = 'sim' # default: date
naver = naverNews(client_id, client_secret, num_display, type_sort)

# dynamodb
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id = config("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = config("AWS_SECRET_ACCESS_KEY"),
    region_name = config("REGION_NAME")
)

@app.route("/stream", methods=['POST'])
def get_():
    """
    동작원리
    1. 사용자가 텍스트 입력 시 카카오톡 서버에서 Flask 서버로 데이터 전달 (Json Format)
    2. Json Format으로 응답 전송
    """
    sample = request.get_json()

    respond = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": 'hi'
                        }
                    }
                ]
            }
        }
    return jsonify(respond)

    talk = req[''] # 유저 입력값

    # naver new api 호출해서 뉴스 검색
    # naver_news = naver.crawl_full(talk)

    # naver news 정상 작동 시
    if naver_news['status_code'] == 200:
        respond = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": naver_news['description']
                        }
                    }
                ]
            }
        }
        return jsonify(respond)
    else:
        respond = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "키워드를 다시 입력하세요."
                        }
                    }
                ]
            }
        }
        return jsonify(respond)

if __name__=="__main__":
    app.run(host='0.0.0.0', port = 8080, debug=True)
import os
import sys
import requests
from bs4 import BeautifulSoup
import json

import torch
from transformers import PreTrainedTokenizerFast
from transformers import BartForConditionalGeneration


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

        full_article = {}  # "title": full article

        if respond.status_code == 200:
            for news in respond.json()["items"]:
                news["title"] = self.remove_tag(news["title"])
                full_article[news["title"]] = news["link"]
            return full_article
        else:
            raise Exception(f"네이버 API 요청 실패: {respond.status_code}")

    def summarizer(self, text):
        tokenizer = PreTrainedTokenizerFast.from_pretrained(
            "digit82/kobart-summarization"
        )
        model = BartForConditionalGeneration.from_pretrained(
            "digit82/kobart-summarization"
        )

        text = text.replace("\n", " ")

        raw_input_ids = tokenizer.encode(text)
        input_ids = [tokenizer.bos_token_id] + raw_input_ids + [tokenizer.eos_token_id]
        summary_ids = model.generate(
            torch.tensor([input_ids]), num_beams=4, max_length=512, eos_token_id=1
        )

        return tokenizer.decode(
            summary_ids.squeeze().tolist(), skip_special_tokens=True
        )

    def crawl_full(self, keyword):
        """
        get_url()로부터 받아온 {기사제목: url}에서 각각 기사 전체 내용 받아오기
        Input: 키워드 (사용자 입력)
        Output: {기사제목: 기사내용}
        """
        div_list = ["div#articleBodyContents", "div#newsEndContents", "div#articeBody"]
        full_article = self.get_url(keyword)
        print(full_article)
        for title in full_article.keys():
            url = full_article[title]
            respond = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

            if respond.status_code == 200:
                html = BeautifulSoup(respond.text, features="html.parser")
                for div in div_list:
                    try:
                        article = html.select_one(div).text.strip()
                        break
                    except:
                        pass
                full_article[title] = self.summarizer(article)

            else:
                raise Exception(f"네이버 기사 크롤링 실패: {respond.status_code}")

        return full_article


if __name__ == "__main__":
    naver = naverNews("D6Zkh_3UA5nBd8rZaF5y", "mQh_izoDfa", 3, "sim")
    info = naver.crawl_full(input("키워드 : "))

    # _data.json 파일에 딕셔너리 형태로 info 저장
    with open("data.json", "w") as f:
        json.dump(info, f, indent="\t")

    # 저장 된 _data.json 파일을 읽어오기.
    with open("data.json", "r") as f:
        data = json.load(f)

    # json.dumps 이용해서 data를 들여쓰기 4칸 , 한글로 표현되도록 출력
    jsonfile = json.dumps(data, indent=4, ensure_ascii=False)



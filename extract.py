import requests
import json
from datetime import datetime

def extract(slot_at):
    url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"

    response = requests.get(url)

    collected_at = datetime.now() #현재 시각

    print(collected_at)

    data = response.json()

    file_path = "data.json"

    with open(file_path,"w",encoding="utf-8") as f: #데이터 저장
        json.dump(data, f)

    return data,collected_at
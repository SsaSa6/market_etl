import requests
from datetime import datetime

def extract():
    url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"

    response = requests.get(url)

    collected_at = datetime.now()

    if response.status_code != 200:
        print("요청 실패")
    else:
        print("요청 성공")

    data = response.json()

    return data,collected_at
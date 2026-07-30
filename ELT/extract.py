import requests
from datetime import datetime

def extract():
    url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"

    response = requests.get(url)

    collected_at = datetime.now() #현재 시각

    data = response.json()

    return data,collected_at
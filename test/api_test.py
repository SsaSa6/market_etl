import requests
import copy
from datetime import datetime

def pairs_extract():
    url = "https://api.upbit.com/v1/market/all"

    params = {
        "is_details": "true"
    }
    response = requests.get(url, params=params)
    markets = response.json()

    data = next(
        item for item in markets
        if item["market"] == "KRW-BTC"
    )
    collected_at = datetime.now()
    print(data)

    return data,collected_at

def pairs_load(data,collected_at):
    data[0]["collected_at"] = collected_at
pairs_load(pairs_extract)
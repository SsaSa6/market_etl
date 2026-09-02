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
    ls = [] #패킹용 리스트
    ls.append(data)
    ls.append(collected_at)
    return ls

def pairs_load(ls):
    data = ls #언패킹
    collected_at = ls[1]
    data[0]["collected_at"] = collected_at #collected_at 추가
    #print(data[0])

    data[0]["event_warning"] = ""
    data[0]["event_caution_price_fluctuations"] = ""
    data[0]["event_caution_trading_volume_soaring"] = ""
    data[0]["event_caution_deposit_amount_soaring"] =  ""
    data[0]["event_caution_global_price_differences"] = ""
    data[0]["event_caution_concentration_of_small_accounts"] = ""

    print(data[0]["market_event"]["caution"]["PRICE_FLUCTUATIONS"])

    caution_list = ["event_caution_price_fluctuations",
                    "event_caution_trading_volume_soaring",
                    "event_caution_deposit_amount_soaring",
                    "event_caution_global_price_differences",
                    "event_caution_concentration_of_small_accounts"]

    list_num = 0

    for keys in data[0]["market_event"]["caution"].keys():
        if data[0]["market_event"]["caution"][keys] == False:
            data[0][caution_list[list_num]] = "False"
        else:
            data[0][caution_list[list_num]] = "True"
        list_num = list_num + 1

    if(data[0]["market_event"]["caution"]==True):
        data[0]["market_event"]["caution"] = "True"
    else:
        data[0]["caution"] = "False"

    if(data[0]["market_event"]["warning"] == True):
        data[0]["event_warning"] = "True"
    else:
        data[0]["event_warning"] = "False"

    if(data[0]["market_event"]["warning"] == True or data[0]["market_event"]["caution"] == True):
        data[0]["market_event"] = "True"
    else:
        data[0]["market_event"] = "False"

    print(data[0])
    

pairs_load(pairs_extract())


import requests
import json
url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"

response = requests.get(url)

data = response.json()

file_path = "data.json"

with open(file_path,"w",encoding="utf") as f:
    json.dump(data, f)
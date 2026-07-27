import requests
import json
url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"

response = requests.get(url)

print(response.json())
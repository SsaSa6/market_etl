import requests
from datetime import datetime

def ticket_extract():
    url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
    try:
        response = requests.get(url)
        response.raise_for_status()
        collected_at = datetime.now()
        
        if response.status_code != 200:
                print("요청 실패")
        else:
                print("요청 성공")
        
        data = response.json()
        print("실행 성공")
        return data,collected_at

    except requests.exceptions.Timeout as e: #네트워크 지연과 같은 오류면
        print(f"오류가 난 이유는 : {e}")
    except requests.exceptions.HTTPError as e: #Http 오류면
        print(f"오류가 난 이유는 : {e}")
    except requests.exceptions.RequestException as e: #그 외 기타면
        print(f"오류가 난 이유는 : {e}")
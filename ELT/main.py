from datetime import datetime
import extract
import load

def main():
    slot_at = datetime.now().replace(second=0,microsecond=0)
    data,collected_at = extract.ticker_extract() #data랑 collected_at을 반환

    load.ticker_load(data,collected_at,slot_at)

if __name__ == "__main__":
    main()
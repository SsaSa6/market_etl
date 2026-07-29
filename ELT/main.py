from datetime import datetime
import ETL.extract as extract

def main():
    slot_at = datetime.now().replace(second=0,microsecond=0)
    data,collected_at = extract.extract() #data랑 collected_at을 반환

if __name__ == "__main__":
    main()
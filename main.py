from datetime import datetime
import extract

slot_at = datetime.now().replace(second=0,microsecond=0)

def main():
    extract.extract(slot_at=slot_at) #data랑 collected_at을 반환

if __name__ == "__main__":
    main()
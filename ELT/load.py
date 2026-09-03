import db
import copy

def ticker_load(data,collected_at,slot_at):
    conn = db.get_connection() #서버연동

    change_dict = {"change": "changer", "timestamp": "time_stamp"} #키와 컬럼

    data_copy = copy.deepcopy(data) #원본 보존

    with conn:
        with conn.cursor() as cursor: #cursor 키기
            data_copy[0]["slot_at"] = slot_at   #slot_at,collected_at 추가
            data_copy[0]["collected_at"] = collected_at

            for key,items in change_dict.items(): #키를 컬럼과 같게 변경
                 data_copy[0][f"{items}"] = data_copy[0][f"{key}"]

            del data_copy[0]["change"] #남은 키 삭제
            del data_copy[0]["timestamp"]
            
            test = []
            columns = []

            for key in data_copy[0]:
                    columns.append(key)
                    test.append(data_copy[0][key])

            columns = ','.join(columns)

            values = test

            values_sum = []

            for i in range(0,len(data_copy[0])):
                 values_sum.append("%s")

            values_sum = ','.join(values_sum)

            insert_sql = f"INSERT INTO Market_Ticker ({columns}) VALUES ({values_sum}) ON DUPLICATE KEY UPDATE market = market"

            cursor.execute(insert_sql,values) #sql 실행

            conn.commit()
            print("적재 성공")

def pairs_load(data,collected_at):
     conn = db.get_connection()

     data_copy = copy.deepcopy(data)

     with conn:
          with conn.cursor() as cousor:
               pass



            

            


    
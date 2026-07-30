import db
import copy

def load(data,collected_at,slot_at):
    conn = db.get_connection()

    change_dict = {"change": "changer", "timestamp": "time_stamp"}

    data_copy = copy.deepcopy(data)

    with conn:
        with conn.cursor() as cursor:
            data_copy[0]["slot_at"] = slot_at
            data_copy[0]["collected_at"] = collected_at

            for key,items in change_dict.items():
                 data_copy[0][f"{items}"] = data_copy[0][f"{key}"]

            del data_copy[0]["change"]
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

            insert_sql = f"INSERT INTO data_set ({columns}) VALUES ({values_sum})"

            print(data_copy)

            cursor.execute(insert_sql,values) #sql 실행

            conn.commit()

            

            


    
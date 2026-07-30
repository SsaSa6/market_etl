import db

def load(data,collected_at,slot_at):
    conn = db.get_connection()

    with conn:
        with conn.cursor() as cursor:
            data[0]["slot_at"] = slot_at
            data[0]["collected_at"] = collected_at
            
            insert_sql = f"INSERT INTO data_set (market,slot_at,collected_at) VALUES (%s,%s,%s)"
            values = (data[0]["market"],slot_at,collected_at)

            cursor.execute(insert_sql,values)

            conn.commit()

            

            


    
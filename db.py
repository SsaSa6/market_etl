import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("local"),
    user=os.getenv("user"),
    passwd=os.getenv("passwd"),
    db=os.getenv("database"),
    charset="utf8"
)

cousur = conn.cursor()

sql = """select market from data_set"""

cousur.execute(sql)

result = cousur.fetchone()

print(result)
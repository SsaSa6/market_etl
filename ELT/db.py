import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():

    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("MYSQL_USER"),
        passwd=os.getenv("MYSQL_ROOT_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("DB_PORT")),
        charset="utf8"
    )
    return conn
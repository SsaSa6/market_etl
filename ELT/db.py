import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():

    conn = pymysql.connect(
        host=os.getenv("local"),
        user=os.getenv("user"),
        passwd=os.getenv("passwd"),
        db=os.getenv("database"),
        charset="utf8"
    )
    return conn
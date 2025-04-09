import psycopg2
import os
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    connection = psycopg2.connect(
        host='localhost',
        database='anime_blog',
        user=os.getenv('POSTGRES_USERNAME'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    return connection
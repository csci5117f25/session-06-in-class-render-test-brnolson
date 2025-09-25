import os
from contextlib import contextmanager
from flask import Flask, render_template, request, redirect
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

pool = None

def setup():
    global pool
    DATABASE_URL = os.environ['DATABASE_URL']
    pool = ThreadedConnectionPool(1, 10, dsn=DATABASE_URL, sslmode='require')

@contextmanager
def get_db_connection():
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)

@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as connection:
      cursor = connection.cursor(cursor_factory=DictCursor)
      # cursor = connection.cursor()
      try:
          yield cursor
          if commit:
              connection.commit()
      finally:
          cursor.close()

def add_guest(name):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO guestbook_entries (name) VALUES (%s)",
            (name,)
        )

def get_guests():
    retval = []
    with get_db_cursor(False) as cursor:
        cursor.execute("SELECT * from guestbook_entries")
        for row in cursor:
            retval.append({"name": row['name']})
    return retval

@app.route('/')
def index():
    guests = get_guests()
    return render_template('hello.html', guests=guests)

@app.post('/submit')
def submit():
    name = request.form.get("guest-name")
    if name:
        add_guest(name)
    return redirect('/')

setup()
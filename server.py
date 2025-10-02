import os
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from flask import url_for

from contextlib import contextmanager
from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from dotenv import load_dotenv


app = Flask(__name__)
app.secret_key = env.get("FLASK_SECRET")

### Auth0 setup

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

###

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
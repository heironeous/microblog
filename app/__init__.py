
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(obj=Config)

db = SQLAlchemy(app=app)
migrate = Migrate(app=app, db=db)

login = LoginManager(app=app)
login.login_view = 'login'

from app import routes, models
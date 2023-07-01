# Run a test server.
from app import app

#app.run()
if __name__ == "__main__":
    app.run()




'''
from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config.DevelopmentConfig")

db = SQLAlchemy(app)

# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_entry")
def add_entry():
    return render_template("add_entry.html")

if __name__ == "__main__":
    db.create_all()
    app.run()

'''
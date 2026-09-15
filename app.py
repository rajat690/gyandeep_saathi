from flask import Flask
app = Flask(__name__)

@app.get("/")
def health():
    return "Gyandeep Saathi is running", 200
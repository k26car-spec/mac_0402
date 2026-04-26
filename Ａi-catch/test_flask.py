#!/usr/bin/env python3
# test_flask.py - 測試 Flask 是否正常

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"Error: {e}"

@app.route('/test')
def test():
    return "Flask is working!"

if __name__ == '__main__':
    import os
    print(f"Templates folder exists: {os.path.exists('templates')}")
    print(f"dashboard.html exists: {os.path.exists('templates/dashboard.html')}")
    print("\nStarting Flask...")
    app.run(host='127.0.0.1', port=8080, debug=False)

#!/bin/bash

# Step 1: Install requirements
pip install -r requirements.txt

# Step 2: Upgrade pip
python.exe -m pip install --upgrade pip

export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export SECRET
export DATABASE_URL=sqlite:///db_directory/testdb.sqlite3

flask run


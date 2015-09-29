# -*- coding: utf-8 -*-
"""
    VPNGater
    ~~~~~~
    A simple list of vpn from vpngate.
    Unsafe.
    :copyright: (c) 2015 by Aldo Ridhoni.
    :license: GPL2.
"""
import sqlite3, sys, csv, urllib2, base64, os
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing

# configuration
DATABASE = 'vpngate.db'
DEBUG = False
SECRET_KEY='development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# DB connection function
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def multi_insert_db(table, values):
    d = get_db()
    for item in values:
        if item:
            keys = ', '.join(f for f, v in item.iteritems())
            vals = ', '.join("'" + v + "'" for f, v in item.iteritems())
            # d.execute("INSERT INTO ? (?) VALUES (?);", [table, keys, vals]) # error
            query = "INSERT INTO %s (%s) VALUES (%s);" % (table, keys, vals)
            d.execute(query)
    d.commit()



@app.before_request
def before_request():
    g.db = connect_db()

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = connect_db()
    return db

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# Req functions
def strip(file):
    output = ''
    string = file.split('\n')
    for line in string:
        li = line.strip()
        if not li.startswith('#') and line.strip() != '':
            output += line.rstrip() + "\n"
    return output

# View functions
@app.route("/")
def index_list():
    lists = query_db('SELECT * FROM vpnlist LIMIT 30')
    if lists is None:
        return 'No such data'
    else:
        return render_template('index.html', lists=lists)

@app.route("/reload")
def reload():
    db = get_db()
    db.execute("DELETE FROM vpnlist;")
    db.execute("DELETE FROM sqlite_sequence WHERE name = 'vpnlist';")
    db.commit()
    # Get the csv file from vpngate
    try:
        try:
            response = urllib2.urlopen("http://www.vpngate.net/api/iphone", None, 30)
        except URLError, e:
            return e
        except socket.timeout:
            return 'timeout'
        #response = open('iphone.csv', 'rb')
        reader = csv.reader(response)
        next(reader) # skip junk
        next(reader) # skip header

        values = []
        for row in reader:
            if len(row) >=2 :
                values.append({"hostname": row[0], "ip": row[1], "speed": row[2], "country": row[5], "config_data": row[14]})

        multi_insert_db('vpnlist', values)
        return redirect(url_for('index_list'))

    except urllib2.URLError:
        return 'Something is wrong'

@app.route("/download/<int:list_id>")
def download(list_id):
    try :
        result = query_db('SELECT * FROM vpnlist WHERE id = ?;', [list_id], one=True)
        decoded = strip(base64.b64decode(result['config_data']))
        flash("File config is successfully downloaded")
        headers = {"Content-Type": "application/x-openvpn-profile",
                   "Content-disposition": "attachment; filename=vpngate_%s.ovpn" % (result['hostname']),
                   "Location": "/"};
        return decoded, 200, headers
    except IndexError, TypeError:
        flash("File not found")
    return redirect(url_for('index_list'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ['PORT']))

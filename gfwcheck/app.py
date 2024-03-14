import json
import time
from flask import Flask
from markupsafe import escape
from ping3 import ping
from tcping import Ping
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)


@app.route('/checkip/<name>')
def checkip(name):
    res = []
    rangeCount = 60
    for i in range(rangeCount):
        ms = ping(escape(name), unit='ms', timeout=1)
        res.append(ms)
    isblock = False
    if res.count(None) / rangeCount > 0.55:
        isblock = True
    resp = {
        "isblock": isblock,
        "source": str(res.count(None)) + "/" + str(rangeCount)
    }

    return json.dumps(resp)


# @app.route('/checktcp/<name>')
# def checktcp(name):
#     start = time.time()
#     ips = escape(name).split(":")
#     rangeCount = 15
#     timeout=1.5
#     ping = Ping(ips[0], ips[1], timeout)
#
#     for i in range(rangeCount):
#         try:
#             ping.ping(1)
#         except Exception as err:
#             print(err)
#     count = ping.__dict__["_successed"]
#     isblock = True
#     if count / rangeCount >= 0.1:
#         isblock = False
#     resp = {
#         "isblock": isblock,
#         "count": str(count) + "/" + str(rangeCount),
#         "conn_times": ping.__dict__["_conn_times"],
#         "use_conn_time": sum(ping.__dict__["_conn_times"]) / 1000,
#         "source": count / rangeCount,
#         "all_time": time.time() - start
#     }
#
#
#     return json.dumps(resp)
def action(ping):
    try:
        ping.ping(1)
    except Exception as err:
        print(err)
@app.route('/checktcp/<name>')
def checktcp(name):

    rangeCount = 60
    start = time.time()
    ips = escape(name).split(":")
    timeout = 1.5
    ping = Ping(ips[0], ips[1], timeout)
    all_task = []
    max_workers=32
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for second in range(rangeCount):
            all_task.append(pool.submit(action, ping))

    count = ping.__dict__["_successed"]
    isblock = True
    if count / rangeCount >= 0.1:
        isblock = False
    resp = {
        "isblock": isblock,
        "count": str(count) + "/" + str(rangeCount),
        "conn_times": ping.__dict__["_conn_times"],
        "use_conn_time": sum(ping.__dict__["_conn_times"]) / 1000,
        "source": count / rangeCount,
        "all_time": time.time() - start
    }

    return json.dumps(resp)




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
# gunicorn app:app -c gunicorn.conf.py

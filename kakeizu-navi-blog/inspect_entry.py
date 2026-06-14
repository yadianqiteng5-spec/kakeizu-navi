import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_to_livedoor import wsse_header, load_config
from urllib import request
uid, key, blog = load_config()
url = sys.argv[1]
req = request.Request(url, method="GET")
req.add_header("X-WSSE", wsse_header(uid, key))
req.add_header("Authorization", 'WSSE profile="UsernameToken"')
with request.urlopen(req, timeout=30) as r:
    xml = r.read().decode("utf-8")
import re
for tag in ["published","updated","issued","app:edited"]:
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), xml)
    print(tag, "=", m.group(1) if m else "(なし)")

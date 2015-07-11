import requests
import json
import sys
import os
from hashlib import sha1
import time
import pickle


class JsonRPCClient(object):
    def __init__(self, host, port=8080, user="", password="", cache_duration=60*60*24):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.cache_duration = cache_duration

        self.cache_path = os.path.dirname(os.path.realpath(__file__))+"/tmp"
        try:
            os.mkdir(self.cache_path)
        except:
            pass


    def _get_cache_key(self, command):
        # hashing a dict: http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
        return sha1(self.host+str(self.port)+json.dumps(command, sort_keys=True)).hexdigest()

    def _is_cached(self, key):
        path = os.path.join(self.cache_path, key)
        if os.path.isfile(path):
            if time.time() - os.path.getmtime(path) < self.cache_duration:
                return True
        return False

    def _set_cache(self, key, data):
        with open(os.path.join(self.cache_path, key), "wb") as f:
            pickle.dump(data, f)

    def _get_cache(self, key):
        with open(os.path.join(self.cache_path, key), "rb") as f:
            return pickle.load(f)

    def http_call(self, command):
        cache_key = self._get_cache_key(command)
        if not self._is_cached(cache_key):
            url = "http://%s:%d/jsonrpc"%(self.host,self.port)
            headers = {'content-type': 'application/json'}
            r = requests.post(
                url, data=json.dumps(command), headers=headers,
                auth=(self.user, self.password)
                )
            if r.status_code == 200:
                self._set_cache(cache_key, r.json())
            else:
                print("bad status")
                return None
        else:
            print "reusing cache"
        return self._get_cache(cache_key)





import urllib
import hashlib
import shutil
def download_image(url):
    # TODO we can get the image from here too:
    # http://192.168.178.37:8080/image/image://http%253a%252f%252fimage.tmdb.org%252ft%252fp%252foriginal%252fyVkU8L6HttPQlatFdI9bata7NX0.jpg

    name = hashlib.sha1(url).hexdigest()+url[-4:]
    path = os.path.join("images", name)
    if not os.path.exists(os.path.join("out",path)):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(os.path.join("out",path), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
    return path

def show_image(path, size=400):
    url = urllib.unquote(path[8:-1])
    if len(url) > 0:
        img_path = download_image(url)
        return '<img src="%s" width="%dpx" />' % (img_path,size)
    return ''


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("call it with %s host port [user] [pw]" % sys.argv[0])
        sys.exit()
    host = sys.argv[1]
    port = int(sys.argv[2])
    user = ""
    if len(sys.argv)>3:
        user = sys.argv[3]
    pw = ""
    if len(sys.argv)>4:
        pw = sys.argv[4]
    client = JsonRPCClient(host, port, user, pw)



    from pprint import pprint

    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'))
    env.globals.update(show_image=show_image)

    out_path = "out"

    template = env.get_template('index.html')
    output_from_parsed_template = template.render()
    with open(os.path.join(out_path, "index.html"), "wb") as fh:
        fh.write(output_from_parsed_template.encode("utf-8"))



    command = {"jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": [
                    "genre","plot","title","episode","year","rating","thumbnail","studio"],
                "limits": { "start": 1, "end": 100000, },
            },
            "id": 1}
    data = client.http_call(command)
    tvshows = data["result"]["tvshows"]
    #pprint(tvshows)

    template = env.get_template('tvshow_list.html')
    output_from_parsed_template = template.render(tvshows=tvshows)
    with open(os.path.join(out_path, "tvshows.html"), "wb") as fh:
        fh.write(output_from_parsed_template.encode("utf-8"))

    command = {"jsonrpc": "2.0",
            "method": "VideoLibrary.GetMovies",
            "params": {
                "properties": [
                    "genre","plot","title","year","rating","thumbnail","studio", ],
                "limits": { "start": 1, "end": 100000, },
            },
            "id": 1}
    data = client.http_call(command)
    movies = data["result"]["movies"]
    #pprint(movies)

    template = env.get_template('movie_list.html')
    output_from_parsed_template = template.render(movies=movies)
    with open(os.path.join(out_path, "movies.html"), "wb") as fh:
        fh.write(output_from_parsed_template.encode("utf-8"))

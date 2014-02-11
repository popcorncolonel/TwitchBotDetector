import requests
import json
import sys # for printing to stderr

MAX = 100
limit = str(MAX)
offset = str(0)

def removeNonAscii(s): return "".join([x if ord(x) < 128 else '?' for x in s])

r = requests.get('https://api.twitch.tv/kraken/games/top' +
                 '?limit=' + limit)
r.text
flag = 1
while flag: #jank bugfix - sometimes can't read json
    try:
        gamedata = r.json()
        flag = 0
    except:
        pass


def user_viewers(user):
    req = 0
    try: 
        req = requests.get("https://api.twitch.tv/kraken/streams/" + user)
    except:
        print ("bad error. retry?\n")
        pass
    if not req:
        print "infinite loop? check here."
    if (type(req) == int):
        print req
        print "wat. line 35 twitch_viewers"
    while (req.status_code != 200):
        print (str(req.status_code) + " viewerlist unavailable")
        req = requests.get("https://api.twitch.tv/kraken/streams/" + user)
    try:
        userdata = req.json()
    except ValueError:
        return user_viewers(user) #nope start over
    if (len(userdata.keys()) == 2):
        viewers = 0
        if (userdata['stream']): # if the streamer is offline, userdata returns null
            viewers = userdata['stream']['viewers']
        if (viewers == 0):
            print user + " appears to be offline!"
        return viewers
    else:
        print str(userdata['status']) + " " + userdata['message'] + " " + userdata['error']
        print user + " is not live right now, or the API is down."
        return 0


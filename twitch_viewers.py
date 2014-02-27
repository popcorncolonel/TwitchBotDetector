import requests
import json
import sys # for printing to stderr and restarting program

restart_on_failure = True #Be careful with this. "True" might result in a lot of repeated tweets.
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

def restart_program():
    python = sys.executable
    os.execl(python, python, * sys.argv)

#user_viewers: 
#   returns the number of viewers twitch.tv/user currently has. returns 0 if offline.
#user is a string representing http://www.twitch.tv/<user>
def user_viewers(user):
    global restart_on_failure
    req = 0
    try:
        req = requests.get("https://api.twitch.tv/kraken/streams/" + user)
    except:
        return user_viewers(user)
    if not req:
        print "infinite loop? check here."
    if (type(req) == int):
        print req
        print "wat. line 35 twitch_viewers"
    while (req.status_code != 200):
        print (str(req.status_code) + " viewerlist unavailable")
        try:
            req = requests.get("https://api.twitch.tv/kraken/streams/" + user)
        except:
            pass
        if (req.status_code == 422 and restart_on_failure):
            print "RESTARTING PROGRAM!!!!!!!!!!!!!!!!!!!!! 422 ERROR"
            restart_program()
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


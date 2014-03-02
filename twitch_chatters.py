import socket
import requests
import sys # for printing to stderr
from twitch_viewers import user_viewers, removeNonAscii
import handle_twitter
from get_exceptions import get_exceptions
from chat_count import chat_count

suspicious = []
confirmed = []

tweetmode = False #true if you want it to tweet, false if you don't
alternative_chatters_method = True  #True if you want to use faster but potentially unreliable
                                    #method of getting number of chatters for a user
user_threshold = 200   #initial necessity for confirmation
user_threshold_2 = 150 #once a streamer has been confirmed at 200 viewers, then they need to go
                       #below this threshold to be taken off
ratio_threshold = 0.16 #if false positives, lower this number. if false negatives, raise this number
expected_ratio = 0.7 #eventually tailor this to each game/channel. Tailoring to channel might be hard.

# these users are known to have small chat to viewer ratios for valid reasons
# example: chat disabled, or chat hosted not on the twitch site, or mainly viewed on 
#          front page of twitch
# type: array of strings: example: ["destiny", "scg_live"]
exceptions = get_exceptions()

#get_chatters2:
#   gets the number of chatters in user's Twitch chat, via chat_count
#   Essentially, chat_count is my experimental method that goes directly to 
#   a user's IRC channel and counts the viewers there. It is not yet proven to be 
#   correct 100% of the time.
#user is a string representing http://www.twitch.tv/<user>
def get_chatters2(user):
    chatters2 = 0
    try:
        chatters2 = chat_count(user)
    except socket.error as error:
        return get_chatters2(user)
    return chatters2

#user_chatters:
#   returns the number of chatters in user's Twitch chat
#user is a string representing http://www.twitch.tv/<user>
def user_chatters(user):
    chatters = 0
    chatters2 = 0
    req = requests.get("http://tmi.twitch.tv/group/user/" + user)
    if (alternative_chatters_method):
        chatters2 = get_chatters2(user)
        if (chatters2 > 1):
            return chatters2
    try:
        while (req.status_code != 200):
            chatters2 = get_chatters2(user)
            if (alternative_chatters_method):
                if (chatters2 > 1):
                    return chatters2
            print "----TMI error", req.status_code, 
            print "getting", user + " (module returned %d)-----" %chatters2
            req = requests.get("http://tmi.twitch.tv/group/user/" + user)
        try:
            chat_data = req.json()
        except ValueError:
            return user_chatters(user)
        chatters = chat_data['chatter_count']
    except TypeError:
        print "recursing, got some kinda error"
        return user_chatters(user)
    return chatters

#user_ratio:
#   returns the ratio of chatters to viewers in <user>'s channel
#user is a string representing http://www.twitch.tv/<user>
def user_ratio(user):
    exceptions = get_exceptions()
    if (user in exceptions):
        print user, "is alright :)"
        return 1
    chatters = user_chatters(user)
    chatters2 = get_chatters2(user)
    viewers = user_viewers(user)
    if (viewers != 0):
        ratio = float(chatters) / viewers
        print user + ": " + str(chatters) + " / " + str(viewers) + " = %0.3f" %ratio,
        print "(%d - %d)" %(chatters2, chatters),
        if (chatters != 0):
            diff = abs(chatters2 - chatters)
            error = (100 * (float(diff) / chatters)) #percent error 
        else:
            return 0
        if (error > 6):
            print " (%0.0f%% error)!" %error,
            if (error < 99 and diff > 10):
                print "!!!!!!!!!!!!!!!!!!!" #if my chatters module goes wrong, i want to notice it.
            else:
                print
        else:
            print
    else: 
        return 1 # user is offline
    return ratio

#game_ratio
#   returns the average chatter:viewer ratio for a certain game
#game is a string - game to search
def game_ratio(game):
    global tweetmode
    try:
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
    except:
        print "uh oh caught exception when connecting. try again. see game_ratio(game)."
        game_ratio(game)
    while (r.status_code != 200):
        print r.status_code, ", service unavailable"
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
    try:
        gamedata = r.json()
    except ValueError:
        print "could not decode json. recursing"
        return game_ratio(game)
#TODO make a dictionary with keys as the game titles and values as the average and count
    count = 0 # number of games checked
    avg = 0
    while ('streams' not in gamedata.keys()):
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
        while (r.status_code != 200):
            print r.status_code, ", service unavailable"
            r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
        try:
            gamedata = r.json()
        except ValueError:
            print "couldn't json; recursing"
            return game_ratio(game)
    if len(gamedata['streams']) > 0:
        for i in range(0, len(gamedata['streams'])):
            viewers =  gamedata['streams'][i]['viewers']
            if viewers < user_threshold:
                break

            user = gamedata['streams'][i]['channel']['name'].lower() 
            name = "http://www.twitch.tv/" + user

            ratio = -1
            ratio = user_ratio(user)
            if (ratio == 0):
                print "ratio is 0... abort program?"
            handle_twitter.send_tweet(user, ratio, game, viewers, tweetmode, 
                                      ratio_threshold, confirmed, suspicious)
            avg += ratio
            count += 1
    else:
        print "couldn't find " + game + " :("
        return 0
    if count != 0:
        avg /= count
    # for the game specified, go through all users more than <user_threshold> viewers, find ratio, average them
    return avg

#remove_offline:
#   removes users from the suspiciuos and confirmed lists if they are no longer botting
def remove_offline():
    flag = False
    for item in suspicious:
        name = item[0]
        originame = name[21:] #remove the http://www.twitch.tv/
        if (user_ratio(originame) > 0.35 or user_viewers(originame) < 150):
            print originame + " appears to have stopped botting! removing from suspicious list"
            suspicious.remove(item)

    for item in confirmed:
        if (len(confirmed)):
            flag = True
        name = item[0]
        originame = name[21:] #remove the http://www.twitch.tv/
        if (user_ratio(originame) > 0.35 or user_viewers(originame) < 150):
            print originame + " appears to have stopped botting! removing from confirmed list"
            confirmed.remove(item)
    if (flag):
        print
        print

#search_all_games:
#   loops through all the games via the Twitch API, checking for their average ratios
def search_all_games():
    try:
        topreq = requests.get("https://api.twitch.tv/kraken/games/top")
        while (topreq.status_code != 200):
            topreq = requests.get("https://api.twitch.tv/kraken/games/top")
        topdata = topreq.json()
    except ValueError:
        search_all_games()
    for i in range(0,len(topdata['top'])):
        game = removeNonAscii(topdata['top'][i]['game']['name'])
        print "__" + game + "__"
        ratio = game_ratio(game)
        print
        print "Average ratio for " + game + ": %0.3f" %ratio
        print
        print "We are suspicious of: "
        if (len(suspicious) == 0):
            print "No one :D"
        for item in suspicious:
            print "%0.3f:" %item[1], item[0]
        print
        print "We have confirmed: "
        if (len(confirmed) == 0):
            print "No one :D"
        for item in confirmed:
            print "%0.3f:" %item[1], item[0]
        print
        print "Total of " + str(len(suspicious) + len(confirmed)) + " botters"
        print
        print
    print "looping back around :D"

#main loop 
while True:
    search_all_games()
    remove_offline()


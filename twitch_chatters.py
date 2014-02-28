import socket
import requests
import sys # for printing to stderr
from twitch_viewers import user_viewers
from twitch_viewers import removeNonAscii
from twython import Twython
import tweepy
from time import gmtime, strftime
from get_passwords import get_passwords
from get_exceptions import get_exceptions
from chat_count import chat_count

#delete tweets if someone stopped streaming?
delete = 0
tweetmode = False #true if you want it to tweet, false if you don't
alternative_chatters_method = False #True if you want to use faster but potentially unreliable
                                    #method of getting number of chatters for a user

passes = get_passwords()

APP_KEY =            passes[0]
APP_SECRET =         passes[1]
OAUTH_TOKEN =        passes[2]
OAUTH_TOKEN_SECRET = passes[3]

twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

id = 0

auth = tweepy.OAuthHandler(APP_KEY, APP_SECRET)
auth.set_access_token(OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
api = tweepy.API(auth)

# these users are known to have small chat to viewer ratios for valid reasons
# example: chat disabled, or chat hosted not on the twitch site, or mainly viewed on front page of twitch
# type: array of strings: example ["destiny", "scg_live"]
exceptions = get_exceptions()

#user_chatters:
#   returns the number of chatters in user's Twitch chat
#user is a string representing http://www.twitch.tv/<user>
def user_chatters(user):
    chatters = 0
    chatters2 = 0
    req = requests.get("http://tmi.twitch.tv/group/user/" + user)
    if (alternative_chatters_method):
        try:
            chatters2 = chat_count(user)
        except socket.error as error:
            pass
        if (chatters2 > 1):
            return chatters2
    try:
        while (req.status_code != 200):
            print "----TMI error", req.status_code, 
            try:
                print "getting", user + " (module returned %d)-----" %chat_count(user)
            except socket.error as error:
                print "-----"
            req = requests.get("http://tmi.twitch.tv/group/user/" + user)
        try:
            chat_data = req.json()
        except ValueError:
            return user_chatters(user)
        chatters = chat_data['chatter_count']
    except TypeError:
        print "recursing, got some kinda error"
        return user_chatters(user)
    #my experimental method that goes directly to a user's IRC channel and counts the viewers there.
    #not yet proven to be correct.
    '''
    if (chatters > 0):
        try:
            chatters2 = chat_count(user)
        except socket.error as error:
            print "oh. error getting chatters via module"
            return user_chatters(user)
        if (chatters2 > 3):
            print "returning %d via module" %chatters2
            return chatters2
    '''
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
    while True:
        try:
            chatters2 = chat_count(user)
            break
        except socket.error as error:
            print "error getting chatters. o well. try again."
            pass
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

suspicious = []
confirmed = []
user_threshold = 200   #initial necessity for confirmation
user_threshold_2 = 150 #once a streamer has been confirmed at 200 viewers, then they need to go
                       #below this threshold to be taken off
ratio_threshold = 0.16 #if false positives, lower this number. if false negatives, raise this number
expected_ratio = 0.7 #eventually tailor this to each game/channel. Tailoring to channel might be hard.

#get_game_tweet:
#   tailors the name of the game (heh) to what is readable and short enough to tweet
#game is a string
def get_game_tweet(game):
    game_tweet = game.split(":")[0] #manually shorten the tweet, many of these by inspection
    if (game_tweet == "League of Legends"):
        game_tweet = "LoL"
    if (game_tweet == "Call of Duty" and len(game.split(":")) > 1):
        game_tweet = "CoD:" + game.split(":")[1] #CoD: Ghosts, CoD: Modern Warfare
    if (game_tweet == "Counter-Strike" and len(game.split(":")) > 1):
        game_tweet = "CS: " 
        for item in game.split(":")[1].split(" "): 
            if (len(item) > 0):
                game_tweet += item[0] #first initial - CS:S, CS:GO
    if (game_tweet == "StarCraft II" and len(game.split(":")) > 1):
        game_tweet = "SC2: "
        for item in game.split(":")[1].split(" "):
            if (len(item) > 0):
                game_tweet += item[0] #first initial - SC2: LotV
    return game_tweet

#send_tweet
#   if <user> is believed to be viewer botting, sends a tweet via the twitter module
#user is a string representing http://www.twitch.tv/<user>
#ratio is <user>'s chatter to viewer ratio
#game is the game they're playing (Unabbreviated: ex. Starcraft II: Heart of the Swarm
#viewers is how many viewers the person has - can be used to get number of chatters, with ratio
def send_tweet(user, ratio, game, viewers):
    global tweetmode
    name = "http://www.twitch.tv/" + user
    if (ratio < ratio_threshold):
        found = 0
        for item in confirmed:
            if item[0] == name:
                item[1] = ratio #update the ratio and game each time
                item[2] = game
        for item in suspicious:
            if item[0] == name:
                item[1] = ratio #update the ratio and game each time
                item[2] = game
                found = 1
        if found:
            suspicious.remove([name, ratio, game])
            if (tweetmode):
                print "Tweeting!"
            else:
                print "(Not actually Tweeting this):"
            confirmed.append([name, ratio, game])
            originame = name[21:]
            chatters = int(viewers * ratio) # TODO: something more intelligent than chatters, take into account the average game ratio and calculate the expected number of viewers
            game_tweet = get_game_tweet(game)
            #TODO: change expected_ratio to be each game - is this a good idea? avg skewed by botting viewers...
            fake_viewers = int(viewers - (1 / expected_ratio) * chatters)
            estimate = "(~" + str(fake_viewers) + " extra viewers of "+ str(viewers) + " total)"
            tweet = name + " (" + game_tweet + ") might have a false-viewer bot " + estimate
            if (ratio < 0.15):
                tweet = name + " (" + game_tweet + ") appears to have a false-viewer bot " + estimate
            if (ratio < 0.09):
                tweet = name + " (" + game_tweet + ") almost definitely has a false-viewer bot " + estimate
            if (len(tweet) + 2 + len(originame) <= 140): #max characters in a tweet
                tweet = tweet + " #" + originame
            print("Tweeting: '" + tweet + "'")
            if (tweetmode):
                try:
                    twitter.update_status(status=tweet)
                except:
                    print "couldn't tweet :("
                    pass
        if not found:
            for item in confirmed:
                if (item[0] == name):
                    return
            suspicious.append([name, ratio, game])

#game_ratio
#   returns the average chatter:viewer ratio for a certain game
#game is a string - game to search
def game_ratio(game):
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
            send_tweet(user, ratio, game, viewers)
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
    for item in suspicious:
        name = item[0]
        originame = name[21:] #remove the http://www.twitch.tv/
        if (user_viewers(originame) < user_threshold_2):
            print originame + " appears to have stopped botting! removing from suspicious list"
            suspicious.remove(item)

    for item in confirmed:
        name = item[0]
        originame = name[21:] #remove the http://www.twitch.tv/
        if (user_ratio(originame) > 0.40 or user_viewers(originame) == 0):
            print originame + " appears to have stopped botting! removing from confirmed list"
            confirmed.remove(item)

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


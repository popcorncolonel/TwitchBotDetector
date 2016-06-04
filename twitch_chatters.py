import socket
import requests
import sys 
import re
import time
from twitch_viewers import user_viewers, removeNonAscii, user_total_views
from get_exceptions import get_exceptions
import urllib2
from botter import Botter

from global_consts import debug, tweetmode, alternative_chatters_method, \
                          d2l_check, user_threshold, ratio_threshold, \
                          expected_ratio, num_games

if len(sys.argv) > 1:
    args = sys.argv[1:]
    if '-debug' in args:
        debug = True
    if '--no-tweetmode' in args or '-q' in args:
        tweetmode = False

import handle_twitter
if debug:
    import webbrowser #just for debugging. like javascript alerts. don't need it otherwise.
if alternative_chatters_method: #From what I can tell, this no longer works. I believe it has something to do with the backend of how their IRC is implemented.
    from chat_count import chat_count

global_sum = 0
global_cnt = 0

#lists of Botters passed around all over the place, represents who's currently botting.
suspicious = []
confirmed = []

# these users are known to have small chat to viewer ratios for valid reasons
# NOTE: Regexes, not only strings (though strings will work too)
#       You don't have to put ^ or $ at the beginning/end. just use .* -- it's more readable.
# example: chat disabled, or chat hosted not on the twitch site, or mainly viewed on 
#          front page of twitch
# type: list of REGEXes: example: ["destiny", "scg_live.*", ".*twitch.*"]
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
        print ":((( get_chatters2 line 37 on twitch_chatters"
        return get_chatters2(user)
    return chatters2

#user_chatters:
#   returns the number of chatters in user's Twitch chat
#user is a string representing http://www.twitch.tv/<user>
def user_chatters(user, depth=0):
    chatters = 0
    chatters2 = 0
    try:
        req = requests.get("http://tmi.twitch.tv/group/user/" + user)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "couldn't get users for " + user + "; recursing"
        time.sleep(0.3) #don't recurse too fast
        return user_chatters(user, depth+1)
    if alternative_chatters_method:
        chatters2 = get_chatters2(user)
        if chatters2 > 1:
            return chatters2
    try:
        while req.status_code != 200:
            print "----TMI error", req.status_code, 
            if alternative_chatters_method:
                chatters2 = get_chatters2(user)
                print "getting", user + " (module returned %d)-----" %chatters2
                if chatters2 > 1:
                    return chatters2
            else:
                print "getting", user + "-----" 
            return user_chatters(user, depth+1)
        try:
            chat_data = req.json()
        except ValueError:
            print "couldn't json in getting " + user + "'s chatters; recursing"
            return user_chatters(user, depth+1)
        chatters = chat_data['chatter_count']
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "recursing in user_chatters, got some kinda TypeError"
        return user_chatters(user, depth+1)
    return chatters

#dota2lounge_list:
#   returns the list of live Twitch streams embedded on dota2lounge.
#   this is useful because, at any given time, there could be tens of thousands
#   of users watching a Twitch stream through d2l, and I don't want to false positive these streams.
def get_dota2lounge_list():
    try:
        u = urllib2.urlopen('http://dota2lounge.com/index.php').read().split("matchmain")
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "D2L error 1 :((("
        return []
    string = "LIVE</span>"
    list1 = filter(lambda x: string in x, u) 

    list2 = []
    string2 = "match?m="
    for item in list1:
        item = item.split("\n")
        for sentence in item:
            if string2 in sentence:
                list2.append(sentence)

    d2l_list = []

    for item in list2:
        url = "http://dota2lounge.com/" + item.split("\"")[1]
        try:
            u2 = urllib2.urlopen(url).read().split("\n")
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print "D2L error 2 :((("
            return []
        list3 = filter(lambda x: "twitch.tv/widgets/live_embed_player.swf?channel=" in x, u2)
        for item in list3:
            item = item.split("channel=")[1].split("\"")[0].lower()
            d2l_list.append(item)
    return d2l_list

# very ugly web scraping :)))
def get_frontpage_users():
    try:
        u = urllib2.urlopen('http://www.twitch.tv',timeout=5).read().split('data-channel=')
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "Twitch frontpage error :((("
        return []
    users = []
    for channel in u:
        name = channel.split("'")[1]
        if name not in users:
            users.append(name)
    return users

#user_ratio:
#   returns the ratio of chatters to viewers in <user>'s channel
#user is a string representing http://www.twitch.tv/<user>
def user_ratio(user):
    chatters2 = 0
    exceptions = get_exceptions()
#users don't have to put ^ or $ at the beginning. just use .* it's more readable.
    for regex in exceptions:
        if regex != '':
            if regex[0] != '^':
                regex = '^' + regex
            if regex[-1] != '$':
                regex += '$'
           #if the username matches the regex 
            if re.match(regex, user, re.I|re.S) != None: 
                print user, "is alright :)",
                return 1
    if user in get_frontpage_users():
        print "nope,", user, "is on the front page of twitch.",
        return 1
    if d2l_check:
        d2l_list = get_dota2lounge_list()
        if user in d2l_list:
            print user, "is being embedded in dota2lounge. nogo",
            return 1
    chatters = user_chatters(user)
    if debug:
        chatters2 = get_chatters2(user)
    viewers = user_viewers(user)
    if viewers == -1: #this means something went wrong with the twitch servers, or user's internet died
        print "RECURSING BECAUSE OF 422 TWITCH ERROR"
        return user_ratio(user)
    if viewers and viewers != 0: #viewers == 0 => streamer offline
        maxchat = max(chatters, chatters2)
        ratio = float(maxchat) / viewers
        print user + ": " + str(maxchat) + " / " + str(viewers) + " = %0.3f" %ratio,
        if debug:
            print "(%d - %d)" %(chatters2, chatters),
        if chatters != 0:
            if debug:
                diff = abs(chatters2 - chatters)
                error = (100 * (float(diff) / chatters)) #percent error 
        else:
            return 0
        if debug and error > 6:
            print " (%0.0f%% error)!" %error,
            if error < 99 and diff > 10:
                print "!!!!!!!!!!!!!!!!!!!" #if my chatters module goes wrong, i want to notice it.
            if ratio > 1:
                webbrowser.open("BDB - ratio for "+user+" = %0.3f" %(ratio))
                print "????????????"
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
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "uh oh caught exception when connecting. try again. see game_ratio(game)."
        time.sleep(5)
        return game_ratio(game)
    if not r:
        time.sleep(5)
        return game_ratio(game)
    while r.status_code != 200:
        print r.status_code, ", service unavailable"
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
    try:
        gamedata = r.json()
    except ValueError:
        print "could not decode json. recursing"
        time.sleep(5)
        return game_ratio(game)
#TODO make a dictionary with keys as the game titles and values as the average and count
    count = 0 # number of games checked
    avg = 0
    while 'streams' not in gamedata.keys():
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
        while r.status_code != 200:
            print r.status_code, ", service unavailable"
            r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game)
            time.sleep(1)
        try:
            gamedata = r.json()
        except ValueError:
            print "couldn't json; recursing"
            continue
    if len(gamedata['streams']) > 0:
        for i in range(0, len(gamedata['streams'])):
            viewers =  gamedata['streams'][i]['viewers']
            if viewers < user_threshold:
                break

            user = gamedata['streams'][i]['channel']['name'].lower() 
            name = "http://www.twitch.tv/" + user

            ratio = -1
            ratio = user_ratio(user)
            if ratio == 0:
                print "ratio is 0... abort program?"
            handle_twitter.send_tweet(user, ratio, game, viewers, tweetmode, 
                                      ratio_threshold, confirmed, suspicious)
            avg += ratio
            count += 1
            time.sleep(1) #don't spam servers
    else:
        print "couldn't find " + game + " :("
        return 0
    global global_sum
    global global_cnt
    global_sum += avg
    global_cnt += count
    if count != 0:
        avg /= count
    # for the game specified, go through all users more than <user_threshold> viewers, find ratio, average them
    return avg

#remove_offline:
#   removes users from the suspicious and confirmed lists if they are no longer botting
def remove_offline():
    print "==REMOVING OFFLINE=="
    flag = False #flag is for styling the terminal, nothing else. 
    to_remove = []
    for item in suspicious:
        name = item.user
        originame = name[10:] #remove the http://www.twitch.tv/
        if (user_ratio(originame) > 2*ratio_threshold or 
                user_viewers(originame) < user_threshold/4):
            print originame + " appears to have stopped botting! removing from suspicious list"
            to_remove.append(item)
        else:
            print
    for item in to_remove:
        suspicious.remove(item)
    to_remove = []
    for item in confirmed:
        if confirmed != []:
            flag = True #flag is for styling the terminal, nothing else.
        name = item.user
        originame = name[10:] #remove the http://www.twitch.tv/
        if user_ratio(originame) > (2 * ratio_threshold) or user_viewers(originame) < 50:
            print originame + " appears to have stopped botting! removing from confirmed list"
            to_remove.append(item)
        else:
            print
    for item in to_remove:
        confirmed.remove(item)
    if flag:
        print
        print
    print "looping back around :D"
    print
    print

#search_all_games:
#   loops through all the games via the Twitch API, checking for their average ratios
def search_all_games():
    global global_sum
    try:
        topreq = requests.get("https://api.twitch.tv/kraken/games/top?limit=" + str(num_games))
        while topreq.status_code != 200:
            print "trying to get top games..."
            topreq = requests.get("https://api.twitch.tv/kraken/games/top?limit=" + str(num_games))
        topdata = topreq.json()
    except requests.exceptions.ConnectionError:
        print "connection error trying to get the game list. recursing :)))"
        return search_all_games
    except ValueError:
        print "nope. recursing. ~287 twitch_chatters.py"
        search_all_games()
    for i in range(0,len(topdata['top'])):
        game = removeNonAscii(topdata['top'][i]['game']['name'])
        print "__" + game + "__", 
        print "(tweetmode off)" if not tweetmode else ""
        prev_suspicious = suspicious[:] #make a duplicate of suspicious before things are added to the new suspicious list
        ratio = game_ratio(game) #does remove elements from suspicious and puts them into confirmed
        for item in suspicious:
            if item.game == game and item in prev_suspicious:
                newconfirmed = [i for i in confirmed if i.game == game and item.user == i.user]
                if newconfirmed != []:
                    suspicious.remove(item)
                    print item.user[10:], "was found to have stopped botting", game + "!",
                    print " removing from suspicious list!"
                else:
                    suspicious.remove(item)
        print
        print "Average ratio for " + game + ": %0.3f" %ratio
        print
        print "Total global ratio: %0.3f" %(global_sum / float(global_cnt))
        print
        print "We are suspicious of: "
        if len(suspicious) == 0:
            print "No one :D"
        for item in suspicious:
            channel = item.user[10:]
            print "%s %s%d / %d = %0.3f   %s" %(channel, 
                                                " "*(20-len(channel)), #formatting spaces
                                                item.chatters, item.viewers, item.ratio,
                                                item.game
                                               )
            #print item.user[10:], "- %d / %d = %0.3f:" %(item.chatters, item.viewers, item.ratio,), "      ", item.game
        print
        print "We have confirmed: "
        if len(confirmed) == 0:
            print "No one :D"
        for item in confirmed:
            channel = item.user[10:]
            print "%s %s%d / %d = %0.3f   %s" %(channel, 
                                                " "*(20-len(channel)), #formatting spaces
                                                item.chatters, item.viewers, item.ratio,
                                                item.game
                                               )
            #print channel+": " + " "*20-len(channel) + \
            #        "%d / %d = %0.3f:" %(item.chatters, item.viewers, item.ratio,), item.game
        print
        print "Total of", len(suspicious)+len(confirmed), "botters"
        print
        print



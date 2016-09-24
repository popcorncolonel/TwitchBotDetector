import handle_twitter
import re
import socket
import sys
import time
import urllib2

import requests

from get_exceptions import get_exceptions
from get_passwords import CLIENT_ID
from global_consts import debug, tweetmode, alternative_chatters_method, \
    d2l_check, user_threshold, ratio_threshold, \
    num_games
from twitch_viewers import user_viewers, remove_non_ascii
from utils import get_json_response

if len(sys.argv) > 1:
    args = sys.argv[1:]
    if '-debug' in args:
        debug = True
    if '--no-tweetmode' in args or '-q' in args:
        tweetmode = False


if debug:
    import webbrowser  # Just for debugging.
if alternative_chatters_method:  # From what I can tell, this no longer works. I believe it has something to do with the backend of how their IRC is implemented.
    from chat_count import chat_count

global_sum = 0
global_cnt = 0

# Lists of Botters passed around all over the place, represents who's currently botting.
suspicious = []
confirmed = []

# These users are known to have small chat to viewer ratios for valid reasons
# NOTE: Regexes, not only strings (though strings will work too)
#       You don't have to put ^ or $ at the beginning/end. just use .* -- it's more readable.
# example: chat disabled, or chat hosted not on the twitch site, or mainly viewed on 
#          front page of twitch
# type: list of REGEXes: example: ["destiny", "scg_live.*", ".*twitch.*"]
exceptions = get_exceptions()


def get_chatters2(user):
    """
    gets the number of chatters in user's Twitch chat, via chat_count
    Essentially, chat_count is my experimental method that goes directly to
    a user's IRC channel and counts the viewers there. It is not yet proven to be
    correct 100% of the time.
    """
    chatters2 = 0
    try:
        chatters2 = chat_count(user)
    except socket.error as error:
        print ":((( get_chatters2 line 37 on twitch_chatters"
        return get_chatters2(user)
    return chatters2


def user_chatters(user, depth=0):
    """
    Returns the number of chatters in user's Twitch chat
    :param user: string representing http://www.twitch.tv/<user>
    """
    chatters = 0
    chatters2 = 0
    try:
        req = requests.get("http://tmi.twitch.tv/group/user/" + user, headers={"Client-ID": CLIENT_ID})
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "couldn't get users for " + user + "; recursing"
        time.sleep(0.3)  # don't recurse too fast
        return user_chatters(user, depth + 1)
    if alternative_chatters_method:
        chatters2 = get_chatters2(user)
        if chatters2 > 1:
            return chatters2
    try:
        while req.status_code != 200:
            print "----TMI error", req.status_code,
            if alternative_chatters_method:
                chatters2 = get_chatters2(user)
                print "getting", user + " (module returned %d)-----" % chatters2
                if chatters2 > 1:
                    return chatters2
            else:
                print "getting", user + "-----"
            return user_chatters(user, depth + 1)
        try:
            chat_data = req.json()
        except ValueError:
            print "couldn't json in getting " + user + "'s chatters; recursing"
            return user_chatters(user, depth + 1)
        chatters = chat_data['chatter_count']
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "recursing in user_chatters, got some kinda TypeError"
        return user_chatters(user, depth + 1)
    return chatters


# dota2lounge_list:
def get_dota2lounge_list():
    """
    returns the list of live Twitch streams embedded on dota2lounge.
    this is useful because, at any given time, there could be tens of thousands
    of users watching a Twitch stream through d2l, and I don't want to false positive these streams.
    """
    try:
        req = urllib2.Request('http://dota2lounge.com/index.php')
        req.add_header('Client-ID', CLIENT_ID)
        u = urllib2.urlopen(req).read().split("matchmain")
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
            req = urllib2.Request(url)
            req.add_header('Client-ID', CLIENT_ID)
            u2 = urllib2.urlopen(req).read().split("\n")
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


def get_frontpage_users():
    """
    Returns a list of featured streamers.
    """
    try:
        url = "https://api.twitch.tv/kraken/streams/featured?limit=100"
        req = requests.get(url, headers={"Client-ID": CLIENT_ID})
        data = req.json()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        print("Error getting featured streams: ", e)
        return []
    return [obj['stream']['channel']['name'] for obj in data['featured']]


def is_being_hosted(user):
    user_dict = get_json_response('https://api.twitch.tv/kraken/channels/{}'.format(user))
    user_id = user_dict['_id']
    hosts = get_json_response('https://tmi.twitch.tv/hosts?include_logins=1&target={}'.format(user_id))
    return hosts['hosts'] != []


def user_ratio(user):
    """
    :param user: string representing http://www.twitch.tv/<user>
    :return: the ratio of chatters to viewers in <user>'s channel
    """
    chatters2 = 0
    exceptions = get_exceptions()
    # Don't have to put ^ or $ at the beginning. Just use .* it's more concise.
    for regex in exceptions:
        if regex != '':
            if regex[0] != '^':
                regex = '^' + regex
            if regex[-1] != '$':
                regex += '$'
            if re.match(regex, user, re.I | re.S) != None:
                print user, "is alright :)",
                return 1
    if user in get_frontpage_users():
        print "nope,", user, "is a featured stream (being shown on the frontpage).",
        return 1
    if is_being_hosted(user):
        print "nope,", user, "is being hosted by someone",
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
    if viewers == -1:  # This means something went wrong with the twitch servers, or internet cut out
        print "RECURSING BECAUSE OF 422 TWITCH ERROR"
        return user_ratio(user)
    if viewers and viewers != 0:  # viewers == 0 => streamer offline
        maxchat = max(chatters, chatters2)
        ratio = float(maxchat) / viewers
        print user + ": " + str(maxchat) + " / " + str(viewers) + " = %0.3f" % ratio,
        if debug:
            print "(%d - %d)" % (chatters2, chatters),
        if chatters != 0:
            if debug:
                diff = abs(chatters2 - chatters)
                error = (100 * (float(diff) / chatters))  # Percent error
        else:
            return 0
        if debug and error > 6:
            print " (%0.0f%% error)!" % error,
            if error < 99 and diff > 10:
                print "!!!!!!!!!!!!!!!!!!!"  # If my chatters module goes wrong, i want to notice it.
            if ratio > 1:
                webbrowser.open("BDB - ratio for " + user + " = %0.3f" % ratio)
                print "????????????"
            else:
                print
    else:
        return 1  # User is offline.
    return ratio


def game_ratio(game):
    """
    Returns the average chatter:viewer ratio for a certain game
    :param game: string (game to search)
    :return:
    """
    global tweetmode
    try:
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game, headers={"Client-ID": CLIENT_ID})
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
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game, headers={"Client-ID": CLIENT_ID})
    try:
        gamedata = r.json()
    except ValueError:
        print "could not decode json. recursing"
        time.sleep(5)
        return game_ratio(game)
    # TODO make a dictionary with keys as the game titles and values as the average and count
    count = 0  # Number of games checked
    avg = 0
    while 'streams' not in gamedata.keys():
        r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game, headers={"Client-ID": CLIENT_ID})
        while r.status_code != 200:
            print r.status_code, ", service unavailable"
            r = requests.get('https://api.twitch.tv/kraken/streams?game=' + game, headers={"Client-ID": CLIENT_ID})
            time.sleep(1)
        try:
            gamedata = r.json()
        except ValueError:
            print "couldn't json; recursing"
            continue
    if len(gamedata['streams']) > 0:
        for i in range(0, len(gamedata['streams'])):
            viewers = gamedata['streams'][i]['viewers']
            if viewers < user_threshold:
                break

            user = gamedata['streams'][i]['channel']['name'].lower()

            ratio = user_ratio(user)
            if ratio == 0:
                print "ratio is 0... abort program?"
            handle_twitter.send_tweet(user, ratio, game, viewers, tweetmode,
                                      ratio_threshold, confirmed, suspicious)
            avg += ratio
            count += 1
            time.sleep(1)  # don't spam servers
    else:
        print "couldn't find " + game + " :("
        return 0
    global global_sum
    global global_cnt
    global_sum += avg
    global_cnt += count
    if count != 0:
        avg /= count
    # For the game specified, go through all users more than <user_threshold> viewers, find ratio, average them.
    return avg


def remove_offline():
    """
    Removes users from the suspicious and confirmed lists if they are no longer botting
    """
    print "==REMOVING OFFLINE=="
    flag = False  # flag is for styling the terminal, nothing else.
    to_remove = []
    for item in suspicious:
        name = item.user
        originame = name[10:]  # Remove the http://www.twitch.tv/
        if (user_ratio(originame) > 2 * ratio_threshold or
                    user_viewers(originame) < user_threshold / 4):
            print originame + " appears to have stopped botting! removing from suspicious list"
            to_remove.append(item)
        else:
            print
    for item in to_remove:
        suspicious.remove(item)
    to_remove = []
    for item in confirmed:
        if confirmed != []:
            flag = True  # Flag is for styling the terminal, nothing else.
        name = item.user
        originame = name[10:]  # remove the http://www.twitch.tv/
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


def search_all_games():
    """
    loops through all the games via the Twitch API, checking for their average ratios
    """
    global global_sum
    try:
        topreq = requests.get("https://api.twitch.tv/kraken/games/top?limit=" + str(num_games),
                              headers={"Client-ID": CLIENT_ID})
        while topreq.status_code != 200:
            print "trying to get top games..."
            topreq = requests.get("https://api.twitch.tv/kraken/games/top?limit=" + str(num_games),
                                  headers={"Client-ID": CLIENT_ID})
        topdata = topreq.json()
    except requests.exceptions.ConnectionError:
        print "connection error trying to get the game list. recursing :)))"
        return search_all_games
    except ValueError:
        print "nope. recursing. ~287 twitch_chatters.py"
        search_all_games()
    for i in range(0, len(topdata['top'])):
        game = remove_non_ascii(topdata['top'][i]['game']['name'])
        print "__" + game + "__",
        print "(tweetmode off)" if not tweetmode else ""
        prev_suspicious = suspicious[:]  # Make a duplicate of suspicious before things are added to the new suspicious list
        ratio = game_ratio(game)  # Remove elements from suspicious and puts them into confirmed
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
        print "Average ratio for " + game + ": %0.3f" % ratio
        print
        print "Total global ratio: %0.3f" % (global_sum / float(global_cnt))
        print
        print "We are suspicious of: "
        if len(suspicious) == 0:
            print "No one :D"
        for item in suspicious:
            channel = item.user[10:]
            print "%s %s%d / %d = %0.3f   %s" % (channel,
                                                 " " * (20 - len(channel)),  # formatting spaces
                                                 item.chatters, item.viewers, item.ratio,
                                                 item.game
                                                 )
        print
        print "We have confirmed: "
        if len(confirmed) == 0:
            print "No one :D"
        for item in confirmed:
            channel = item.user[10:]
            print "%s %s%d / %d = %0.3f   %s" % (channel,
                                                 " " * (20 - len(channel)),  # formatting spaces
                                                 item.chatters, item.viewers, item.ratio,
                                                 item.game
                                                 )
        print
        print "Total of", len(suspicious) + len(confirmed), "botters"
        print
        print

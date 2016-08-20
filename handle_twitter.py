from global_consts import tweetmode, expected_ratio
import sys

if len(sys.argv) > 1:
    args = sys.argv[1:]
    if '--no-tweetmode' in args or '-q' in args:
        tweetmode = False

if tweetmode:
    from twython import Twython
    from get_passwords import get_passwords, get_twitter_name
    import twitter
from botter import Botter

if tweetmode:
    passes = get_passwords()

    #must be a string - ex "day9tv"
    twitter_name = get_twitter_name() 

    APP_KEY =            passes[0]
    APP_SECRET =         passes[1]
    OAUTH_TOKEN =        passes[2]
    OAUTH_TOKEN_SECRET = passes[3]

    tweetter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    api = twitter.Api(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET) 

    num_recent_tweets = 50

#get_formatted_game:
#   tailors the name of the game (heh) to what is readable and short enough to tweet
#game is a string
def get_formatted_game(game):
    formatted_game = game.split(":")[0] #manually shorten the tweet, many of these by inspection
    if formatted_game[:17] == "The Elder Scrolls":
        formatted_game = "TES:" + formatted_game[17:] #TES: Online
    if formatted_game == "Halo":
        formatted_game = game
    if formatted_game == "League of Legends":
        formatted_game = "LoL"
    if formatted_game == "Call of Duty" and len(game.split(":")) > 1:
        formatted_game = "CoD:" + game.split(":")[1] #CoD: Ghosts, CoD: Modern Warfare
    if formatted_game == "Counter-Strike" and len(game.split(":")) > 1:
        formatted_game = "CS: " 
        for item in game.split(":")[1].split(" "): 
            if len(item) > 0:
                formatted_game += item[0] #first initial - CS:S, CS:GO
    if formatted_game == "StarCraft II" and len(game.split(":")) > 1:
        formatted_game = "SC2: "
        for item in game.split(":")[1].split(" "):
            if len(item) > 0:
                formatted_game += item[0] #first initial - SC2: LotV
    return formatted_game

#send_tweet
#   if <user> is believed to be viewer botting, sends a tweet via the twitter module
#user is a string representing http://www.twitch.tv/<user>
#ratio is <user>'s chatter to viewer ratio
#game is the game they're playing (Unabbreviated: ex. Starcraft II: Heart of the Swarm)
#viewers is how many viewers the person has - can be used to get number of chatters, with ratio
def send_tweet(user, ratio, game, viewers, tweetmode, ratio_threshold, confirmed, suspicious):
    name = "twitch.tv/" + user + "?live"
    if ratio < ratio_threshold:
        found = False #Whether or not the user has been found in the *suspicious* list
        for item in confirmed:
            if item.user == name:
                item.ratio = ratio #update the info each time we go through it
                item.viewers = viewers
                item.chatters=int(viewers * ratio)
                item.game = game
        for item in suspicious:
            if item.user == name:
                item.viewers = viewers
                item.chatters=int(viewers * ratio)
                item.ratio = ratio #update the info
                item.game = game
                found = True
        if found:
            print
            if tweetmode:
                print "Tweeting!"
            else:
                print "(Not actually Tweeting this):"
            #move item from suspiciuos to confirmed
            confirmed.append([item for item in suspicious if item.user == name][0]) 

            #usernames in these lists are unique (you can only stream once at a time...)
            suspicious = [item for item in suspicious if item.user != name] 

            chatters = int(viewers * ratio) 
            formatted_game = get_formatted_game(game)
            #TODO: change expected_ratio to be each game - is this a good idea? avg skewed by botting viewers, and low sample size...
            fake_viewers = int(viewers - (1 / expected_ratio) * chatters)
            estimate = "(~" + str(fake_viewers) + " extra viewers of "+ str(viewers) + " total)"
            tweet = name + " (" + formatted_game + ") might have a false-viewer bot " + estimate
            if ratio < 0.07:
                tweet = name + " (" + formatted_game + ") appears to have a false-viewer bot " + estimate
            if ratio < 0.05:
                tweet = name + " (" + formatted_game + ") almost definitely has a false-viewer bot " + estimate
            if len(tweet) + 2 + len(user) <= 140: #max characters in a tweet
                tweet = tweet + " #" + user
            if not tweetmode:
                print "Not",
            print "Tweet text: '" + tweet + "'"
            if tweetmode:
                while True:
                    try:
                        statuses = api.GetUserTimeline(twitter_name, count=num_recent_tweets)[:num_recent_tweets]
                        break
                    except twitter.TwitterError:
                        print "error getting statuses for BDB - retrying"
                        pass
                found_rec_tweet = False #did we recently tweet about this person?
                for status in statuses:
                    names = status.text.split("#")
                    if len(names) == 2:
                        if names[1] == user:
                            found_rec_tweet = True
                            break
                if found_rec_tweet:
                    print "Not tweeting because I found recent tweet for", user
                else:
                    try:
                        tweetter.update_status(status=tweet)
                        time.sleep(10) #rate limiting
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except:
                        print "couldn't tweet :("
                        pass
        if not found:
            for item in confirmed:
                if item.user == name:
                    print
                    return
            new_botter = Botter(user=name, ratio=ratio, game=game, viewers=viewers, chatters=int(viewers * ratio))
            suspicious.append(new_botter)
            print " <-- added to suspicious for this"
    else:
        print


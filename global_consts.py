debug = False #debug mode with extraneous error messages and information
tweetmode = False #true if you want it to tweet, false if you don't
d2l_check = True #check dota 2 lounge's website for embedded live matches?
user_threshold = 200   #initial viewers necessity for confirmation
ratio_threshold = 0.16 #if false positives, lower this number. if false negatives, raise this number
expected_ratio = 0.7 #eventually tailor this to each game/channel. Tailoring to channel might be hard.
num_games = 50 #number of games to look at, sorted by viewer count
alternative_chatters_method = False  #True if you want to use faster but potentially unreliable
                                     #method of getting number of chatters for a user

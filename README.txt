Essentially this is a bot that tries to detect streams with fake viewers via
the Twitch API and the power of statistics.

It looks at certain metrics such as the ratio between chatters to "viewers". I
realize that this is not a perfect metric, but it has proven to be
surprisingly accurate. Alternative bot detection methods are listed below.
I still don't know how to deal with streams with fake chat users, but
I'm working on learning some potential features that can be used to detect
them with Machine Learning. Let me know if you see any patters in streams with 
fake chatters by [emailing me](popcorncolonel@gmail.com)!

TL;DR:
Go to http://www.twitter.com/BotDetectorBot!

TODO:
1) More sophisticated detection methods, including:
    -Sharp, significant increases in viewers without proportional increases in
     the number of chat users (take into account videos in the front page of
     Twitch.. maybe check the front page of Twitch to see which user is there?
     On average how many users are watching via the main twitch page?)

    -Take into account the average chat viewer ratio for each game per user
        -maybe a bad idea - skewed by bots

    -Long-term database storage of average viewer count

    -If the stream has more viewers than followers, there may be cause for concern.

    -More chatters than viewers, plus weird names/inactive chat => suspicion

2) Keep the program running when my internet crashes. Currently the program
   just exits.

3) COMPLETE: Overhaul the tweet removal system, or rethink it in general. 
   Should it delete old tweets that were saying that the user was botting?
   See http://www.twitter.com/LiveBotDetector, or 
       http://github.com/popcorncolonel/LiveBotDetector

4) New heuristic for detecting chatbots: very low average follower count in
   chat (regarding how many people each user is following) is indicative of
   chatbots. Also if a lot of the bots have the exact same number (say, under 5)
   
   Or, if most of the followers are following the exact same streams.

   The main problems with these is that I need to individually access the
   Twitch servers for each chatter; this could take hours for certain streams
   with large viewer counts.


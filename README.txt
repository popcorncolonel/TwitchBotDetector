Essentially this is a bot that tries to detect streams with fake viewers via
the Twitch API.

It looks at certain metrics such as the ratio between chatters to "viewers". I
realize that this is not a perfect metric, but it has proved to be
surprisingly accurate. Some alternative bot detection methods are listed
below. I still don't know how to deal with streams with fake chat users, but
I'm working on learning some potential features that can be used to detect
them with Machine Learning. However, people with fake chatters and fake
viewers are hard to detect by inspection.

TL;DR:
Go to http://www.twitter.com/BotDetectorBot!


TODO:
1) More sophisticated detection methods, including:
-sharp, significant increases in viewers without proportional increases in
 the number of chat users (take into account videos in the front page of
 Twitch.. maybe check the front page of Twitch to see which user is there?
 On average how many users are watching via the main twitch page?)

-take into account the average chat viewer ratio for each game per user

-long-term database storage of average viewer count

-If the stream has more viewers than followers, there may be cause for concern.

2) Keep the program running when my internet crashes. Currently the program
 just exits.

3) Overhaul the tweet removal system, or rethink it in general. Should it
delete old tweets that were saying that the user was botting?

4) Separate twitter module. Why is it even in twitch_chatters.


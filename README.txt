Go to http://www.twitter.com/BotDetectorBot!

TODO:
1) Detect when the server is returning a lot of 502/503 errors, switch to a
different method of counting chat users. AKA connecting directly to the IRC's
and count using the WHO/NAMES commands.

2) More sophisticated detection methods, including:
-sharp, significant increases in viewers without proportional increases in
 the number of chat users (take into account videos in the front page of
 Twitch.. maybe check the front page of Twitch to see which user is there?
 On average how many users are watching via the main twitch page?)

-take into account the average chat viewer ratio for each game per user

-long-term database storage of average viewer count

3) Keep the program running when my internet crashes. Currently the program
 just exits.


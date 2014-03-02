#counts the number of chatters in a certain Twitch chat room.
import sys
import socket
from pass_info import get_username, get_password
from twitch_viewers import removeNonAscii

names_num = "353"
end_names_num = "366"

i = 0#
def count_users(full_msg):
    data = full_msg.split("\r\n")
    count = 0
    print full_msg
    for namegroup in data:
        temp = namegroup############################
        namegroup = namegroup.split(" ")
        if (names_num in namegroup):
            names = namegroup[5:]
            count += len(names)
        if ("End of /NAMES list" in namegroup):
            if (count == 65959): #This was a number I was getting repeatedly
                print "what."    #When looking at riotgames (300k viewers).
                print temp###    #I still don't know why it is/was happening, so
                return 0         #it is still printing for debugging purposes.
            return count - 1
    if (count == 2):
        print full_msg
    if (count == 65959):
        print "wath"
        return 0
    if (count == 0):
        return count
    return count - 1 #don't count myself - i'm not actually in chat

def chat_count(chatroom, verbose=False):
    global i
    i = 0
    chan = "#" + chatroom
    nick = get_username()
    PASS = get_password()
    sock = socket.socket()
    sock.connect(("irc.twitch.tv",6667))
    sock.send("PASS " + PASS + "\r\n")
    sock.send("USER " + nick + " 0 * :" + nick + "\r\n")
    sock.send("NICK " + nick + "\r\n")
    full_msg = ""
    while 1:
       sock.send("JOIN "+chan+"\r\n")
       #sock.send("MODE " + nick + " +B\r\n")
       data = removeNonAscii(sock.recv(1024))
       i+=1
       if data[0:4] == "PING":
          sock.send(data.replace("PING", "PONG"))
          continue
       #if data.split(" ")[1] == "001":
       #   sock.send("MODE " + nick + " +B\r\n")
       full_msg += data
       if (":End of /NAMES list" in data):
           if (verbose):
               print "returning (\"End of /NAMES list\") due to:"
               print '-----'
               print data
               print '-----'
           return count_users(full_msg)
       if (":jtv MODE #" in data):
           if (verbose):
               print "returning (FOUND MODE) due to:"
               print data
           return count_users(full_msg)
       if ("PRIVMSG" in data): #privmsg's only come in after the names list
           if (verbose):
               print "returning (PRIVMSG) due to:"
               print data
           return count_users(full_msg)
       if ("366 " + nick in data): 
           if (verbose):
               print "returning (366) due to:"
               print data
           return count_users(full_msg)

#usage: "python chat_count.py twitchplayspokemon"
if (len(sys.argv) == 2):
    count = chat_count(sys.argv[1], verbose=False)
    if (type(count) == int):
        print count, "chatters in %s" %sys.argv[1]



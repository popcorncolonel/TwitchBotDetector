#counts the number of chatters in a certain Twitch chat room.
import sys
import socket
from pass_info import get_username, get_password

names_num = "353"
end_names_num = "366"

i = 0#
def chat_count(chatroom, verbose=False):
    global i
    chan = "#" + chatroom
    nick = get_username()
    PASS = get_password()
    sock = socket.socket()
    sock.connect(("irc.twitch.tv",6667))
    sock.send("PASS " + PASS + "\r\n")
    sock.send("USER " + nick + " 0 * :" + nick + "\r\n")
    sock.send("NICK " + nick + "\r\n")
    count = 0
    while 1:
       sock.send("JOIN "+chan+"\r\n")
       data = sock.recv(65536)
       i+=1
       #print i, "iterations.",
       #print "(count so far: %d)" %count
       if data[0:4] == "PING":
          sock.send(data.replace("PING", "PONG"))
       #if data.split(" ")[1] == "001":
       #   sock.send("MODE " + nick + " +B\r\n")
       #   sock.send("JOIN " + chan + "\r\n")
       data = data.split("\r\n")
       origicount = count
       for message in data:
           if (len(message.split(" ")) > 1 and message.split(" ")[1] == "366"):
               if (verbose):
                   print count, "users"
               return count
           if (len(message.split(" ")) > 1 and message.split(" ")[1] == "353"):
               names = message.split(" ")
               if ("366" in names):
                   print "woah woah woah", message
               #print names[5:]
               count += len(names[5:])
               #print "count is now", count
       if (verbose):
           if (origicount == count):
               print data
               print "^ this data was not counted"
           print count, "users"

if (len(sys.argv) == 2):
    count = chat_count(sys.argv[1])
    if (type(count) == int):
        print count, "chatters in %s" %sys.argv[1]



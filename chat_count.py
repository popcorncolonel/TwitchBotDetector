#counts the number of chatters in a certain Twitch chat room.
import sys
import socket
from pass_info import get_username, get_password

names_num = "353"
end_names_num = "366"

i = 0#
def count_users(full_msg):
    data = full_msg.split("\r\n")
    count = 0
    for namegroup in data:
        namegroup = namegroup.split(" ")
        if (names_num in namegroup):
            names = namegroup[5:]
            count += len(names)
    return count - 1 #don't count myself - i'm not actually in chat

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
    full_msg = ""
    while 1:
       sock.send("JOIN "+chan+"\r\n")
       #sock.send("MODE " + nick + " +B\r\n")
       data = sock.recv(4096)
       i+=1
       if data[0:4] == "PING":
          sock.send(data.replace("PING", "PONG"))
       #if data.split(" ")[1] == "001":
       #   sock.send("MODE " + nick + " +B\r\n")
       full_msg += data
       if (end_names_num in data.split(" ")):
           return count_users(full_msg) 

if (len(sys.argv) == 2):
    count = chat_count(sys.argv[1], verbose=True)
    if (type(count) == int):
        print count, "chatters in %s" %sys.argv[1]



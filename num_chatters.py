import socket
bot_owner = "asdf"

PASS = "oauth:f2hqds54vh0s78pmdvy1fx17van0pit"
nick = "chat_scavenger"
chan = "#not_tim"

sock = socket.socket()
sock.connect(("irc.twitch.tv", 6667))
sock.send("PASS " + PASS + "\r\n")
#sock.send("USER " + nick + " 0 * :" + bot_owner + "\r\n")
sock.send("NICK " + nick + "\r\n")

sock.send("WHO " + chan + "\r\n")
data = sock.recv(5120)
print data
if data.split(" ")[1] == "001":
    sock.send("MODE " + nick + " +B\r\n")
    #sock.send("JOIN " + chan + "\r\n")
data = sock.recv(5120)
print data





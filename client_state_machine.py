"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
"""
from chat_utils import *
import json
import random
import math


class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s
        self.public_key = ()  # Own public key to be sent to peer
        self.private_key = ()  # Own private key to decrypt
        self.peer_public_key = ()  # Peer's private key to encrypt and send

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer):
        msg = json.dumps({"action":"connect", "target":peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        if response["status"] == "success":
            self.peer = peer
            return True
        elif response["status"] == "busy":
            self.out_msg += 'User is busy. Please try again later\n'
        elif response["status"] == "self":
            self.out_msg += 'Cannot talk to yourself (sick)\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return False

    def disconnect(self):
        msg = json.dumps({"action":"disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''

    def proc(self, my_msg, peer_msg):
        self.out_msg = ''
# ==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
# ==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action":"time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action":"list"}))
                    logged_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in

                elif my_msg[0] == 'c':
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.connect_to(peer):
                        self.state = S_CHATTING
                        self.public_key, self.private_key = keygen()
                        mysend(self.s, json.dumps({"action": "publickey", "from": "[" + self.me + "]","key": self.public_key}))  # Sends public key over to peer
                        self.out_msg += 'You are connected with ' + self.peer + '\n'
                        self.out_msg += 'Generating encryption key pairs...\n'
                        self.out_msg += 'Your public key:' + str(self.public_key) + '\n'
                        self.out_msg += 'Your public key:' + str(self.private_key) + '\n'
                        self.out_msg += 'Secure channel established.\n'
                        self.out_msg += 'Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"search", "target":term}))
                    search_rslt = json.loads(myrecv(self.s))["results"].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"poem", "target":poem_idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    if len(poem) > 0:
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'

                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                try:
                    peer_msg = json.loads(peer_msg)
                except Exception as err :
                    self.out_msg += " json.loads failed " + str(err)
                    return self.out_msg

                if peer_msg["action"] == "connect":
                    # ----------your code here------#
                    self.state = S_CHATTING
                    self.peer = peer_msg["from"]
                    self.public_key, self.private_key = keygen()
                    mysend(self.s,json.dumps({"action": "publickey", "from": "[" + self.me + "]", "key": self.public_key}))
                    self.out_msg += 'Request from ' + self.peer + '\n'
                    self.out_msg += 'You are connected with ' + self.peer + '\n'
                    self.out_msg += 'Generating encryption key pairs...\n'
                    self.out_msg += 'Your public key:' + str(self.public_key) + '\n'
                    self.out_msg += 'Your public key:' + str(self.private_key) + '\n'
                    self.out_msg += 'Secure channel established.\n'
                    self.out_msg += 'Chat away!\n\n'
                    self.out_msg += '------------------------------------\n'
                    # ----------end of your code----#

# ==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
# ==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # my stuff going out
                text_list = encrypt(self.peer_public_key, '[' + self.me + ']' + my_msg)  # ENCRYPT MESSAGE HERE
                encrypted_msg = str(text_list[0])
                for num in text_list[1:]:
                    encrypted_msg += ',' + str(num)
                self.out_msg += "[Encrypted]" + encrypted_msg + '\n'
                mysend(self.s, json.dumps({"action":"exchange", "from":"[" + self.me + "]", "message":encrypted_msg}))
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = ''
            if len(peer_msg) > 0:  # peer's stuff, coming in
                # ----------your code here------#
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect":
                    self.out_msg += "(" + peer_msg["from"] + " joined)\n"
                elif peer_msg["action"] == "publickey":
                    self.peer_public_key = peer_msg["key"]
                elif peer_msg["action"] == "disconnect":
                    self.out_msg += peer_msg["message"]
                    self.state = S_LOGGEDIN
                else:
                    self.out_msg += "[Source text]" + peer_msg["from"] + peer_msg["message"] + "\n"
                    self.out_msg += "[Decrypted text]" + decrypt(self.private_key, [int(i) for i in peer_msg["message"].split(',')])
                # ----------end of your code----#
            if self.state == S_LOGGEDIN:
                # Display the menu again
                self.out_msg += menu

# ==============================================================================
# invalid state
# ==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)

        return self.out_msg

# ==============================================================================
# Encryption func
# ==============================================================================


def prime_generator():  # Generates two prime numbers and n (prime 1 * prime 2)
    flag = 0
    while flag == 0:
        x = random.randint(1,500)  # Sets the range for allowed prime numbers, larger number slows down performance
        y = random.randint(1,500)  # Sets the range for allowed prime numbers, larger number slows down performance
        if prime(x) and prime(y) and x != y:
            flag = 1
    n = x * y
    return n, x, y


def keygen():  # Generates client encryption keypairs, Public (e,n) Private (d,n)
    d = None
    while d is None:
        n, a, b = prime_generator()
        phi = (a-1) * (b-1)
        e = find_e(phi)
        d = find_d(phi, e)
    return (e, n), (d, n)


def find_e(phi):  # Find the e value for public key
    factors = set()
    for f in range(1, int(math.sqrt(phi)) + 1):
        if phi % f == 0:
            factors.add(f)
            factors.add(int(phi / f))
    e = random.randint(3, 100)
    while e % 2 == 0 or e in factors:
        e = random.randint(3, 100)
    return e


def find_d(phi, e): #Find the d value for private key (satisfies the condition de=1 % (phi(n)) )
    for d in range(3, phi):
        if d * e % phi == 1:
            return d


def decrypt(private_key, encrypted_txt): #Receive message, returns the decrypted text from an encrypted form with the private key
    d, n = private_key
    text = ''
    for i in encrypted_txt:
        text += chr(i**d % n)
    return text

def encrypt(public_key, txt): #Send message, returns the encrypted text from a plain form with the public key
    e, n = public_key
    return [ord(char) ** e % n for char in txt]


def prime(num):
    if num > 1:
        factors = 0
        for i in range(1, num):
            if num % i == 0:
                factors += 1
        if factors == 1:
            return True
    return False
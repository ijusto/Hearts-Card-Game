import random
import base64
import hashlib
import sys

class DiffieHellman:

    def __init__(self, privKey, pubKey):
        self.privKey = privKey
        self.pubKey = pubKey
        self.otherEntityPubKey = None
        self.a = None
        self.q = None  # large prime
        self.g = None  # primitive root mod q
        self.y = None
        self.yOtherEntity = None
        self.K = None

    def run(self):
        self.g = 9
        self.q = 1001
        self.a = random.randint(5, 10)

        self.y = (self.g ** self.a) % self.q

        print('g: ', self.g, ' (a shared value), n: ', self.q, ' (a prime number)')
        print('\nAlice calculates:')
        print('a (Alice random): ', self.a)
        print('Alice value (A): ', self.y, ' (g^a) mod p')

        print('\nAlice calculates:')

        keyA = (self.yOtherEntity ** self.a) % self.q
        print('Key: ', keyA, ' (B^a) mod p')
        print('Key: ', hashlib.sha256(str(keyA)).hexdigest())


import random
import base64
import hashlib
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class EllipticCurveDiffieHellman:

    def __init__(self):
        self.exchange_private_key = None
        self.exchange_public_key = None
        self.other_exchange_public_key = None
        self.a = None
        self.q = None  # large prime
        self.g = None  # primitive root mod q
        self.y = None
        self.yOtherEntity = None
        self.K = None

    def DH(self):
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

    def sign(self, data):
        private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        if not data:
            data = b"this is some data I'd like to sign"
        signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    def sharedKeyECDHE(self, peer_public_key):
        shared_key = self.exchange_private_key.exchange(ec.ECDH(), peer_public_key)
        # Perform key derivation.
        derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'handshake data',
                           backend=default_backend()).derive(shared_key)

    def generateExchangeKeys(self):
        # Generate a private key for use in the exchange.
        self.exchange_private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        self.exchange_public_key = self.exchange_private_key.public_key()
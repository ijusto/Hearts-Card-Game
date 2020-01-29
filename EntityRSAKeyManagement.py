import sys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class EntityRSAKeyManagement:

    def __init__(self, key_size):
        self.key_size = key_size # 4096
        self.priv_key = None
        self.pub_key = None

    def getRSAPrivKey(self):
        return self.priv_key

    def getRSAPubKey(self):
        priv_key = self.getRSAPrivKey()
        return priv_key.public_key()

    def generateRSAKey(self):
        # Use 65537 (2^16 + 1) as public exponent
        self.priv_key = rsa.generate_private_key(65537, self.key_size, default_backend())

    def rsaCipheringConfidentially(self, msg, otherEntityPubKey):
        return self.rsaCiphering(msg, otherEntityPubKey)

    def rsaDecipheringConfidentially(self, msg):
        return self.rsaDeciphering(msg, self.priv_key)

    def rsaCipheringAuthenticate(self, msg):
        return self.rsaCiphering(msg, self.priv_key)

    def rsaDecipheringAuthenticate(self, msg, otherEntityPubKey):
        return self.rsaDeciphering(msg, otherEntityPubKey)

    def rsaCiphering(self, msg, key):
        if isinstance(msg, str):
            msg = bytes(msg, 'utf-8')
        # Calculate the maximum amount of data we can encrypt with OAEP + SHA256
        maxLenG = (key.key_size // 8) - 2 * hashes.SHA256.digest_size - 2
        maxLen = maxLenG
        minLen = 0
        ciphertext = bytes()
        if maxLenG >= len(msg):
            ciphertext = key.encrypt(msg, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                 hashes.SHA256(), None))
        else:
            while minLen <= len(msg):
                plaintext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen + maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                ciphertext += key.encrypt(plaintext, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                            hashes.SHA256(), None))

        return ciphertext

    def rsaDeciphering(self, msg, key):
        if isinstance(msg, str):
            msg = bytes(msg, 'utf-8')
        maxLenG = 512
        maxLen = maxLenG
        minLen = 0
        plaintext = bytes()
        if maxLenG >= len(msg):
            plaintext = key.decrypt(msg, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                hashes.SHA256(), None))
        else:
            while minLen < len(msg):
                ciphertext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen + maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                plaintext += key.decrypt(ciphertext, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                            hashes.SHA256(), None))
        return plaintext

    def sign(self, dataToBeSigned):
        data = dataToBeSigned
        if isinstance(dataToBeSigned, str):
            data = bytes(dataToBeSigned, 'utf-8')
        signature = self.priv_key.sign(data, padding.PSS(padding.MGF1(hashes.SHA256()),
                                                               padding.PSS.MAX_LENGTH), hashes.SHA256())
        return signature

    def set_key_size(self, key_size):
        self.key_size = key_size

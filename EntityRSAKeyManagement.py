import sys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class EntityRSAKeyManagement:

    def __init__(self, key_size):
        self.key_size = key_size # 4096
        self.pem_pwd = None # "ola"
        self.pem_file = None
        self.clear_text_filename = None # "contentToCipher.txt"
        self.ciphertext_filename = None # "cipheredContent.txt"
        self.priv_key = None
        self.pub_key = None

    def getRSAPrivKey(self):
        priv_key = self.priv_key
        if self.pem_file:
            # Load key pair to a PEM file protected by a password
            with open(self.pem_file, "rb") as kf:
                priv_key = serialization.load_pem_private_key(kf.read(), bytes(self.pem_pwd, "utf-8"),
                                                              default_backend())
        return priv_key

    def getRSAPubKey(self):
        priv_key = self.getRSAPrivKey()
        pubKey = None
        if priv_key:
            pubKey = priv_key.public_key()
        return pubKey

    def generateRSAKey(self):
        if self.pem_file:
            f = open(self.pem_file, "wb")
        # Use 65537 (2^16 + 1) as public exponent
        self.priv_key = rsa.generate_private_key(65537, self.key_size, default_backend())

        if self.pem_file:
            # Save the key pair to a PEM file protected by the password saved in variable pwd
            pem_encoding = self.priv_key.private_bytes(serialization.Encoding.PEM,
                                                  serialization.PrivateFormat.PKCS8,
                                                  serialization.BestAvailableEncryption(bytes(self.pem_pwd, "utf-8")))

            # Save the contents of pem_encoding in a file
            f.write(pem_encoding)
            f.close()

    def rsaCipheringConfidentially(self, msg, otherEntityPubKey):
        return self.rsaCiphering(msg, otherEntityPubKey)

    def rsaDecipheringConfidentially(self, msg):
        return self.rsaDeciphering(msg, self.priv_key)

    def rsaCipheringAuthenticate(self, msg):
        return self.rsaCiphering(msg, self.priv_key)

    def rsaDecipheringAuthenticate(self, msg, otherEntityPubKey):
        return self.rsaDeciphering(msg, otherEntityPubKey)

    def rsaCiphering(self, msg, key):
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

    def set_clear_text_filename(self, clear_text_filename):
        self.clear_text_filename = clear_text_filename

    def set_ciphertext_filename(self, ciphertext_filename):
        self.ciphertext_filename = ciphertext_filename

    def set_key_size(self, key_size):
        self.key_size = key_size

    def set_pem_pwd(self, pem_pwd):
        self.pem_pwd = pem_pwd

    def set_pem_file(self, clientID):
        self.pem_file = clientID + ".txt"

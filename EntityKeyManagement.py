import sys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class EntityKeyManagement:

    def __init__(self, key_size):
        self.key_size = key_size # 4096
        self.pem_pwd = None # "ola"
        self.pem_file = None + ".txt"
        self.clear_text_filename = None # "contentToCipher.txt"
        self.ciphertext_filename = None # "cipheredContent.txt"
        self.priv_key = None
        self.pub_key = None

    def getPrivKey(self):
        priv_key = self.priv_key
        if self.pem_file:
            # Load key pair to a PEM file protected by a password
            with open(self.pem_file, "rb") as kf:
                priv_key = serialization.load_pem_private_key(kf.read(), bytes(self.pem_pwd, "utf-8"),
                                                              default_backend())
        return priv_key

    def getPubKey(self):
        priv_key = self.getPrivKey()
        pubKey = None
        if priv_key:
            pubKey = priv_key.public_key()
        return pubKey

    def generateKey(self):
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

    def rsaCiphering(self):
        # Open input for reading and output file for writing
        in_file = open(self.clear_text_filename, "rb")
        out_file = open(self.ciphertext_filename, "wb")

        # Load key pair to a PEM file protected by a password
        with open(self.pem_file, "rb") as kf:
            priv_key = serialization.load_pem_private_key(kf.read(), bytes(self.pem_pwd, "utf-8"),
                                                                            default_backend())
        pub_key = priv_key.public_key()

        # Calculate the maximum amount of data we can encrypt with OAEP + SHA256
        maxLen = (pub_key.key_size // 8) - 2 * hashes.SHA256.digest_size - 2

        while True:
            # Read for plaintext no more than maxLen bytes from the input file
            plaintext = in_file.read(maxLen)

            if not plaintext:
                break

            # Encrypt the plaintext using OAEP + MGF1(SHA256) + SHA256
            ciphertext = pub_key.encrypt(plaintext,
                                         padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                      hashes.SHA256(),
                                                      None))
            # Write the chipertext in the output file
            out_file.write(ciphertext)

        in_file.close()
        out_file.close()

    def rsaDeciphering(self):
        # Load key pair to a PEM file protected by a password
        with open(self.pem_file, "rb") as kf:
            priv_key = serialization.load_pem_private_key(kf.read(), bytes(self.pem_pwd, "utf-8"),
                                                                            default_backend())
        pub_key = priv_key.public_key()

        f = open(self.ciphertext_filename, "rb")
        ciphertext = f.read()

        plaintext = priv_key.decrypt(ciphertext, padding.OAEP(padding.MGF1(hashes.SHA256()), hashes.SHA256(), None))

        f = open(self.clear_text_filename, "wb")
        f.write(plaintext)
        f.close()

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

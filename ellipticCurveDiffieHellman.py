import random
import base64
import hashlib
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


class EllipticCurveDiffieHellman:

    def __init__(self, ccprivKey, ccpubKey, ccpubKeyOtherEntity):
        self.ccprivKey = ccprivKey
        self.ccpubKey = ccpubKey
        self.ccpubKeyOtherEntity = ccpubKeyOtherEntity
        self.exchange_private_key = None
        self.exchange_public_key = None
        self.other_exchange_public_key = None
        self.a = None
        self.q = None  # large prime
        self.g = None  # primitive root mod q
        self.y = None
        self.yOtherEntity = None
        self.K = None

    def sign(self, data):
        private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        if not data:
            data = b"this is some data I'd like to sign"
        signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    def validateSignature(self, signature, data):
        return self.exchange_public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))

    def sharedKeyECDHE(self, peer_public_key):
        shared_key = self.exchange_private_key.exchange(ec.ECDH(), peer_public_key)
        # Perform key derivation.
        derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'handshake data',
                           backend=default_backend()).derive(shared_key)

    def generateExchangeKeys(self):
        # Generate a private key for use in the exchange.
        self.exchange_private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        self.exchange_public_key = self.exchange_private_key.public_key()
        self.serialized_public = self.exchange_public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                                              format=serialization.PublicFormat.SubjectPublicKeyInfo)

        loaded_public_key = serialization.load_pem_public_key(self.serialized_public, backend = default_backend())

    def cipherUsingSharedKey(self, shared_key, msg):
        # Setup cipher: AES in CBC mode, w/ a random IV and PKCS #7 padding (similar to PKCS #5)
        iv = os.urandom(algorithms.AES.block_size // 8)
        cipher = Cipher(algorithms.AES(shared_key), modes.CBC(iv), default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()

        maxLenG = algorithms.AES.block_size
        maxLen = maxLenG
        minLen = 0
        ciphertext = bytes()
        if maxLenG >= len(msg):
            ciphertext = encryptor.update(padder.update(msg) + padder.finalize())
        else:
            finalize = False
            # Cycle to repeat while there is data left on the input data
            # Read a chunk of the input data to the plaintext variable
            # Use for the chunk length a multiple of the AES data block size
            while minLen < len(msg):
                plaintext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen + maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                    finalize = True
                if finalize:
                    ciphertext = encryptor.update(padder.update(plaintext) + padder.finalize())
                else:
                    ciphertext = encryptor.update(padder.update(plaintext))

        return iv + ciphertext + encryptor.finalize()

    def decipherUsingSharedKey(self, shared_key, msg):
        # Setup cipher: AES in CBC mode, w/ a random IV and PKCS #7 padding (similar to PKCS #5)
        iv = msg[:algorithms.AES.block_size // 8]
        msg = msg[algorithms.AES.block_size // 8:]
        cipher = Cipher(algorithms.AES(shared_key), modes.CBC(iv), default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        maxLenG = algorithms.AES.block_size
        maxLen = maxLenG
        minLen = 0
        plaintext = bytes()

        if maxLenG >= len(msg):
            plaintext = unpadder.update(decryptor.update(msg) + decryptor.finalize()) + unpadder.finalize()
        else:
            finalize = False
            # Cycle to repeat while there is data left on the input data
            # Read a chunk of the input data to the ciphertext variable
            # Use for the chunk length a multiple of the AES data block size
            while minLen < len(msg):
                ciphertext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen + maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                    finalize = True
                if finalize:
                    plaintext = unpadder.update(decryptor.update(msg)) + decryptor.finalize() + unpadder.finalize()
                else:
                    plaintext = unpadder.update(decryptor.update(msg))

        return plaintext
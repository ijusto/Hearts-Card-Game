import sys
from PyKCS11 import *
from PyKCS11.LowLevel import CKA_CLASS, CKO_PUBLIC_KEY, CKA_LABEL, CKA_VALUE, CKO_PRIVATE_KEY, CKM_SHA1_RSA_PKCS
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric import (padding, rsa, utils)

class CitizenCard:

    def __init__(self):
        self.lib = 'c:\\Windows\\System32\\pteidpkcs11.dll.'
        #self.lib = '/usr/local/lib/libpteidpkcs11.so'
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(self.lib)
        self.session = self.createSession()
        self.pubKeyHandle = self.session.findObjects([(CKA_CLASS, CKO_PUBLIC_KEY), (CKA_LABEL, 'CITIZEN AUTHENTICATION KEY')])[0]
        self.pubKeyDer = self.session.getAttributeValue(self.pubKeyHandle, [CKA_VALUE], True)[0]
        self.privKey = self.session.findObjects([(CKA_CLASS, CKO_PRIVATE_KEY), (CKA_LABEL, 'CITIZEN AUTHENTICATION KEY')])[0]
        self.pubKey = load_der_public_key(bytes(self.pubKeyDer), default_backend())

    #def setPubKey(self, pubkeyder):
    #    self.pubKey = load_der_public_key(bytes(pubkeyder), default_backend())

    def setPubKey(self, pubkey):
        self.pubKey = pubkey

    def getCitizenCardSlot(self):
        slots = self.pkcs11.getSlotList()
        for slot in slots:
            if 'CARTAO DE CIDADAO' in self.pkcs11.getTokenInfo(slot).label:
                return slot

    def createSession(self):
        slot = self.getCitizenCardSlot()
        return self.pkcs11.openSession(slot)

    def closeSession(self):
        self.session.closeSession()

    def sign(self, dataToBeSigned):
        data = dataToBeSigned
        if isinstance(dataToBeSigned, str) :
            data = bytes(dataToBeSigned, 'utf-8')
        signature = bytes(self.session.sign(self.privKey, data, Mechanism(CKM_SHA1_RSA_PKCS)))
        return signature

    #def validateSignature(self, data, signature):
    #    try:
    #        self.pubKey.verify(signature, data, padding.PKCS1v15(), hashes.SHA1())
    #        return 'Verification succeeded'
    #    except:
    #        return 'Verification failed'
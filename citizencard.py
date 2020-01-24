import sys
from PyKCS11 import *
from PyKCS11.LowLevel import CKA_CLASS, CKO_PUBLIC_KEY, CKA_LABEL, CKA_VALUE, CKO_PRIVATE_KEY, CKM_SHA1_RSA_PKCS
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric import (padding, rsa, utils)

class CitizenCard:

    def __init__(self):
        lib = '/usr/local/lib/libpteidpkcs11.so'
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(lib)
        session = self.createSession(pkcs11)
        pubKeyHandle = session.findObjects([(CKA_CLASS, CKO_PUBLIC_KEY), (CKA_LABEL, 'CITIZEN AUTHENTICATION KEY')])[0]
        pubKeyDer = session.getAttributeValue(pubKeyHandle, [CKA_VALUE], True)[0]
        privKey = session.findObjects([(CKA_CLASS, CKO_PRIVATE_KEY), (CKA_LABEL, 'CITIZEN AUTHENTICATION KEY')])[0]
        pubKey = load_der_public_key(bytes(pubKeyDer), default_backend())

    def getCitizenCardSlot(self, pkcs11):
        slots = pkcs11.getSlotList()
        for slot in slots:
            if 'CARTAO DE CIDADAO' in pkcs11.getTokenInfo(slot).label:
                return slot

    def createSession(self, pkcs11):
        slot = self.getCitizenCardSlot(pkcs11)
        return pkcs11.openSession(slot)

    def closeSession(self):
        self.session.closeSession()

    def sign(self, pkcs11, dataToBeSigned):
        data = bytes(dataToBeSigned, 'utf-8')
        signature = bytes(self.session.sign(self.privKey, data, Mechanism(CKM_SHA1_RSA_PKCS)))
        try:
            self.pubKey.verify(signature, data, padding.PKCS1v15(), hashes.SHA1())
            print('Verification succeeded')
        except:
            print('Verification failed')
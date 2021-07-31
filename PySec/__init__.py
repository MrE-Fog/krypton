﻿#from PySec import Basic
#from PySec import decorators
import hashlib
import sys
import sys
import ctypes
import os
#import PySec
DEBUG = True
if sys.platform == "win32" and DEBUG:
    a = ctypes.cdll.LoadLibrary(r"Cross-PlatformCryptoLib\out\build\x64-Debug\Debug/Cross-PlatformCryptoLib.dll")
elif sys.platform == "win32" and not DEBUG:
    a = ctypes.cdll.LoadLibrary(r"Cross-PlatformCryptoLib\out\build\x64-Release\RelWithDebInfo/Cross-PlatformCryptoLib.dll")
elif sys.platform != "win32" and DEBUG:
    a = ctypes.cdll.LoadLibrary(r"Cross-PlatformCryptoLib\out\build\Linux-Clang-Debug\Cross-PlatformCryptoLib.dll")
else:
    a = ctypes.cdll.LoadLibrary(r"Cross-PlatformCryptoLib\out\build\Linux-Clang-Release\Cross-PlatformCryptoLib.dll")

Encrypt = a.AESEncrypt
Encrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,ctypes.c_char_p]
Encrypt.restype = ctypes.c_char_p
strbuff = ctypes.create_string_buffer
NewStrBuilder = ctypes.create_string_buffer

def RestEncrypt(text, key, keydel = False,condel=False):
    buff = strbuff(text)
    iv = ctypes.create_string_buffer(12)
    kbuff=strbuff(key)
    tagbuff = strbuff(16)
    if keydel is True:
        ctypes.memset(id(key)+33,0,len(key)-1)
    if condel is True:
        ctypes.memset(id(text)+33,0,len(text)-1)
    result = Encrypt(buff, kbuff, iv, tagbuff)
    b = len(result)
    c = b+len(iv.value)
    a = NewStrBuilder(b+c+len(tagbuff.value))
    StrAdd(a,result,0)
    StrAdd(a,iv,b)
    StrAdd(a,tagbuff,b+c) #Error on excecute - perhaps not
    result = a.value
    return result

Decrypt = a.AESDecrypt
Decrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
Decrypt.restype = ctypes.c_char_p

def RestDecrypt(ctext, key, keydel = False):
    cbuff = strbuff(ctext[:-12-16])
    kbuff=strbuff(key)
    iv = ctext[-12:]
    tag = ctext[-12-16:-12]
    if keydel is True:
        ctypes.memset(id(key)+33,0,len(key)-1)
    return Decrypt(iv,kbuff,cbuff,strbuff(tag))

__all__ = ["Basic","decorators"]
ignore = ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__']
search = 9
aes = None
deaes = None
def getUser():
    return b"not connected to cloud"

key = "PySec.key"
DEBUG = True

StrAdd = a.AddToStrBuilder
StrAdd.argtypes = [ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
StrAdd.restype = ctypes.c_int

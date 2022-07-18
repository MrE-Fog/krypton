"""
Provides User Models
"""

import datetime
import os
import pickle
from typing import ByteString
from sqlalchemy import delete, select, func
from functools import wraps
from . import factors, _utils
from .bases import user
from .. import DBschemas, configs, Globalsalt
from .. import base

ITER = 500000
LEN = 32
class UserError(Exception):
    """
    Exception to be raised when an error occures in a user model.
    """
    def __init__(self, *args: object) -> None:
        self.message = args[0]
        super().__init__()
    def __str__(self) -> str:
        return self.message

def userExistRequired(func):
    """User has to be saved in order to run

    Arguments:
        func -- function

    Raises:
        UserError: If user is not saved

    Returns:
        inner1
    """
    @wraps(func)
    def inner1(self, *args, **kwargs):
        """Ensure user is saved

        Raises:
            UserError: If user is not saved

        Returns:
            N/A
        """
        if self.saved and self.loggedin:
            return func(self, *args, **kwargs)
        raise UserError("This user has not yet been saved or is logged out.")
    return inner1

class standardUser(user):
    """Please pass None to __init__ to create a new user, after that call saveNewUser with required args."""
    _userName:str = ""
    __key:bytes = None
    salt:bytes
    sessionKey:bytes
    saved = True
    loggedin = False
    backupKeys:list[str]
    backupAESKeys:list[bytes]
    def __init__(self, userID:int=None, userName:str=None) -> None:
        super().__init__()
        self.c = configs.SQLDefaultUserDBpath
        if userID is None and userName is not None:
            userID = select(DBschemas.UserTable.id).where(DBschemas.UserTable.name == userName)
            userID = configs.SQLDefaultUserDBpath.scalar(userID)
        if userID is None:
            self.saved = False
            return
        self.id = userID
        stmt = select(DBschemas.UserTable.name).where(DBschemas.UserTable.id == userID).limit(1)
        try: self._userName = self.c.scalar(stmt)[0]
        except:
            self.saved = False
        self.__privKey = self.getData("userPrivateKey")
        self.pubKey = self.getData("userPublicKey")

    @userExistRequired
    def setData(self, name: str, value: any) -> None:
        """Store user data as a key-value pair

        Arguments:
            name -- key

            value -- value
        """
        try:
            self.deleteData(name)
        except:
            pass
        entry = DBschemas.UserData(
            Uid = self.id,
            name = name,
            value = base.restEncrypt(value, self.__key)
        )
        self.c.add(entry)
        self.c.commit()

    @userExistRequired
    def getData(self, name: str) -> any:
        """Get value set by setData

        Arguments:
            name -- the key

        Raises:
            AttributeError: if a value is not set

        Returns:
            The value
        """
        stmt = select(DBschemas.UserData.value).where(DBschemas.UserData.name == name
            and DBschemas.UserData.Uid == self.id)
        result = self.c.scalar(stmt)
        # Don't forget to check backuped keys to decrypt data
        if result is None:
            raise AttributeError()
        text = base.restDecrypt(result, self.__key)
        return text

    @userExistRequired
    def deleteData(self, name:str) -> None:
        """Delete key-value pair set by setData

        Arguments:
            name -- The key to remove
        """
        stmt = delete(DBschemas.UserData).where(DBschemas.UserData.name == name
            and DBschemas.UserData.Uid == self.id)
        self.c.execute(stmt)

    @userExistRequired
    def delete(self):
        """Delete a user

        Returns:
            None
        """
        _utils.cleanUpSessions(self.id)
        stmt = select(DBschemas.UserTable).where(DBschemas.UserTable.id == self.id)
        values = self.c.scalar(stmt)
        self.c.delete(values)
        stmt = select(DBschemas.PubKeyTable).where(DBschemas.PubKeyTable.name == self.id)
        values = self.c.scalar(stmt)
        self.c.delete(values)
        self.c.execute(delete(DBschemas.UserData).where(DBschemas.UserData.Uid == self.id))
        self.c.flush()
        self.c.commit()
        return None

    def login(self, pwd:str=None, mfaToken:str=None, fido:str=None):
        """Log the user in

        Keyword Arguments:
            pwd -- Password (default: {None})

            otp -- One-Time Password (default: {None})

            fido -- Fido Token (default: {None})

        Raises:
            UserError: Password is not set

        Returns:
            Session Key, None if user is not saved
        """
        if not self.saved:
            return None
        stmt = select(DBschemas.UserTable.pwdAuthToken).where(DBschemas.UserTable.id == self.id).limit(1)
        try: authTag = self.c.scalar(stmt)
        except: raise UserError("User must have a password set.")
        self.__key = factors.password.auth(authTag, pwd)
        if self.__key is False: raise UserError("User must have a password set.")
        key = os.urandom(32)
        self.sessionKey = base.restEncrypt(self.__key, key)
        token = DBschemas.SessionKeys(
            Uid = self.id,
            key = self.sessionKey,
            iss = datetime.datetime.now(),
            exp = datetime.datetime.now() + datetime.timedelta(minutes=configs.defaultSessionPeriod)
        )
        self.c.add(token)
        self.c.commit()
        self.loggedin = True

        self.__privKey = self.getData("userPrivateKey")
        self.pubKey = self.getData("userPublicKey")
        self.backupAESKeys = pickle.loads(self.getData("backupAESKeys"))
        self.backupKeys = pickle.loads(self.getData("backupKeys"))
        return key

    @userExistRequired
    def logout(self):
        """logout Logout the user and delete the current Session
        """
        base.zeromem(self.__key)
        base.zeromem(self.__privKey)
        stmt = delete(DBschemas.SessionKeys).where(DBschemas.SessionKeys.key == self.sessionKey)
        self.c.execute(stmt)
        self.c.flush()
        self.c.commit()
        self.loggedin = False
        return

    @userExistRequired
    def restoreSession(self, key):
        """Resume sessoin from key

        Arguments:
            key -- Session Key
        """
        _utils.cleanUpSessions()
        self.sessionKey = key
        stmt = select(DBschemas.SessionKeys).where(DBschemas.SessionKeys.Uid == self.id).limit(1)
        row:DBschemas.SessionKeys = self.c.scalars(stmt)[0]
        self.__key = base.restDecrypt(row.key, key)

    @userExistRequired
    def resetPWD(self):
        """The method name says it all."""

    @userExistRequired
    def enableMFA(self):
        """The method name says it all."""

    @userExistRequired
    def disableMFA(self):
        """The method name says it all."""

    @userExistRequired
    def createOTP(self):
        """The method name says it all."""

    def saveNewUser(self, name:str, pwd:str, fido:str=None):
        """Save a new user

        Arguments:
            name -- User Name

            pwd -- Password

        Keyword Arguments:
            fido -- Fido Token (default: {None})

        Raises:
            ValueError: If user is already saved
        """
        if self.saved:
            raise ValueError("This user is already saved.")

        self.salt = os.urandom(12)
        stmt = select(func.max(DBschemas.UserTable.id))
        self.id = self.c.scalar(stmt) + 1
        keys = base.createECCKey()
        self.pubKey = keys[0]
        self.__privKey = keys[1]
        key = DBschemas.PubKeyTable(
            name = self.id,
            key = self.pubKey
        )
        self.c.add(key)
        tag = factors.password.getAuth(pwd)
        userEntry = DBschemas.UserTable(
            id = self.id,
            name = base.PBKDF2(name, Globalsalt, ITER, LEN),
            pwdAuthToken = tag,
            salt = self.salt
        )
        self.c.add(userEntry)
        self.c.flush()
        self.__key = factors.password.auth(tag, pwd)
        self.saved = True
        self.loggedin = True
        self.setData("userPrivateKey", self.__privKey)
        self.setData("userPublicKey", self.pubKey)
        self.setData("backupKeys", pickle.dumps([]))
        self.setData("backupAESKeys", pickle.dumps([]))
        self.c.flush()
        self.c.commit()
        self.login(pwd=pwd)

    @userExistRequired
    def decryptWithUserKey(self, data:ByteString, salt:bytes, sender=None) -> bytes:
        """Decrypt data with user's key

        Arguments:
            data -- Ciphertext

            salt -- Salt

        Keyword Arguments:
            sender -- If applicable sender's user name (default: {None})

        Returns:
            Plaintext
        """
        # Will also need to check the backup keys if decryption fails
        key = base.getSharedKey(self.__privKey, sender, salt)

    @userExistRequired
    def encryptWithUserKey(self, data:ByteString, otherUsers:list[str]=None) -> list[tuple[str, bytes, bytes]]:
        """Encrypt data with user's key

        Arguments:
            data -- Plaintext

        Keyword Arguments:
            otherUsers -- List of user names of people who can decrypt it  (default: {None})

        Returns:
            List of tuples of form (user name, ciphertext, salt), which needs to be provided so that user name's user can decrypt it.
        """
        salts = [os.urandom(12) for name in otherUsers]
        AESKeys = [base.getSharedKey(self.__privKey, name, salts[i])
            for i, name in enumerate(otherUsers)]
        results = [base.restEncrypt(data, key) for key in AESKeys]
        for i in AESKeys: base.zeromem(i)
        return zip(otherUsers, results, salts)

    @userExistRequired
    def generateNewKeys(self):
        """Regenerate encryption keys
        """
        keys = base.createECCKey()
        backups = self.getData("backupKeys")
        backupList:list[bytes] = pickle.loads(backups)
        backupList.append(self.__privKey)
        self.setData("backupKeys", pickle.dumps(backupList))
        for x in backups: base.zeromem(x)
        base.zeromem(backups)
        backups = self.getData("backupAESKeys")
        backupList:list[bytes] = pickle.loads(backups)
        backupList.append(self.__key)
        self.setData("backupAESKeys", pickle.dumps(backupList))
        for x in backups: base.zeromem(x)
        base.zeromem(backups)
        self.__key = os.urandom(32)
        self.__privKey = keys[0]
        self.pubKey = keys[1]
        stmt = select(DBschemas.PubKeyTable).where(DBschemas.PubKeyTable.name == self.id)
        stmt = self.c.scalar(stmt)
        self.c.delete(stmt)
        key = DBschemas.PubKeyTable(
            name = self.id,
            key = self.pubKey
        )
        self.c.add(key)
        self.c.flush()
        self.setData("userPrivateKey", self.__privKey)
        self.setData("userPublicKey", self.pubKey)
        self.setData("accountKeysCreation", datetime.now().year)

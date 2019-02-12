# -*- coding: utf-8 -*-

import base64
import os
import pathlib

from getpass import getuser
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def create_keyfile(path):
    with open(path, 'wb') as fp:
        fp.write(Fernet.generate_key())


class SetupError(Exception):
    user = ''


class KeyStore:
    """Object to store the key more secure."""

    def __init__(self, db_key):
        self._safe = Fernet(Fernet.generate_key())
        self._token = self._safe.encrypt(db_key)

    @property
    def key(self):
        return self._safe.decrypt(self._token)


class CryptedDBHandler:

    def __init__(self, crypted_filename, keyfile=None, password=None):
        if keyfile is None and password is None:
            raise SetupError('You must provide keyfile or password.')
        self.user = getuser() or 'unknown'
        self.crypted = pathlib.Path(crypted_filename)
        self._salt = os.urandom(25)
        if not self.crypted.exists():
            self._create_crypted_file()
        if keyfile is not None:
            if not os.path.exists(keyfile):
                create_keyfile(keyfile)
            self.store = self._read_token_from_file(keyfile)
        else:
            self.store = self._make_token(password)
        self.lockfile = self.lock()
        self.tmp = TemporaryDirectory(suffix='-gman')
        self.db_path = pathlib.Path(self.tmp.name, f'gman-{self.user}.sqlite')
        self.useable = False

    def lock(self):
        lockfile = self.crypted.with_suffix('.lock')
        try:
            with lockfile.open('x') as fp:
                fp.write(self.user)
            return lockfile
        except FileExistsError:
            with lockfile.open() as fp:
                user = fp.read()
            error = SetupError(f'Datenbank gesperrt von {user}.')
            error.user = user
            raise error

    def _create_crypted_file(self):
        with self.crypted.open('wb') as fp:
            fp.write(self._salt)

    def _read_token_from_file(self, keyfile):
        with open(keyfile, 'rb') as fp:
            return KeyStore(fp.read())

    def _make_token(self, password):
        with self.crypted.open('rb') as fp:
            self._salt = fp.read(25)
        if not isinstance(password, bytes):
            password = bytes(password, 'utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256,
            length=32,
            salt=self._salt,
            iterations=150000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return KeyStore(key)

    def decrypt(self):
        with self.crypted.open('rb') as fp:
            fp.seek(25)
            data = fp.read()
        if data:
            f = Fernet(self.store.key)
            with self.db_path.open('wb') as fp:
                fp.write(f.decrypt(data))
        self.useable = True
        return self.db_path

    def encrypt(self):
        with self.db_path.open('rb') as fp:
            data = fp.read()
        self.tmp.cleanup()
        f = Fernet(self.store.key)
        with self.crypted.open('wb') as fp:
            fp.write(self._salt)
            fp.write(f.encrypt(data))
        self.lockfile.unlink()
        self.useable = False

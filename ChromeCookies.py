import os
import json
import base64
import sqlite3
import shutil
from datetime import datetime, timedelta
import win32crypt  # pip install pypiwin32
from Cryptodome.Cipher import AES  # pip install pycryptodome
from requests.cookies import RequestsCookieJar


def get_chrome_datetime(chrome_date):
    """Return a `datetime.datetime` object from a chrome format datetime
    Since `chromedate` is formatted as the number of microseconds since January, 1601"""
    if chrome_date != 86400000000 and chrome_date:
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=chrome_date)
        except Exception as e:
            print(f"Error: {e}, chromedate: {chrome_date}")
            return chrome_date
    else:
        return ""


def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)

    # decode the encryption key from Base64
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # remove 'DPAPI' str
    key = key[5:]
    # return decrypted key that was originally encrypted
    # using a session key derived from current user's logon credentials
    # doc: http://timgolden.me.uk/pywin32-docs/win32crypt.html
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


def decrypt_data(data, key):
    try:
        # get the initialization vector
        iv = data[3:15]
        data = data[15:]
        # generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # decrypt password
        return cipher.decrypt(data)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            # not supported
            return ""


def parse_cookies(host_tag):
    # local sqlite Chrome cookie database path
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                           "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
    # copy the file to current directory
    # as the database will be locked if chrome is currently open
    filename = "myparser/Cookies.db"
    if not os.path.isfile(filename):
        # copy file when does not exist in the current directory
        shutil.copyfile(db_path, filename)

    # connect to the database
    db = sqlite3.connect(filename)
    # ignore decoding errors
    db.text_factory = lambda b: b.decode(errors="ignore")
    cursor = db.cursor()
    cursor.execute(f"""
    SELECT host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value
    FROM cookies
    WHERE host_key like '%{host_tag}%'""")

    # get the AES key
    key = get_encryption_key()

    jar = RequestsCookieJar()

    for host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value in cursor.fetchall():
        if not value:
            decrypted_value = decrypt_data(encrypted_value, key)
        else:
            # already decrypted
            decrypted_value = value
        print(f"""
        Host: {host_key}
        Cookie name: {name}
        Cookie value (decrypted): {decrypted_value}
        Creation datetime (UTC): {get_chrome_datetime(creation_utc)}
        Last access datetime (UTC): {get_chrome_datetime(last_access_utc)}
        Expires datetime (UTC): {get_chrome_datetime(expires_utc)}
        ===============================================================
        """)

        jar.set(name, decrypted_value, domain=host_key, path='/')
    # close connection
    db.close()

    # os.remove(filename)

    return jar


if __name__ == "__main__":
    parse_cookies("nhentai.net")

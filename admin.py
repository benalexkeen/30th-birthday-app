import binascii
import getpass
import hashlib
import json
import os

from werkzeug.security import (generate_password_hash,
    check_password_hash)


__here__ = os.path.dirname(__file__)
config_path = os.path.join(__here__, 'config.json')

with open(config_path, 'r') as f:
    config = json.load(f)


def login(username, password):
    user = [x for x in config['admin_users'] if x['username'] == username]
    if not user:
        return False
    else:
        stored_password = user[0]['password']
        return check_password_hash(stored_password, password)


def create_user(username, password):
    hashed_password = generate_password_hash(password)
    if not 'admin_users' in config:
        config['admin_users'] = []
    config['admin_users'].append({
        'username': username,
        'password': hashed_password
    })
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


if __name__ == '__main__':
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    create_user(username, password)

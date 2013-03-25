#!/usr/bin/env python

from __future__ import print_function, with_statement
from contextlib import closing
from email.utils import parsedate
import mailbox, imaplib, os, sqlite3, json, hashlib

OBS_DIR = os.path.join(os.path.expanduser('~'), '.config', 'dnet', 'obs')
HASH_ALGO = hashlib.sha256

class OutboxSyncer(object):
    def __init__(self):
        self.config = load_config()
        self.imap_pool = {}


    def process(self, mbox_filenames):
        try:
            with open_database() as db:
                for mbox_filename in mbox_filenames:
                    mbox = mailbox.mbox(mbox_filename)
                    self.process_mbox(mbox, db)
        finally:
            self.empty_connection_pool()


    def process_mbox(self, mbox, db):
        accounts = self.config['accounts']
        with closing(db.cursor()) as cur:
            for key, msg in mbox.iteritems():
                account, date_time = msg.get_from().split(' ', 1)
                contents = mbox.get_string(key)
                msg_hash = HASH_ALGO(contents).hexdigest()
                params = (msg_hash, account)
                with db:
                    cur.execute('SELECT COUNT(*) FROM messages WHERE hash = ? AND account = ?', params)
                    ((count,),) = cur.fetchall()
                    if count == 0:
                        cur.execute('INSERT INTO messages (hash, account) VALUES (?, ?)', params)
                    else:
                        continue
                try:
                    acc_cfg = accounts[account]
                    imap = self.get_imap_connection(account, acc_cfg)
                    response, _ = imap.append(acc_cfg['folder'], r'\Seen',
                            parsedate(date_time), contents)
                    assert response == 'OK'
                except:
                    with db:
                        cur.execute('DELETE FROM messages WHERE hash = ? AND account = ?', params)
                    raise
                else:
                    print('Appended', msg_hash, 'to', account)
                    with db:
                        cur.execute('UPDATE messages SET success = 1 WHERE hash = ? AND account = ?', params)


    def get_imap_connection(self, name, account):
        conn = self.imap_pool.get(name)
        if conn is None:
            impl = imaplib.IMAP4_SSL if account.get('ssl') else imaplib.IMAP4
            conn = impl(account['host'])
            conn.login(account['user'], account['password'])
            self.imap_pool[name] = conn
        return conn


    def empty_connection_pool(self):
        for conn in self.imap_pool.itervalues():
            try:
                conn.logout()
            except:
                pass


def load_config():
    cfg_filename = os.environ.get('OBS_CONFIG', os.path.join(OBS_DIR, 'obs.json'))
    with file(cfg_filename, 'rb') as cfg_file:
        return json.load(cfg_file)


def open_database():
    if not os.path.exists(OBS_DIR):
        os.makedirs(OBS_DIR)
    db = sqlite3.connect(os.path.join(OBS_DIR, 'obs.db'))
    with db:
        db.execute('''CREATE TABLE IF NOT EXISTS messages
                (hash TEXT, account TEXT, success INTEGER DEFAULT 0,
                PRIMARY KEY (hash, account))''')
    return closing(db)


if __name__ == '__main__':
    import sys
    if any(i in sys.argv for i in ('-h', '--help', '-?', '/?')) or len(sys.argv) < 2:
        print('Usage: {0} <mailbox> [<mailbox2> ...]'.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    OutboxSyncer().process(sys.argv[1:])

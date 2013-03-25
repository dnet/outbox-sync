Outbox Syncer
=============

Outbox Syncer uploads messages from a mbox file into one or more IMAP
mailboxes, optionally sorted by sender addresses. The IMAP accounts can
be configured in `~/.config/dnet/obs/obs.json`, or an alternative path
can be specified in the `OBS_CONFIG` environment variable. See
`obs.sample.json` for the syntax, the source mbox file name(s) can be
passed as command line argument(s).

License
-------

The whole project is available under MIT license.

Dependencies
------------

 - Python 2.x (tested on 2.7.3)

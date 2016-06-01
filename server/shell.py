#!/usr/bin/python
# coding: utf-8
import logging
from ConfigParser import ConfigParser
from cmd import Cmd
from getpass import getpass

from twisted.internet import reactor

from server.spotify_player import Spotify

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    class Shell(Cmd):
        prompt = 'spotify> '
        doc_header = 'Commands'
        logger = logging.getLogger('shell.commander')

        def precmd(self, line):
            if line:
                self.logger.debug('New command: %s', line)
            return line

        def emptyline(self):
            pass

        def __init__(self):
            Cmd.__init__(self)
            cfg = ConfigParser()
            cfg.read("config.ini")
            self.s = Spotify(cfg.items("SPOTIFY"))

        def do_login(self, line):
            username = line
            password = getpass("password: ")
            self.s.login(username, password)

        def do_relogin(self, _):
            self.s.relogin()

        def do_logout(self, _):
            self.s.logout()

        def do_search(self, query):
            self.s.search(query).addCallback(lambda x: self.logger.info(unicode(x)))

        def do_more(self, _):
            self.s.more().addCallback(lambda x: self.logger.info(unicode(x)))

        def do_play(self, uri):
            self.s.play_uri(uri)

        def do_pause(self, _):
            self.s.pause()

        def do_mute(self, _):
            self.s.mute()

        def do_volume(self, percent):
            self.s.set_volume(int(percent))

        def log_deferred(self, d):
            d.addCallback(lambda x: self.logger.info("logged in"))

        def do_EOF(self, _):
            self.s.event_loop.stop()
            reactor.stop()
            print('')
            return True


    reactor.callLater(0, Shell().cmdloop)
    reactor.run()
#!/usr/bin/python
# coding: utf-8
import json
import logging

import subprocess
from ConfigParser import ConfigParser
from cmd import Cmd
from getpass import getpass

from twisted.internet import reactor
from twisted.internet.defer import Deferred

import spotify

logging.basicConfig(level=logging.INFO)


def login_required(f):
    def _check_logged_in(self, *args, **kwargs):
        assert self.logged_in
        return f(self, *args, **kwargs)

    return _check_logged_in


class Spotify(object):
    def __init__(self, config):
        self.config = spotify.Config()
        for param, value in config:
            self.config.__setattr__(param, value)
        self.session = spotify.Session(config=self.config)
        self.logged_in = False

        self.set_volume(90)
        self.query_count = int(self.config.query_count)
        self.query = None

        self.set_signals()

        self.logged_in_deferred = None
        self.logged_out_deferred = None

        try:
            self.audio_driver = spotify.AlsaSink(self.session)
        except ImportError:
            self.logger.warning(
                'No audio sink found; audio playback unavailable.')

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def set_volume(self, percent=None):
        if type(percent) == int and 100 >= percent >= 0:
            self.volume = percent
        try:
            subprocess.call("amixer cset numid=1 -- {0}%".format(self.volume), shell=True)
        except:
            pass

    def unmute(self):
        self.set_volume()

    @staticmethod
    def mute():
        try:
            subprocess.call("amixer cset numid=1 -- 0%")
        except:
            pass

    @login_required
    def search(self, query=''):
        d = Deferred()
        self.query = self.session.search(query, callback=lambda x: d.callback(self.tracks_to_json(x.tracks)),
                                         track_count=self.query_count, album_count=0, artist_count=0, playlist_count=0)
        return d

    @login_required
    def more(self):
        assert self.query
        d = Deferred()
        self.query.more(callback=lambda x: d.callback(self.tracks_to_json(x.tracks)))
        return d

    @login_required
    def play_uri(self, track):
        try:
            track = self.session.get_track(track)
            track.load()
        except (ValueError, spotify.Error) as e:
            return
        self.session.player.load(track)
        self.session.player.play()

    def pause(self):
        self.session.player.play(False)

    def resume(self):
        self.session.player.play()

    def stop(self):
        self.session.player.play(False)
        self.session.player.unload()

    @login_required
    def seek(self, seconds):
        if self.session.player.state is spotify.PlayerState.UNLOADED:
            self.logger.warning('A track must be loaded before seeking')
            return
        self.session.player.seek(int(seconds) * 1000)

    def connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN and self.logged_in_deferred:
            self.logged_in = True
            self.logged_in_deferred.callback(self.logged_in)
            self.logged_in_deferred = None
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT and self.logged_out_deferred:
            self.logged_in = False
            self.logged_out_deferred.callback(self.logged_in)
            self.logged_out_deferred = None

    def end_of_track(self, _):
        self.session.player.play(False)

    def set_signals(self):
        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED, self.connection_state_changed)
        self.session.on(spotify.SessionEvent.END_OF_TRACK, self.end_of_track)

    def login(self, username, password):
        self.session.login(username, password, remember_me=True)
        self.logged_in_deferred = Deferred()
        return self.logged_in_deferred

    def relogin(self):
        self.session.relogin()
        self.logged_in_deferred = Deferred()
        return self.logged_in_deferred

    def forget_me(self):
        self.session.forget_me()

    def logout(self):
        self.session.logout()
        self.logged_out_deferred = Deferred()
        return self.logged_out_deferred

    @staticmethod
    def tracks_to_json(tracks):
        tracks = [
            {"title": unicode(track.name),
             "artists": [unicode(artist.name) for artist in track.artists],
             "time": track.duration / 1000,
             "album": unicode(track.album.name)
             } for track in tracks]
        return json.dumps(tracks, indent=2)


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

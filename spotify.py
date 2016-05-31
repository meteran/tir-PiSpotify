#!/usr/bin/python
# coding: utf-8
import subprocess
import threading
from ConfigParser import ConfigParser

from twisted.internet.defer import Deferred

import spotify


def login_required(f):
    def _check_logged_in(self, *args, **kwargs):
        assert self.logged_in
        f(self, *args, **kwargs)
    return _check_logged_in


class Spotify(object):
    def __init__(self, config):
        self.config = spotify.Config()
        for param, value in config:
            self.config.__setattr__(param, value)
        self.session = spotify.Session(config=self.config)
        self.logged_in = False

        self.set_volume(90)
        self.query_count = self.config.query_count
        self.search = None

        self.set_signals()

        try:
            self.audio_driver = spotify.AlsaSink(self.session)
        except ImportError:
            self.logger.warning(
                'No audio sink found; audio playback unavailable.')

    def set_volume(self, percent=None):
        if type(percent) == int and 100 >= percent >= 0:
            self.volume = percent
        try:
            subprocess.Popen("amixer cset numid=1 -- {0}%".format(self.volume))
        except:
            pass

    @staticmethod
    def mute():
        try:
            subprocess.Popen("amixer cset numid=1 -- 0%")
        except:
            pass

    @login_required
    def search(self, query=''):
        d = Deferred()
        self.search = self.session.search(query, callback=lambda x: d.callback(x.tracks),
                                          track_count=self.query_count, album_count=0, artist_count=0, playlist_count=0)
        return d

    @login_required
    def more(self):
        assert self.search
        d = Deferred()
        self.search.more(callback=lambda x: d.callback(x.tracks))
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
    def do_seek(self, seconds):
        if self.session.player.state is spotify.PlayerState.UNLOADED:
            self.logger.warning('A track must be loaded before seeking')
            return
        self.session.player.seek(int(seconds) * 1000)

    def connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.logged_in = True
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            self.logged_in = False

    def end_of_track(self, _):
        self.session.player.play(False)

    def set_signals(self):
        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.connection_state_changed)
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK, self.end_of_track)


if __name__ == "__main__":
    cfg = ConfigParser()
    cfg.read("config.ini")
    s = Spotify(cfg.items("SPOTIFY"))


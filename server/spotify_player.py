#!/usr/bin/python
# coding: utf-8
import json
import subprocess

import spotify
from twisted.internet import reactor
from twisted.internet.defer import Deferred


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

        self.audio_driver = spotify.AlsaSink(self.session)

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
        assert self.session.player.state is not spotify.PlayerState.UNLOADED
        self.session.player.seek(int(seconds) * 1000)

    def connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN and self.logged_in_deferred:
            self.logged_in = True
            reactor.callFromThread(self.logged_in_deferred.callback, self.logged_in)
            self.logged_in_deferred = None
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT and self.logged_out_deferred:
            self.logged_in = False
            reactor.callFromThread(self.logged_out_deferred.callback, self.logged_in)
            self.logged_out_deferred = None

    def end_of_track(self, _):
        # self.session.player.play(False)
        pass

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
             "album": unicode(track.album.name),
             "uri": unicode(track.link.uri)
             } for track in tracks]
        return json.dumps(tracks, indent=2)

    @login_required
    def get_playlists(self):
        d = Deferred()
        if self.session.playlist_container.is_loaded:
            print "loaded"
            reactor.callLater(0, d.callback, self.session.playlist_container)
        else:
            print "not loaded"
            self.session.playlist_container.off(spotify.PlaylistContainerEvent.CONTAINER_LOADED)
            print "asd"
            self.session.playlist_container.on(spotify.PlaylistContainerEvent.CONTAINER_LOADED, lambda x: d.callback(x))
            print "afdsa"
            self.session.playlist_container.load()
        print "fsadfsd"
        return d

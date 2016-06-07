#!/usr/bin/python
# coding: utf-8
from ConfigParser import ConfigParser

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from txrestapi.resource import APIResource
from txrestapi.methods import GET,POST

from spotify_player import Spotify

import logging
import json

DEBUG = False


def debug(*args):
    if DEBUG:
        for arg in args:
            print arg,

class Discover(DatagramProtocol):
    def __init__(self, config, server_address="0.0.0.0"):
        self.config = config
        self.server_address = "%s#%s:%s" % (
            self.config.get("MULTICAST", "prefix"), server_address, self.config.get("SERVER", "port"))
        self.group_address = self.config.get("MULTICAST", "group")
        self.broadcast_address = (self.group_address, self.config.getint("MULTICAST", "broadcast_port"))
        self.broadcast_interval = self.config.getint("MULTICAST", "interval")

    def startProtocol(self):
        self.transport.setTTL(5)
        self.transport.joinGroup(self.group_address)
        self.chronic_send_address()

    def send_address(self):
        self.transport.write(self.broadcast_address, self.broadcast_address)

    def chronic_send_address(self):
        self.send_address()
        reactor.callLater(self.broadcast_interval, self.chronic_send_address())

    def datagramReceived(self, datagram, addr):
        self.send_address()
        print datagram, addr


def wrong_request(request):
    request.setResponseCode(401)
    return ""


class Playlist(Resource):
    isLeaf = True
    def __init__(self, spotify):
        Resource.__init__(self)
        self.spotify = spotify

    def render_GET(self, request):
        if len(request.postpath) == 0:
            return self.spotify.get_all_albums
        if len(request.postpath) == 1:
            return self.spotify.get_album(request.postpath[0])
        return wrong_request(request)


class Player(APIResource):
    def __init__(self, spotify):
        APIResource.__init__(self)
        self.spotify = spotify

    @GET('^/login')
    def get_login(self, request):
        "Check if and, which user is logged in"
        request.setHeader("Content-Type", "application/json")
        response = {'logged_in': self.spotify.logged_in}
        if self.spotify.logged_in:
            response['username'] = self.spotify.session.remembered_user_name
        return json.dumps(response)

    @POST('^/login')
    def login_as(self, request):
        "Login as username:password"
        username = request.args['username'][0]
        password = request.args['password'][0]
        def delayedResponse(logged_in):
            response = self.get_login(request)
            request.write(response)
            request.finish()
        # Deferred work like shit now.
        self.spotify.login(username,password).addCallback(delayedResponse)
        return NOT_DONE_YET

    @GET('^/logout')
    @POST('^/logout')
    def logout(self, request):
        def delayed(logged_in):
            request.setHeader("Content-Type", "application/json")
            request.write(json.dumps({'logged_in':logged_in}))
            request.finish()
        self.spotify.logout().addCallback(delayed)
        return NOT_DONE_YET

    @GET('^/playlists$')
    def get_all_playlists(self, request):
        "List all playlists"
        def callback(playlist_json):
            request.setHeader("Content-Type", "application/json")
            request.write(playlist_json)
            request.finish()
        self.spotify.get_playlists().addCallback(callback)
        return NOT_DONE_YET

    @GET('^/playlists/(?P<index>[^/]+)')
    @GET('^/playlists/(?P<index>[^/]+)/tracks')
    def get_playlist(self, request, index):
        "Get nth playlist"
        index = int(index)
        request.setHeader("Content-Type", "application/json")
        try:
            return self.spotify.get_playlist_tracks(index)
        except IndexError:
            request.setResponseCode(404)
            return json.dumps({'error':'no playlist with this index', 'index':index})

    def get_state(self, response=None):
        if response is None:
            response = {}
        response['state'] = self.spotify.session.player.state
        return response

    def get_volume(self, response=None):
        if response is None:
            response = {}
        response['volume']=self.spotify.volume
        return response

    @GET('^/status')
    def get_playback_status(self, request):
        request.setHeader("Content-Type", "application/json")
        response = self.get_state()
        response = self.get_volume(response)
        return json.dumps(response)

    @GET('^/play')
    @POST('^/play')
    def play(self, request):
        request.setHeader("Content-Type", "application/json")
        if 'uri' in request.args:
            self.spotify.play_uri(request.args['uri'][0])
        else:
            self.spotify.resume()
        return json.dumps(self.get_state())

    @GET('^/pause')
    @POST('^/pause')
    def pause(self, request):
        request.setHeader("Content-Type", "application/json")
        self.spotify.pause()
        return json.dumps(self.get_state())


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('spotify_server')

cfg = ConfigParser()
cfg.read("config.ini")

spotify = Spotify(cfg.items("SPOTIFY"))
try:
    spotify.relogin()
    logger.info("Logged in as '%s'", spotify.session.remembered_user_name)
except:
    logger.info("Not logged in.")

# root = Resource()
# root.putChild("playlist", Playlist(spotify))
# root.putChild("player", Player(spotify))

player = Player(spotify)
site = Site(player)
reactor.listenTCP(cfg.getint("SERVER", "port"), site)
reactor.run()

if __name__ == "__main__":
    DEBUG = False
    discover = Discover(cfg)

#!/usr/bin/python
# coding: utf-8
from ConfigParser import ConfigParser

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from txrestapi.resource import APIResource
from txrestapi.methods import GET,POST
from zeroconf import ServiceInfo, Zeroconf

from spotify_player import Spotify
from converters import json_resource, write_json, serialize_playlists, serialize_tracks, serialize_track

import logging
import socket

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

    def _get_state(self, response=None):
        if response is None:
            response = {}
        response['state'] = self.spotify.session.player.state
        return response

    def _get_volume(self, response=None):
        if response is None:
            response = {}
        response['volume'] = self.spotify.volume
        return response

    def _get_login(self, response=None):
        if response is None:
            response = {}
        response['logged_in']= self.spotify.logged_in
        if self.spotify.logged_in:
            response['username'] = self.spotify.session.remembered_user_name
        return response

    @GET('^/playlists/(?P<pl_id>[^/]+)/tracks/(?P<track_id>[^/]+)/play')
    @json_resource
    def play_track(self, request, pl_id, track_id):
        try:
            playlist = self.spotify.get_playlist(int(pl_id))
            track = playlist.tracks[int(track_id)]
            self.spotify.play(track)
            return {
                'now_playing': serialize_track(track, playlist_name=playlist.name)
            }
        except IndexError:
            request.setResponseCode(404)

    @GET('^/playlists/(?P<pl_id>[^/]+)/tracks/(?P<track_id>[^/]+)')
    @json_resource
    def show_track(self, request, pl_id, track_id):
        request.setHeader("Content-Type", "application/json")
        try:
            playlist = self.spotify.get_playlist(int(pl_id))
            track = playlist.tracks[int(track_id)]
            return serialize_track(track, playlist_name=playlist.name)
        except IndexError:
            request.setResponseCode(404)

    @GET('^/playlists/(?P<index>[^/]+)')
    @GET('^/playlists/(?P<index>[^/]+)/tracks')
    @json_resource
    def get_playlist(self, request, index):
        "Get nth playlist"
        try:
            playlist = self.spotify.get_playlist(int(index))
            return serialize_tracks(playlist.tracks, playlist_name=playlist.name)
        except IndexError:
            request.setResponseCode(404)
            return {'error': 'no playlist with this index', 'index': index}

    @GET('^/playlists')
    def get_all_playlists(self, request):
        "List all playlists"
        def callback(playlists):
            write_json(request, serialize_playlists(playlists))
            request.finish()
        self.spotify.get_playlists().addCallback(callback)
        return NOT_DONE_YET

    @GET('^/play')
    @POST('^/play')
    @json_resource
    def play(self, request):
        if 'uri' in request.args:
            self.spotify.play_uri(request.args['uri'][0])
        else:
            self.spotify.resume()
        return self._get_state()

    @GET('^/pause')
    @POST('^/pause')
    @json_resource
    def pause(self, request):
        self.spotify.pause()
        return self._get_state()

    @GET('^/login')
    @json_resource
    def get_login(self, request):
        "Check if and, which user is logged in"
        return self._get_login()

    @POST('^/login')
    def login_as(self, request):
        "Login as username:password"
        username = request.args['username'][0]
        password = request.args['password'][0]
        def delayedResponse(logged_in):
            request.write(self.get_login(request)) #also sets headers
            request.finish()
        # Deferred work like shit now.
        self.spotify.login(username,password).addCallback(delayedResponse)
        return NOT_DONE_YET

    @GET('^/logout')
    @POST('^/logout')
    def logout(self, request):
        def delayed(logged_in):
            write_json(request,{'logged_out':not logged_in})
            request.finish()
        self.spotify.logout().addCallback(delayed)
        return NOT_DONE_YET

    @GET('^/status')
    @GET('^/')
    @json_resource
    def get_status(self, request):
        response = self._get_state()
        response = self._get_volume(response)
        response = self._get_login(response)
        return response

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('spotify_server')
    # logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    # read config
    cfg = ConfigParser()
    cfg.read("config.ini")
    # setup spotify and API
    spotify = Spotify(cfg.items("SPOTIFY"))
    try:
        spotify.relogin()
        logger.info("Logged in as '%s'", spotify.session.remembered_user_name)
    except:
        logger.info("Not logged in.")
    player = Player(spotify)
    site = Site(player)
    # setup and register service
    host = socket.gethostbyname(socket.gethostname())
    port = cfg.getint("SERVER", "port")
    service_info = ServiceInfo(
        type='_http._tcp.local.',
        name='pispotify._http._tcp.local.',
        address=socket.inet_aton(host), port=port,
        properties={'version':'0.1'}
    )
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    logger.info("Listening on %s:%d",host,port)
    reactor.listenTCP(port, site)
    try:
        reactor.run()
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(service_info)
        zeroconf.close()

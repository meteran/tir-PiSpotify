#!/usr/bin/python
# coding: utf-8
from ConfigParser import ConfigParser

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.resource import Resource
from twisted.web.server import Site

from spotify_player import Spotify

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
        self.broadcast_address = (self.group_address, self.config.getint("MULTICAST", "message_port"))
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


class Player(Resource):
    pass


cfg = ConfigParser()
cfg.read("config.ini")
spotify = Spotify(cfg.items("SPOTIFY"))
root = Resource()
root.putChild("playlist", Playlist(spotify))
root.putChild("player", Player(spotify))

site = Site(root)

if __name__ == "__main__":
    DEBUG = False
    debug()
    discover = Discover(cfg)

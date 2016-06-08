import json

from functools import wraps

def json_resource(func):
    "Wrap request handler output in json"
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        request.setHeader("Content-Type", "application/json")
        return json.dumps(func(self,request,*args,**kwargs), indent=2)
    return wrapper

def write_json(request, object):
    request.setHeader("Content-Type", "application/json")
    request.write(json.dumps(object, indent=2))

def serialize_playlists(playlists):
    return [{"name": playlist.name, "id": index} for index, playlist in enumerate(playlists)]

def serialize_tracks(tracks, playlist_name=""):
    return {'music': [serialize_track(track, playlist_name) for track in tracks]}

def serialize_track(track, playlist_name=""):
    # with open("/tmp/static/"+str(track.link.uri), 'w') as f:
    #     f.write(track.album.cover().data)
    return {
        "title": unicode(track.name),
        "album": unicode(track.album.name),
        "artist": ", ".join(unicode(artist.name) for artist in track.artists),
        "duration": track.duration / 1000,
        "uri": unicode(track.link.uri),
        "playlist": unicode(playlist_name),
        "image": "/static/cover.jpg",
    }
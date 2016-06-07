package com.example.android.uamp.model;

import android.support.v4.media.MediaMetadataCompat;
import android.util.Log;

import com.example.android.uamp.utils.LogHelper;
import com.example.android.uamp.utils.ServiceDiscoveryHelper;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URL;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.Iterator;

public class PiSpotifySource implements MusicProviderSource {
    private static final String TAG = LogHelper.makeLogTag(PiSpotifySource.class);

    private static final String JSON_MUSIC = "music";
    private static final String JSON_TITLE = "title";
    private static final String JSON_ALBUM = "album";
    private static final String JSON_ARTIST = "artist";
    private static final String JSON_IMAGE = "image";
    private static final String JSON_PLAYLIST = "playlist";
    private static final String JSON_DURATION = "duration";
    private final ServiceDiscoveryHelper discoveryHelper;

    public PiSpotifySource(ServiceDiscoveryHelper discoveryHelper) {
        this.discoveryHelper = discoveryHelper;
    }

    @Override
    public Iterator<MediaMetadataCompat> iterator() {
        try {
            String catalogUrl = "http://" + discoveryHelper.getService().getHost().getHostName() + "/music.json";
            Log.d(TAG, "iterator " + catalogUrl);
            int slashPos = catalogUrl.lastIndexOf('/');
            String path = catalogUrl.substring(0, slashPos + 1);
            JSONObject jsonObj = fetchJSONFromUrl(catalogUrl);
            ArrayList<MediaMetadataCompat> tracks = new ArrayList<>();
            if (jsonObj != null) {
                JSONArray jsonTracks = jsonObj.getJSONArray(JSON_MUSIC);

                if (jsonTracks != null) {
                    for (int j = 0; j < jsonTracks.length(); j++) {
                        tracks.add(buildFromJSON(jsonTracks.getJSONObject(j), path));
                    }
                }
            }
            return tracks.iterator();
        } catch (JSONException e) {
            LogHelper.e(TAG, e, "Could not retrieve music list");
            throw new RuntimeException("Could not retrieve music list", e);
        }
    }

    private MediaMetadataCompat buildFromJSON(JSONObject json, String basePath) throws JSONException {
        String title = json.getString(JSON_TITLE);
        String album = json.getString(JSON_ALBUM);
        String artist = json.getString(JSON_ARTIST);
        String playlist = json.getString(JSON_PLAYLIST);
        String iconUrl = json.getString(JSON_IMAGE);
        int duration = json.getInt(JSON_DURATION) * 1000; //ms
        LogHelper.d(TAG, "Found music track: ", json);


        if (!iconUrl.startsWith("http")) {
            iconUrl = basePath + iconUrl;
        }


        // Since we don't have a unique ID in the server, we fake one using the hashcode of the metadata
        String id = String.valueOf(json.toString().hashCode());

        // Adding the music source to the MediaMetadata (and consequently using it in the
        // mediaSession.setMetadata) is not a good idea for a real world music app, because
        // the session metadata can be accessed by notification listeners. This is done in this
        // sample for convenience only.
        return new MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_MEDIA_ID, id)
                .putString(MediaMetadataCompat.METADATA_KEY_ALBUM, album)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, artist)
                .putLong(MediaMetadataCompat.METADATA_KEY_DURATION, duration)
                .putString(MediaMetadataCompat.METADATA_KEY_COMPILATION, playlist)
                .putString(MediaMetadataCompat.METADATA_KEY_ALBUM_ART_URI, iconUrl)
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, title)
                .build();
    }

    /**
     * Download a JSON file from a server, parse the content and return the JSON
     * object.
     *
     * @return result JSONObject containing the parsed representation.
     */
    private JSONObject fetchJSONFromUrl(String urlString) throws JSONException {
        BufferedReader reader = null;
        try {
            URLConnection urlConnection = new URL(urlString).openConnection();
            reader = new BufferedReader(new InputStreamReader(
                    urlConnection.getInputStream(), "utf-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return new JSONObject(sb.toString());
        } catch (JSONException e) {
            throw e;
        } catch (Exception e) {
            LogHelper.e(TAG, "Failed to parse the json for media list", e);
            return null;
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
    }
}

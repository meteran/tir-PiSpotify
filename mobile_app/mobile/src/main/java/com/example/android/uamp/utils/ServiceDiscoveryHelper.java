package com.example.android.uamp.utils;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.util.Log;

import com.example.android.uamp.MusicService;

public class ServiceDiscoveryHelper {


    public static final String SERVICE_TYPE = "_http._tcp.";
    public static final String SERVICE_NAME = "pispotify";
    private static final String TAG = LogHelper.makeLogTag(ServiceDiscoveryHelper.class);
    private final NsdManager mNsdManager;


    private final NsdManager.DiscoveryListener discoveryListener =
            new NsdManager.DiscoveryListener() {

                @Override
                public void onDiscoveryStarted(String regType) {
                    Log.d(TAG, "Service discovery started");
                }

                @Override
                public void onServiceFound(NsdServiceInfo service) {
                    Log.d(TAG, "Service discovery success " + service);
                    if (!service.getServiceType().equals(SERVICE_TYPE)) {
                        Log.d(TAG, "Unknown Service Type: " + service.getServiceType());
                    } else if (service.getServiceName().equals(SERVICE_NAME)) {
                        Log.d(TAG, service.toString());
                        mNsdManager.resolveService(service, mResolveListener);
                    }
                }

                @Override
                public void onServiceLost(NsdServiceInfo service) {
                    // When the network service is no longer available.
                    // Internal bookkeeping code goes here.
                    Log.e(TAG, "service lost " + service.getServiceName());
                    if (SERVICE_NAME.equals(service.getServiceName())) {
                        Log.e(TAG, "pispotify service no longer available");
                        mService = null;
                    }
                }

                @Override
                public void onDiscoveryStopped(String serviceType) {
                    Log.i(TAG, "Discovery stopped: " + serviceType);
                }

                @Override
                public void onStartDiscoveryFailed(String serviceType, int errorCode) {
                    Log.e(TAG, "Discovery failed: Error code: " + errorCode);
                    mNsdManager.stopServiceDiscovery(this);
                }

                @Override
                public void onStopDiscoveryFailed(String serviceType, int errorCode) {
                    Log.e(TAG, "Discovery failed: Error code: " + errorCode);
                    mNsdManager.stopServiceDiscovery(this);
                }
            };
    private final MusicService musicService;
    private NsdServiceInfo mService;

    private final NsdManager.ResolveListener mResolveListener = new NsdManager.ResolveListener() {

        @Override
        public void onResolveFailed(NsdServiceInfo serviceInfo, int errorCode) {
            Log.e(TAG, "Resolve failed " + errorCode);
        }

        @Override
        public void onServiceResolved(NsdServiceInfo serviceInfo) {
            Log.e(TAG, "Resolve Succeeded. " + serviceInfo);
            mService = serviceInfo;
            Log.i(TAG, "resolved " + mService.getHost().getHostName() + ":" + mService.getPort());
            //musicService.getmMusicProvider().retrieveMediaAsync(null);
            musicService.notifyChildrenChanged("__ROOT__");
        }
    };


    public ServiceDiscoveryHelper(Context mContext, MusicService musicService) {
        this.musicService = musicService;
        mNsdManager = (NsdManager) mContext.getSystemService(Context.NSD_SERVICE);
        mNsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener);
    }

    public NsdServiceInfo getService() {
        return mService;
    }
}

#!/usr/bin/env python

import logging
import socket
import sys
from time import sleep

from zeroconf import ServiceInfo, Zeroconf

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)

    desc = {'version': '0.1'}
    info = ServiceInfo("_http._tcp.local.",
                       "pispotify._http._tcp.local.",
                       socket.inet_aton("192.168.0.17"), 80, 0, 0, desc) #use the right ip
    
    zeroconf = Zeroconf()
    print("Registration of a service, press Ctrl-C to exit...")
    zeroconf.register_service(info)
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        zeroconf.unregister_service(info)
        zeroconf.close()
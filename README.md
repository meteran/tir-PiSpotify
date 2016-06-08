PiSpotify
=========
Zdalny odtwarzacz muzyki ze spotify zbudowany w oparciu o RaspberryPi

### 1. Zasada działania:
 Aplikacja mobilna łączy się serwerem uruchomionym w sieci lokalnej.
 Serwer umożliwia odtwarzanie muzyki.
 Dzięki temu możemy sterować muzyką, która jest odtwarzana w innym pomieszczeniu w domu.

### 2. Składowe projektu
 * Serwer uruchomiony na RaspberryPi.
 * Aplikacja mobilna uruchomiona na telefonie z systemem Android.

### 3. Serwer
 Serwer jest napisany w twisted i udostępnia REST API.
 Do odtwarzania muzyki skorzystaliśmy z biblioteki [pyspotify](https://pyspotify.mopidy.com/en/latest/),
 która z kolei korzysta z libspotify

### 4. Aplikacja mobilna
 (opisana w podkatalogu `mobile`)

### 5. Serwis "autodiscover"
 Do wykrywania adresu serwera przez aplikację mobilną użyliśmy:
 * po stronie serwera [zeroconf](https://pypi.python.org/pypi/zeroconf)
 * po stronie aplikacji [NSD](https://developer.android.com/training/connect-devices-wirelessly/nsd.html)


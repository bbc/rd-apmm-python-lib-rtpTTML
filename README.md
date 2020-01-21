# rtpTTML

A library for transmitting/receiving TTML documents over RTP.

## What rtpTTML does/doesn't do
This library is very minimal. It takes documents as strings, encodes them as an RTP payload, and sends them over UDP. It's doesn't currently implement any of the RTP control mechanisms, SDP, FEC etc. PRs welcome if you want to add these features!

This library makes use of [RTP](https://github.com/bbc/rd-apmm-python-lib-rtp) and [rtpPayload_ttml](https://github.com/bbc/rd-apmm-python-lib-rtpPayload_ttml) for encoding/decoding the payload bitstreams.

## Example usage
There are fully functional transmitter and receiver examples in the [examples directory](https://github.com/bbc/rd-apmm-python-lib-rtpTTML/tree/master/examples). The bare minimum usage is as follows.

```python
from rtpTTML import TTMLReceiver


def processDoc(doc, timestamp):
    print("{}\n".format(doc))

port = 12345
client = TTMLReceiver(port, processDoc)
client.run()
```

```python
from time import sleep
from datetime import datetime
from rtpTTML import TTMLTransmitter


address = "127.0.0.1"
port = 12345
server = TTMLTransmitter(address, port)

while True:
    now = datetime.now()
    doc = generateDoc(server.nextSeqNum, str(now))

    server.sendDoc(doc, now)
    sleep(1)
```

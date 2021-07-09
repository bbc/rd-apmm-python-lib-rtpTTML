# rtpTTML

A library for transmitting/receiving TTML documents over RTP as per [RFC 8759](https://datatracker.ietf.org/doc/rfc8759/).

## What rtpTTML does/doesn't do
This library is very minimal. It takes documents as strings, encodes them as an RTP payload, and sends them over UDP. It's doesn't currently implement any of the RTP control mechanisms, SDP, FEC, document validation, document rendering etc. PRs welcome if you want to add these features!

This library makes use of [RTP](https://github.com/bbc/rd-apmm-python-lib-rtp) and [rtpPayload_ttml](https://github.com/bbc/rd-apmm-python-lib-rtpPayload_ttml) for encoding/decoding the payload bitstreams.

## Installation

```bash
pip install rtpTTML
```

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

with TTMLTransmitter(address, port) as tx:
    while True:
        docStr = generateDoc(tx.nextSeqNum)
        nowTime = datetime.now()

        tx.sendDoc(docStr, nowTime)
        sleep(1)
```

## Debugging
If you are looking to debug RTP TTML packets on the wire, you might be interested in the wireshark disector available [here](https://github.com/bbc/rd-apmm-wireshark-rtpTTML).

## Contributing
We desire that contributors of pull requests have signed, and submitted via email, a [Contributor Licence Agreement (CLA)](http://www.bbc.co.uk/opensource/cla/rfc-8759-cla.docx), which is based on the Apache CLA.

The purpose of this agreement is to clearly define the terms under which intellectual property has been contributed to the BBC and thereby allow us to defend the project should there be a legal dispute regarding the software at some future time.

If you haven't signed and emailed the agreement yet then the project owners will contact you using the contact info with the pull request.

## License 
See [LICENSE](LICENSE).
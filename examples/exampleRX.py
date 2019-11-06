import asyncio
import argparse
from rtpTTML import TTMLClient  # type: ignore


class Receiver:
    def __init__(self, port):
        self.client = TTMLClient(port, self.processDoc)

    def processDoc(self, doc, timestamp):
        print(doc)

    def run(self):
        self.client.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Example TTML RTP receiver.')
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        help='receiver port',
        required=True)
    args = parser.parse_args()

    rx = Receiver(args.port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(rx.run())
    loop.close()

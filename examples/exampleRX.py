import asyncio
import argparse
from rtpTTML import TTMLReceiver  # type: ignore


class Receiver:
    def __init__(self, port: int):
        self.receiver = TTMLReceiver(port, self.processDoc)

    def processDoc(self, doc: str, timestamp: int) -> None:
        print("{}\n".format(doc))

    async def run(self) -> None:
        self.receiver.run()


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

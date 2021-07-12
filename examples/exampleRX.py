# James Sandford, copyright BBC 2020
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import argparse
from rtpTTML import TTMLReceiver


class Receiver:
    def __init__(self, port: int, encoding: str) -> None:
        self.receiver = TTMLReceiver(port, self.processDoc, encoding=encoding)

    def processDoc(self, doc: str, timestamp: int) -> None:
        print("{}\n".format(doc))

    def stop(self) -> None:
        self.receiver.async_close()

    async def run(self) -> None:
        await self.receiver.async_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Example TTML RTP receiver.')
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        help='receiver port',
        required=True)
    parser.add_argument(
        '-e',
        '--encoding',
        type=str,
        default="UTF-8",
        help='Character encoding of document. One of UTF-8, UTF-16, UTF-16LE, '
             'and UTF-16BE (default: UTF-8)',
        required=False)
    args = parser.parse_args()

    rx = Receiver(args.port, encoding=args.encoding)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(rx.run())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    rx.stop()
    loop.close()

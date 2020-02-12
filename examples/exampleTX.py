from datetime import datetime
from uuid import uuid4, UUID
import asyncio
import argparse
from lxml import etree
from rtpTTML import TTMLTransmitter  # type: ignore


class DocGen:
    def __init__(self, flowID: UUID) -> None:
        self.flowID = str(flowID)

    def generateDoc(self, seqNum: int, text: str) -> str:
        NSMAP = {
            "tt": "http://www.w3.org/ns/ttml",
            "xmlns": "http://www.w3.org/XML/1998/namespace",
            "ebuttExt": "urn:ebu:tt:extension",
            "ttp": "http://www.w3.org/ns/ttml#parameter",
            "tts": "http://www.w3.org/ns/ttml#styling",
            "ebuttm": "urn:ebu:tt:metadata"
        }
        bNSMAP = {k: "{{{}}}".format(NSMAP[k]) for k in NSMAP}

        tt = etree.Element(
            bNSMAP["tt"] + "tt",
            nsmap=NSMAP,
            attrib={
                bNSMAP["ttp"] + "timeBase": "media",
                bNSMAP["ttp"] + "cellResolution": "50 30",
                bNSMAP["tts"] + "extent": "1920px 1080px",
                bNSMAP["ebuttm"] + "sequenceIdentifier": self.flowID,
                bNSMAP["ebuttm"] + "sequenceNumber": str(seqNum)})

        head = etree.SubElement(tt, bNSMAP["tt"] + "head")
        metadata = etree.SubElement(head, bNSMAP["tt"] + "metadata")
        docMetadata = etree.SubElement(
            metadata, bNSMAP["ebuttm"] + "documentMetadata")

        ebuttVer = etree.SubElement(
            docMetadata,
            bNSMAP["ebuttm"] + "documentEbuttVersion")
        ebuttVer.text = "v1.0"

        styling = etree.SubElement(head, bNSMAP["tt"] + "styling")

        etree.SubElement(
            styling,
            bNSMAP["tt"] + "style",
            attrib={
                bNSMAP["xmlns"] + "id": "defaultStyle",
                bNSMAP["tts"] + "fontFamily": "monospaceSansSerif",
                bNSMAP["tts"] + "fontSize": "1c 2c",
                bNSMAP["tts"] + "textAlign": "center",
                bNSMAP["tts"] + "color": "white",
                bNSMAP["tts"] + "backgroundColor": "black"})

        layout = etree.SubElement(head, bNSMAP["tt"] + "layout")
        etree.SubElement(
            layout,
            bNSMAP["tt"] + "region",
            attrib={
                bNSMAP["xmlns"] + "id": "bottom",
                bNSMAP["tts"] + "origin": "10%% 10%%",
                bNSMAP["tts"] + "extent": "80%% 80%%",
                bNSMAP["tts"] + "displayAlign": "after"})

        body = etree.SubElement(
            tt, bNSMAP["tt"] + "body", attrib={"dur": "00:00:10"})

        div = etree.SubElement(
            body, bNSMAP["tt"] + "div", attrib={"style": "defaultStyle"})

        p = etree.SubElement(
            div,
            bNSMAP["tt"] + "p",
            attrib={
                bNSMAP["xmlns"] + "id": "sub",
                "region": "bottom"})

        span = etree.SubElement(
            p,
            bNSMAP["tt"] + "span")
        span.text = text

        return etree.tostring(tt, encoding="unicode")


class Transmitter:
    def __init__(
       self, address: str, port: int, encoding: str, bom: bool) -> None:
        self._address = address
        self._port = port
        self._encoding = encoding
        self._bom = bom
        flowid = uuid4()
        self._docGen = DocGen(flowid)
        self._running = False

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        async with TTMLTransmitter(
                self._address,
                self._port,
                encoding=self._encoding,
                bom=self._bom
           ) as transmitter:
            while self._running:
                now = datetime.now()
                doc = self._docGen.generateDoc(
                    transmitter.nextSeqNum, str(now))

                await transmitter.sendDoc(doc, now)
                await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Example TTML RTP transmitter.')
    parser.add_argument(
        '-i',
        '--ip_address',
        type=str,
        help='receiver ip address',
        required=True)
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
    parser.add_argument(
        '-b',
        '--bom',
        type=bool,
        default=False,
        help='Include Byte Order Mark at start of of document',
        required=False)
    args = parser.parse_args()

    tx = Transmitter(args.ip_address, args.port, args.encoding, args.bom)

    loop = asyncio.get_event_loop()
    task = loop.create_task(tx.run())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    tx.stop()
    loop.run_until_complete(task)
    loop.close()

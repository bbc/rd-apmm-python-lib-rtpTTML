from datetime import datetime
from uuid import uuid4, UUID
import asyncio
import argparse
from lxml import etree
from rtpTTML import TTMLServer  # type: ignore


class DocGen:
    def __init__(self, flowID: UUID):
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
                bNSMAP["xmlns"] + "lang": "en",
                bNSMAP["ttp"] + "timeBase": "clock",
                bNSMAP["ttp"] + "clockMode": "utc",
                bNSMAP["ttp"] + "cellResolution": "50 30",
                bNSMAP["ttp"] + "dropMode": "nonDrop",
                bNSMAP["ttp"] + "markerMode": "discontinuous",
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

        numSubs = etree.SubElement(
            docMetadata,
            bNSMAP["ebuttm"] + "documentTotalNumberOfSubtitles")
        numSubs.text = "1"

        maxChar = etree.SubElement(
            docMetadata,
            bNSMAP["ebuttm"] +
            "documentMaximumNumberOfDisplayableCharacterInAnyRow")
        maxChar.text = "40"

        country = etree.SubElement(
            docMetadata,
            bNSMAP["ebuttm"] + "documentCountryOfOrigin")
        country.text = "gb"

        styling = etree.SubElement(head, bNSMAP["tt"] + "styling")

        etree.SubElement(
            styling,
            bNSMAP["tt"] + "style",
            attrib={
                bNSMAP["xmlns"] + "id": "defaultStyle",
                bNSMAP["tts"] + "fontFamily": "monospaceSansSerif",
                bNSMAP["tts"] + "fontSize": "1c 1c",
                bNSMAP["tts"] + "lineHeight": "normal",
                bNSMAP["tts"] + "textAlign": "center",
                bNSMAP["tts"] + "color": "white",
                bNSMAP["tts"] + "backgroundColor": "transparent",
                bNSMAP["tts"] + "fontStyle": "normal",
                bNSMAP["tts"] + "fontWeight": "normal",
                bNSMAP["tts"] + "textDecoration": "none"})

        etree.SubElement(
            styling,
            bNSMAP["tt"] + "style",
            attrib={
                bNSMAP["xmlns"] + "id": "whiteOnBlack",
                bNSMAP["tts"] + "color": "white",
                bNSMAP["tts"] + "backgroundColor": "black",
                bNSMAP["tts"] + "fontSize": "1c 2c"})

        etree.SubElement(
            styling,
            bNSMAP["tt"] + "style",
            attrib={
                bNSMAP["xmlns"] + "id": "textCenter",
                bNSMAP["tts"] + "textAlign": "center"})

        layout = etree.SubElement(head, bNSMAP["tt"] + "layout")
        etree.SubElement(
            layout,
            bNSMAP["tt"] + "region",
            attrib={
                bNSMAP["xmlns"] + "id": "bottom",
                bNSMAP["tts"] + "origin": "10%% 10%%",
                bNSMAP["tts"] + "extent": "80%% 80%%",
                bNSMAP["tts"] + "padding": "0c",
                bNSMAP["tts"] + "displayAlign": "after",
                bNSMAP["tts"] + "writingMode": "lrtb"})

        body = etree.SubElement(
            tt, bNSMAP["tt"] + "body", attrib={"dur": "00:00:10"})

        div = etree.SubElement(
            body, bNSMAP["tt"] + "div", attrib={"style": "defaultStyle"})

        p = etree.SubElement(
            div,
            bNSMAP["tt"] + "p",
            attrib={
                bNSMAP["xmlns"] + "id": "sub2",
                "style": "textCenter",
                "region": "bottom"})

        span = etree.SubElement(
            p,
            bNSMAP["tt"] + "span",
            attrib={"style": "whiteOnBlack"})
        span.text = text

        return etree.tostring(tt, encoding="unicode")


class Transmitter:
    def __init__(self, address: str, port: int):
        self.flowID = uuid4()
        self.pGen = DocGen(self.flowID)
        self.server = TTMLServer(address, port)

    async def run(self) -> None:
        while True:
            now = datetime.now()
            doc = self.pGen.generateDoc(self.server.nextSeqNum, str(now))

            self.server.sendDoc(doc, now)
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
    args = parser.parse_args()

    tx = Transmitter(args.ip_address, args.port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(tx.run())
    loop.close()

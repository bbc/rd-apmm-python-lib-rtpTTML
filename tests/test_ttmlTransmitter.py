#!/usr/bin/python
#
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

from unittest import TestCase, mock
from unittest.mock import MagicMock
from hypothesis import given, strategies as st  # type: ignore
from rtpPayload_ttml import (
    RTPPayload_TTML, SUPPORTED_ENCODINGS, utfEncode)
from rtpPayload_ttml.utfUtils import BOMS

from rtpTTML import TTMLTransmitter
import asyncio


class TestTTMLTransmitter (TestCase):
    def setUp(self):
        self.transmitter = TTMLTransmitter("", 0)

    def setup_example(self):
        self.setUp()

    @given(
        st.text(min_size=1),
        st.integers(min_value=4))
    def test_fragmentDoc(self, doc, maxLen):
        fragments = self.transmitter._fragmentDoc(doc, maxLen)

        reconstructedDoc = ""
        for fragment in fragments:
            self.assertLessEqual(len(utfEncode(fragment)), maxLen)
            reconstructedDoc += fragment

        self.assertEqual(doc, reconstructedDoc)

    @given(st.datetimes())
    def test_datetimeToRTPTs(self, time):
        rtpTs = self.transmitter._datetimeToRTPTs(time)

        self.assertIsInstance(rtpTs, int)
        self.assertGreaterEqual(rtpTs, 0)
        self.assertLess(rtpTs, 2**32)

    @given(st.tuples(
        st.text(min_size=1),
        st.sampled_from(SUPPORTED_ENCODINGS),
        st.booleans(),
        st.integers(min_value=0, max_value=(2**32)-1),
        st.booleans(),
        st.booleans()).filter(
            lambda x: len(utfEncode(x[0], x[1], x[2])) < 2**16))
    def test_generateRTPPacket(self, data):
        doc, encoding, bom, time, isFirst, marker = data
        thisTransmitter = TTMLTransmitter("", 0, encoding=encoding, bom=bom)
        expectedSeqNum = thisTransmitter._nextSeqNum

        packet = thisTransmitter._generateRTPPacket(
            doc, time, isFirst, marker)
        payload = RTPPayload_TTML(
            encoding=encoding, bom=bom).fromBytearray(packet.payload)

        self.assertEqual(packet.timestamp, time)
        self.assertEqual(packet.sequenceNumber, expectedSeqNum)
        self.assertEqual(packet.marker, marker)
        self.assertEqual(payload.userDataWords, doc)

        self.assertEqual(thisTransmitter._nextSeqNum, expectedSeqNum + 1)

    @given(st.tuples(
        st.text(min_size=1),
        st.sampled_from(SUPPORTED_ENCODINGS),
        st.booleans(),
        st.datetimes(),
        st.booleans()).filter(
            lambda x: len(utfEncode(x[0], x[1], x[2])) < 2**16))
    def test_packetiseDoc(self, data):
        doc, encoding, bom, time, marker = data
        thisTransmitter = TTMLTransmitter("", 0, encoding=encoding, bom=bom)
        expectedSeqNum = thisTransmitter._nextSeqNum

        packets = thisTransmitter._packetiseDoc(doc, time)

        for x in range(len(packets)):
            payload = RTPPayload_TTML(
                encoding=encoding, bom=bom).fromBytearray(packets[x].payload)

            self.assertEqual(
                packets[x].timestamp, thisTransmitter._datetimeToRTPTs(time))
            self.assertEqual(packets[x].sequenceNumber, expectedSeqNum + x)
            self.assertIn(payload.userDataWords, doc)
            self.assertLess(len(utfEncode(payload.userDataWords)), 2**16)

            thisBom = BOMS[encoding]
            if bom and (x == 0):
                self.assertTrue(payload._userDataWords.startswith(thisBom))
            else:
                self.assertFalse(payload._userDataWords.startswith(thisBom))

            if x == (len(packets) - 1):
                self.assertTrue(packets[x].marker)
            else:
                self.assertFalse(packets[x].marker)

        self.assertEqual(
            thisTransmitter.nextSeqNum, expectedSeqNum + len(packets))


class TestTTMLTransmitterContexts (TestCase):
    async def dummyEndpoint(self, mockTransport, mockProtocol):
        return (mockTransport, mockProtocol)

    async def async_test_async(self, endpoint, port, doc, time):
        mockTransport = MagicMock()
        mockProtocol = MagicMock()
        endpoint.return_value = self.dummyEndpoint(mockTransport, mockProtocol)

        async with TTMLTransmitter("", port) as transmitter:
            await transmitter.sendDoc(doc, time)
            if len(doc) > 0:
                mockTransport.sendto.assert_called()
            else:
                mockTransport.sendto.assert_not_called()

        mockTransport.close.assert_called_once()

    @mock.patch(
        "asyncio.unix_events._UnixSelectorEventLoop.create_datagram_endpoint")
    @given(
        st.integers(min_value=0, max_value=(2**16)-1),
        st.text(),
        st.datetimes())
    def test_async(self, endpoint, port, doc, time):
        asyncio.get_event_loop().run_until_complete(
            self.async_test_async(endpoint, port, doc, time))

    @mock.patch("socket.socket")
    @given(
        st.integers(min_value=0, max_value=(2**16)-1),
        st.text(),
        st.datetimes())
    def test_sync(self, socket, port, doc, time):
        socket.reset_mock()
        sockInst = socket()

        with TTMLTransmitter("", port) as transmitter:
            transmitter.sendDoc(doc, time)
            if len(doc) > 0:
                sockInst.sendto.assert_called()
            else:
                sockInst.sendto.assert_not_called()

        sockInst.close.assert_called_once()

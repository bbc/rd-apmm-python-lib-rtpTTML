#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from unittest import TestCase, mock
from unittest.mock import MagicMock
from hypothesis import given, strategies as st
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

from rtpTTML import TTMLTransmitter  # type: ignore
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
            self.assertLessEqual(len(bytearray(fragment, "utf-8")), maxLen)
            reconstructedDoc += fragment

        self.assertEqual(doc, reconstructedDoc)

    @given(st.datetimes())
    def test_datetimeToRTPTs(self, time):
        rtpTs = self.transmitter._datetimeToRTPTs(time)

        self.assertIsInstance(rtpTs, int)
        self.assertGreaterEqual(rtpTs, 0)
        self.assertLess(rtpTs, 2**32)

    @given(
        st.text().filter(lambda x: len(bytearray(x, "utf-8")) < 2**16),
        st.integers(min_value=0, max_value=(2**32)-1),
        st.booleans())
    def test_generateRTPPacket(self, doc, time, marker):
        expectedSeqNum = self.transmitter._nextSeqNum

        packet = self.transmitter._generateRTPPacket(doc, time, marker)
        payload = RTPPayload_TTML().fromBytearray(packet.payload)

        self.assertEqual(packet.timestamp, time)
        self.assertEqual(packet.sequenceNumber, expectedSeqNum)
        self.assertEqual(packet.marker, marker)
        self.assertEqual(payload.userDataWords, doc)

        self.assertEqual(self.transmitter._nextSeqNum, expectedSeqNum + 1)

    @given(
        st.text(),
        st.datetimes())
    def test_packetiseDoc(self, doc, time):
        expectedSeqNum = self.transmitter._nextSeqNum

        packets = self.transmitter._packetiseDoc(doc, time)

        for x in range(len(packets)):
            payload = RTPPayload_TTML().fromBytearray(packets[x].payload)

            self.assertEqual(packets[x].timestamp, self.transmitter._datetimeToRTPTs(time))
            self.assertEqual(packets[x].sequenceNumber, expectedSeqNum + x)
            self.assertIn(payload.userDataWords, doc)
            self.assertLess(len(bytearray(payload.userDataWords, "utf-8")), 2**16)

            if x == (len(packets) - 1):
                self.assertTrue(packets[x].marker)
            else:
                self.assertFalse(packets[x].marker)

        self.assertEqual(self.transmitter.nextSeqNum, expectedSeqNum + len(packets))


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

    @mock.patch("asyncio.unix_events._UnixSelectorEventLoop.create_datagram_endpoint")
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

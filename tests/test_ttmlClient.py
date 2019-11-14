#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from unittest import TestCase, mock
from hypothesis import given, assume, strategies as st

from rtpTTML.ttmlClient import MAX_SEQ_NUM  # type: ignore
from rtpTTML import TTMLClient  # type: ignore


class TestTTMLClient (TestCase):
    def callback(self, doc, timestamp):
        self.callbackCallCount += 1
        self.callbackValues.append((doc, timestamp))

    @mock.patch("socket.socket")
    def setUp(self, mockSocket):
        self.callbackCallCount = 0
        self.callbackValues = []
        self.client = TTMLClient(0, self.callback)

    def setup_example(self):
        self.setUp()

    def test_unloop(self):
        msnPlus1 = MAX_SEQ_NUM + 1
        # [[prevNum, thisNum, expectedReturnVal]]
        tests = [
            [MAX_SEQ_NUM-1, MAX_SEQ_NUM, MAX_SEQ_NUM],
            [MAX_SEQ_NUM-1, 0, MAX_SEQ_NUM+1],
            [MAX_SEQ_NUM, 0, MAX_SEQ_NUM+1],
            [MAX_SEQ_NUM, 1, MAX_SEQ_NUM+2],
            [0, 1, 1],
            [0, 2, 2],
            [msnPlus1 + MAX_SEQ_NUM-1, MAX_SEQ_NUM, msnPlus1 + MAX_SEQ_NUM],
            [msnPlus1 + MAX_SEQ_NUM-1, 0, msnPlus1 + MAX_SEQ_NUM+1],
            [msnPlus1 + MAX_SEQ_NUM, 0, msnPlus1 + MAX_SEQ_NUM+1],
            [msnPlus1 + MAX_SEQ_NUM, 1, msnPlus1 + MAX_SEQ_NUM+2],
            [msnPlus1, 1, msnPlus1 + 1],
            [msnPlus1, 2, msnPlus1 + 2]]

        for test in tests:
            ret = self.client._unloopSeqNum(test[0], test[1])
            self.assertEqual(ret, test[2], msg="Failing test: {}".format(test))

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.lists(st.booleans(), min_size=10, max_size=10))
    def test_keysComplete(self, startKey, keepList):
        assume(keepList[0] is True)

        for keyOffset in range(10):
            if keepList[keyOffset]:
                self.client._fragments[startKey + keyOffset] = None

        complete = True

        seenFalse = False
        for keepItem in keepList[1:]:
            if keepItem is False:
                seenFalse = True
            else:
                if seenFalse:
                    complete = False

        self.assertEqual(complete, self.client._keysComplete())

    def test_keysCompleteEmpty(self):
        self.assertFalse(self.client._keysComplete())

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.lists(st.text(min_size=1), min_size=1))
    def test_processFragments(self, startKey, docFragments):
        expectedDoc = ""

        for x in range(len(docFragments)):
            expectedDoc += docFragments[x]
            self.client._fragments[startKey+x] = docFragments[x]

        self.client._processFragments()

        self.assertEqual(0, len(self.client._fragments))
        self.assertEqual(1, self.callbackCallCount)

        self.assertEqual(expectedDoc, self.callbackValues[0][0])

    def test_processFragmentsEmpty(self):
        self.client._processFragments()

        self.assertEqual(0, self.callbackCallCount)

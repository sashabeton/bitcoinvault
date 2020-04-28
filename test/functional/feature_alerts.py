#!/usr/bin/env python3
# Copyright (c) 2016-2018 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the Alerts changeover logic."""
import os
import shutil

from decimal import Decimal
from io import BytesIO
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import get_datadir_path


class AlertsTest(BitcoinTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 2
        self.extra_args = [
            [
                "-reindex",
            ],
            [
                "-reindex",
            ],
        ]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def get_best_block(self, node):
        tip = node.getbestblockhash()
        return node.getblock(tip)

    def find_address(self, listreceivedbyaddress, address):
        for addr in listreceivedbyaddress:
            if addr['address'] == address: return addr

    def reset_blockchain(self):
        self.stop_nodes()
        for i in range(self.num_nodes):
            datadir = get_datadir_path(self.options.tmpdir, i)
            if os.path.exists(datadir): shutil.rmtree(datadir)

        self.nodes = []
        self.setup_chain()
        self.start_nodes()
        self.setup_network()
        self.sync_all()

    def run_test(self):
        self.alert_recovery_pubkey = "02ecec100acb89f3049285ae01e7f03fb469e6b54d44b0f3c8240b1958e893cb8c"
        self.alert_recovery_privkey = "cRfYLWua6WcpGbxuv5rJgA2eDESWxqgzmQjKQuqDFMfgbnEpqhrP"

        self.log.info("Test tx from normal address to alert address")
        self.test_tx_from_normal_addr_to_alert_addr()

        self.reset_blockchain()
        self.log.info("Test atx from alert address to normal address")
        self.test_atx_from_alert_addr_to_normal_addr()

        self.reset_blockchain()
        self.log.info("Test tx from normal address to normal address")
        self.test_tx_from_normal_addr_to_normal_addr()

        self.reset_blockchain()
        self.log.info("Test atx becomes tx after 144 blocks")
        self.test_atx_becomes_tx()

    def test_tx_from_normal_addr_to_alert_addr(self):
        self.nodes[0].generate(200)
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        txid = self.nodes[0].sendtoaddress(alert_addr1['address'], 10)
        self.nodes[0].generate(1)

        self.sync_all()

        assert self.nodes[1].getbalance() == 10
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.get_best_block(self.nodes[0])['tx']
        assert txid not in self.get_best_block(self.nodes[0])['atx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(1, True), alert_addr1['address'])['txids']

    def test_atx_from_alert_addr_to_normal_addr(self):
        addr0 = self.nodes[0].getnewaddress()
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])
        txid = self.nodes[1].sendtoaddress(addr0, 10)
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        self.sync_all()

        assert self.nodes[0].getbalance() == 0
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.get_best_block(self.nodes[0])['atx']

        self.nodes[1].generatetoaddress(200, alert_addr1['address'])
        self.sync_all()

        assert self.nodes[0].getbalance() == 10
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(1, True), addr0)['txids']

    def test_tx_from_normal_addr_to_normal_addr(self):
        addr1 = self.nodes[1].getnewaddress()
        self.nodes[0].generate(200)
        txid = self.nodes[0].sendtoaddress(addr1, 10)
        self.nodes[0].generate(1)

        self.sync_all()

        assert self.nodes[1].getbalance() == 10
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.get_best_block(self.nodes[0])['tx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(1, True), addr1)['txids']

    def test_atx_becomes_tx(self):
        addr0 = self.nodes[0].getnewaddress()
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])
        txid = self.nodes[1].sendtoaddress(addr0, 10)
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        self.sync_all()

        assert self.nodes[0].getbalance() == 0
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.get_best_block(self.nodes[0])['atx']

        self.nodes[1].generatetoaddress(144, alert_addr1['address'])
        self.sync_all()

        assert self.nodes[0].getbalance() == 10
        assert self.get_best_block(self.nodes[0]) == self.get_best_block(self.nodes[1])
        assert txid in self.get_best_block(self.nodes[0])['tx']
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(1, True), addr0)['txids']


if __name__ == '__main__':
    AlertsTest().main()

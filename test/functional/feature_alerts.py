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
                "-txindex",
            ],
            [
                "-reindex",
                "-txindex",
            ],
        ]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def find_address(self, listreceivedbyaddress, address):
        for addr in listreceivedbyaddress:
            if addr['address'] == address: return addr

    def find_vout_n(self, rawtransaction, amount):
        for vout in rawtransaction['vout']:
            if vout['value'] == amount: return vout['n']

    def reset_blockchain(self):
        self.stop_nodes(wait=1)
        for i in range(self.num_nodes):
            datadir = get_datadir_path(self.options.tmpdir, i)
            if os.path.exists(datadir):
                shutil.rmtree(datadir)
                os.mkdir(datadir)

        self.nodes = []
        self.setup_chain()
        self.start_nodes(extra_args=self.extra_args)
        self.setup_network()
        self.sync_all()

    def reset_node(self, i):
        self.stop_node(i, wait=1)
        datadir = get_datadir_path(self.options.tmpdir, i)
        if os.path.exists(datadir):
            shutil.rmtree(datadir)
            os.mkdir(datadir)

        self.start_node(i, extra_args=self.extra_args)

    def run_test(self):
        self.alert_recovery_pubkey = "02ecec100acb89f3049285ae01e7f03fb469e6b54d44b0f3c8240b1958e893cb8c"
        self.alert_recovery_privkey = "cRfYLWua6WcpGbxuv5rJgA2eDESWxqgzmQjKQuqDFMfgbnEpqhrP"

        self.reset_blockchain()
        self.log.info("Test sign atx with wallet")
        self.test_sign_atx_with_wallet()

        self.reset_blockchain()
        self.log.info("Test sign atx with recovery key")
        self.test_sign_atx_with_recovery_key()

        self.reset_blockchain()
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

        self.reset_blockchain()
        self.log.info("Test atx fee is paid to original miner")
        self.test_atx_fee_is_paid_to_original_miner()

    def test_tx_from_normal_addr_to_alert_addr(self):
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)

        # mine some coins to node0
        self.nodes[0].generate(200)

        # send tx from node0 to alert_addr1 and generate block with this tx
        txid = self.nodes[0].sendtoaddress(alert_addr1['address'], 10)
        self.nodes[0].generate(1)

        # assert
        self.sync_all()
        assert self.nodes[1].getbalance() == 10
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.nodes[0].get_best_block()['tx']
        assert txid not in self.nodes[0].get_best_block()['atx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(1, True), alert_addr1['address'])['txids']

    def test_atx_from_alert_addr_to_normal_addr(self):
        addr0 = self.nodes[0].getnewaddress()
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)

        # mine some coins to alert_addr1
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # send atx from alert_addr1 to addr0 and generate block with this atx
        txid = self.nodes[1].sendtoaddress(addr0, 10)
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 0
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.nodes[0].get_best_block()['atx']

        # generate more blocks so atx becomes tx
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 10
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(1, True), addr0)['txids']

    def test_tx_from_normal_addr_to_normal_addr(self):
        addr1 = self.nodes[1].getnewaddress()

        # mine some coins to node0
        self.nodes[0].generate(200)

        # send tx from node0 to addr1 and generate block with this tx
        txid = self.nodes[0].sendtoaddress(addr1, 10)
        self.nodes[0].generate(1)

        # assert
        self.sync_all()
        assert self.nodes[1].getbalance() == 10
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.nodes[0].get_best_block()['tx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(1, True), addr1)['txids']

    def test_atx_becomes_tx(self):
        addr0 = self.nodes[0].getnewaddress()
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)

        # mine some coins to alert_addr1
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # send atx from alert_addr1 to addr0 and generate block with this atx
        txid = self.nodes[1].sendtoaddress(addr0, 10)
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 0
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.nodes[0].get_best_block()['atx']

        # generate 144 more blocks
        self.nodes[1].generatetoaddress(144, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 10
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txid in self.nodes[0].get_best_block()['tx']
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(1, True), addr0)['txids']

    def test_sign_atx_with_wallet(self):
        addr0 = self.nodes[0].getnewaddress()

        # mine some coins to alert_addr1
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # find vout to spend
        txtospendhash = self.nodes[1].getblockbyheight(10)['tx'][0]
        txtospend = self.nodes[1].getrawtransaction(txtospendhash, True)
        vouttospend = self.find_vout_n(txtospend, 175)

        # create and sign atx from alert_addr1 to addr0
        txtosend = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}], {addr0: 174.99})
        txtosend = self.nodes[1].signrawtransactionwithwallet(txtosend, [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript'], 'amount': 174.99}])
        txsent = self.nodes[1].decoderawtransaction(txtosend['hex'])

        # broadcast atx and mine block with this atx
        self.nodes[1].sendrawtransaction(txtosend['hex'])
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txsent['txid'] in self.nodes[0].get_best_block()['atx']

    def test_sign_atx_with_recovery_key(self):
        addr0 = self.nodes[0].getnewaddress()

        # mine some coins to alert_addr1
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # find vout to spend
        txtospendhash = self.nodes[1].getblockbyheight(10)['tx'][0]
        txtospend = self.nodes[1].getrawtransaction(txtospendhash, True)
        vouttospend = self.find_vout_n(txtospend, 175)

        # create and sign atx from alert_addr1 to addr0
        txtosend = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}], {addr0: 174.99})
        txtosend = self.nodes[1].signrawtransactionwithkey(txtosend, [self.alert_recovery_privkey], [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript'], 'amount': 174.99}])
        txsent = self.nodes[1].decoderawtransaction(txtosend['hex'])

        # broadcast atx and mine block with this atx
        self.nodes[1].sendrawtransaction(txtosend['hex'])
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].get_best_block() == self.nodes[1].get_best_block()
        assert txsent['txid'] in self.nodes[0].get_best_block()['atx']

    def test_atx_fee_is_paid_to_original_miner(self):
        mine_addr = self.nodes[0].getnewaddress()
        mine_addr2 = self.nodes[0].getnewaddress()
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)

        # mine coins and send 10 to alert address
        self.nodes[0].generatetoaddress(200, mine_addr)
        amount = 10
        self.nodes[0].sendtoaddress(alert_addr1['address'], amount)
        self.nodes[0].generatetoaddress(1, mine_addr)

        # send coins back as with tx alert and confirm it
        self.sync_all()
        assert self.nodes[1].getbalance() == amount
        txid = self.nodes[1].sendtoaddress(mine_addr, amount - 1)
        tx = self.nodes[1].getrawtransaction(txid, 1)
        fee = amount - tx['vout'][0]['value'] - tx['vout'][1]['value']
        self.nodes[1].generatetoaddress(1, mine_addr2)  # mine to separate address
        self.nodes[1].generatetoaddress(144, mine_addr)

        # assert
        self.sync_all()
        coinbase_id = self.nodes[1].get_best_block()['tx'][0]
        coinbase = self.nodes[1].getrawtransaction(coinbase_id, 1)
        assert coinbase['vout'][1]['value'] == fee


if __name__ == '__main__':
    AlertsTest().main()

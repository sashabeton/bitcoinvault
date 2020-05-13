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
        self.COINBASE_MATURITY = 100
        self.COINBASE_AMOUNT = Decimal(175)

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

        self.reset_blockchain()
        self.log.info("Test atx is rejected when inputs have different source")
        self.test_atx_is_rejected_when_inputs_have_different_source()

        self.reset_blockchain()
        self.log.info("Test atx is rejected when contains non-alert type inputs")
        self.test_atx_is_rejected_when_contains_non_alert_inputs()

        self.reset_blockchain()
        self.log.info("Test standard recovery transaction flow")
        self.test_recovery_tx_flow()

        self.reset_blockchain()
        self.log.info("Test recovery tx is rejected when iputs does not match alert")
        self.test_recovery_tx_is_rejected_when_inputs_does_not_match_alert()

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.nodes[0].getbestblock()['tx']
        assert txid not in self.nodes[0].getbestblock()['atx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(), alert_addr1['address'])['txids']

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.nodes[0].getbestblock()['atx']

        # generate more blocks so atx becomes tx
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 10
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(), addr0)['txids']

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.nodes[0].getbestblock()['tx']
        assert txid in self.find_address(self.nodes[1].listreceivedbyaddress(), addr1)['txids']

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.nodes[0].getbestblock()['atx']

        # generate 144 more blocks
        self.nodes[1].generatetoaddress(144, alert_addr1['address'])

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == 10
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txid in self.nodes[0].getbestblock()['tx']
        assert txid in self.find_address(self.nodes[0].listreceivedbyaddress(), addr0)['txids']

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txsent['txid'] in self.nodes[0].getbestblock()['atx']

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
        assert self.nodes[0].getbestblock() == self.nodes[1].getbestblock()
        assert txsent['txid'] in self.nodes[0].getbestblock()['atx']

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
        coinbase_id = self.nodes[1].getbestblock()['tx'][0]
        coinbase = self.nodes[1].getrawtransaction(coinbase_id, 1)
        assert coinbase['vout'][1]['value'] == fee

    def test_atx_is_rejected_when_inputs_have_different_source(self):
        addr0 = self.nodes[0].getnewaddress()

        # mine some coins to alert_addr1
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(50, alert_addr1['address'])
        alert_addr2 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(50, alert_addr2['address'])
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # find vout to spend
        txtospendhash = self.nodes[1].getblockbyheight(10)['tx'][0]
        txtospend = self.nodes[1].getrawtransaction(txtospendhash, True)
        vouttospend = self.find_vout_n(txtospend, 175)
        txtospendhash2 = self.nodes[1].getblockbyheight(60)['tx'][0]
        txtospend2 = self.nodes[1].getrawtransaction(txtospendhash2, True)
        vouttospend2 = self.find_vout_n(txtospend2, 175)

        # create and sign atx from alert_addr1 and alert_addr2 to addr0
        txtosend = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}, {'txid': txtospendhash2, 'vout': vouttospend2}], {addr0: 349.99})
        txtosend = self.nodes[1].signrawtransactionwithwallet(txtosend, [
            {'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript']},
            {'txid': txtospendhash2, 'vout': vouttospend2, 'scriptPubKey': txtospend2['vout'][vouttospend2]['scriptPubKey']['hex'], 'redeemScript': alert_addr2['redeemScript']}
        ])

        # broadcast atx and mine block with this atx
        self.nodes[1].sendrawtransaction(txtosend['hex'])
        exception_message = ""
        try:
            self.nodes[1].generatetoaddress(1, alert_addr1['address'])
        except Exception as e:
            exception_message = e.args[0]

        # assert
        assert 'bad-tx-alert-type' in exception_message

    def test_atx_is_rejected_when_contains_non_alert_inputs(self):
        addr0 = self.nodes[0].getnewaddress()

        # mine some coins to alert_addr1
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(50, alert_addr1['address'])
        addr1 = self.nodes[1].getnewaddress()
        self.nodes[1].generatetoaddress(50, addr1)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # find vout to spend
        txtospendhash = self.nodes[1].getblockbyheight(10)['tx'][0]
        txtospend = self.nodes[1].getrawtransaction(txtospendhash, True)
        vouttospend = self.find_vout_n(txtospend, 175)
        txtospendhash2 = self.nodes[1].getblockbyheight(60)['tx'][0]
        txtospend2 = self.nodes[1].getrawtransaction(txtospendhash2, True)
        vouttospend2 = self.find_vout_n(txtospend2, 175)

        # create and sign atx from alert_addr1 and alert_addr2 to addr0
        txtosend = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}, {'txid': txtospendhash2, 'vout': vouttospend2}], {addr0: 349.99})
        txtosend = self.nodes[1].signrawtransactionwithwallet(txtosend, [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript']}])

        # broadcast atx and mine block with this atx
        self.nodes[1].sendrawtransaction(txtosend['hex'])
        exception_message = ""
        try:
            self.nodes[1].generatetoaddress(1, alert_addr1['address'])
        except Exception as e:
            exception_message = e.args[0]

        # assert
        assert 'bad-tx-alert-type' in exception_message

    def test_recovery_tx_flow(self):
        alert_addr0 = self.nodes[0].getnewvaultaddress(self.alert_recovery_pubkey)
        other_addr0 = self.nodes[0].getnewaddress()
        attacker_addr1 = self.nodes[1].getnewaddress()

        # mine some coins to node0
        self.nodes[0].generatetoaddress(200, alert_addr0['address'])  # 200
        assert self.nodes[0].getbalance() == (200 - self.COINBASE_MATURITY) * self.COINBASE_AMOUNT

        # send atx to node1
        atx_to_recover = self.nodes[0].sendtoaddress(attacker_addr1, 10)
        atx_to_recover = self.nodes[0].gettransaction(atx_to_recover)['hex']
        atx_to_recover = self.nodes[0].decoderawtransaction(atx_to_recover)
        atx_fee = (200 - self.COINBASE_MATURITY) * self.COINBASE_AMOUNT - 10 - self.nodes[0].getbalance()

        # generate block with atx above
        self.nodes[0].generatetoaddress(1, alert_addr0['address'])  # 201

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() + 10 < (201 - self.COINBASE_MATURITY) * self.COINBASE_AMOUNT
        assert self.nodes[1].getbalance() == 0
        assert atx_to_recover['hash'] in self.nodes[0].getbestblock()['atx']

        # recover atx
        amount_to_recover = sum([vout['value'] for vout in atx_to_recover['vout']])
        assert atx_fee == self.COINBASE_AMOUNT - amount_to_recover

        recovery_tx = self.nodes[0].createrecoverytransaction(atx_to_recover['hash'], {other_addr0: amount_to_recover})
        recovery_tx = self.nodes[0].signrecoverytransaction(recovery_tx, [self.alert_recovery_privkey], alert_addr0['redeemScript'])
        recovery_txid = self.nodes[0].sendrawtransaction(recovery_tx['hex'])
        self.nodes[0].generatetoaddress(1, alert_addr0['address'])  # 202

        # assert
        self.sync_all()
        assert recovery_txid in self.nodes[0].getbestblock()['tx']
        assert recovery_txid in self.find_address(self.nodes[0].listreceivedbyaddress(), other_addr0)['txids']
        assert self.nodes[0].getbalance() == (202 - self.COINBASE_MATURITY) * self.COINBASE_AMOUNT - atx_fee

        # generate blocks so atx might become tx
        self.nodes[0].generatetoaddress(143, alert_addr0['address'])  # 345

        # assert
        self.sync_all()
        assert self.nodes[0].getbalance() == (345 - self.COINBASE_MATURITY) * self.COINBASE_AMOUNT  # dont subtract atx_fee because node0 takes it as a block miner
        assert atx_to_recover['hash'] not in self.nodes[0].getbestblock()['tx']
        assert self.find_address(self.nodes[1].listreceivedbyaddress(), attacker_addr1)['amount'] == 0
        assert self.find_address(self.nodes[1].listreceivedbyaddress(), attacker_addr1)['txids'] == []
        assert self.find_address(self.nodes[0].listreceivedbyaddress(), other_addr0)['amount'] == self.COINBASE_AMOUNT - atx_fee
        assert self.find_address(self.nodes[0].listreceivedbyaddress(), other_addr0)['txids'] == [recovery_txid]

    def test_recovery_tx_is_rejected_when_inputs_does_not_match_alert(self):
        addr0 = self.nodes[0].getnewaddress()

        # mine some coins to alert_addr1
        alert_addr1 = self.nodes[1].getnewvaultaddress(self.alert_recovery_pubkey)
        self.nodes[1].generatetoaddress(200, alert_addr1['address'])

        # create, sign and mine 1st atx from alert_addr1 to addr0
        txtospendhash = self.nodes[1].getblockbyheight(10)['tx'][0]
        txtospend = self.nodes[1].getrawtransaction(txtospendhash, True)
        vouttospend = self.find_vout_n(txtospend, 175)
        tx_alert1 = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}], {addr0: 174.99})
        tx_alert1 = self.nodes[1].signrawtransactionwithwallet(tx_alert1, [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript']}])
        self.nodes[1].sendrawtransaction(tx_alert1['hex'])
        self.nodes[1].generatetoaddress(1, alert_addr1['address'])

        # create, sign and mine 2nd atx from alert_addr1 to addr0
        self.sync_all()
        txtospendhash2 = self.nodes[1].getblockbyheight(20)['tx'][0]
        txtospend2 = self.nodes[1].getrawtransaction(txtospendhash2, True)
        vouttospend2 = self.find_vout_n(txtospend2, 175)
        tx_alert2 = self.nodes[1].createrawtransaction([{'txid': txtospendhash2, 'vout': vouttospend2}], {addr0: 174.99})
        tx_alert2 = self.nodes[1].signrawtransactionwithwallet(tx_alert2, [{'txid': txtospendhash2, 'vout': vouttospend2, 'scriptPubKey': txtospend2['vout'][vouttospend2]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript']}])
        self.nodes[1].sendrawtransaction(tx_alert2['hex'])
        self.nodes[1].generatetoaddress(10, alert_addr1['address'])
        self.sync_all()

        # create and sign (invalid) recovery tx spending both alerts inputs
        recovery_tx = self.nodes[1].createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}, {'txid': txtospendhash2, 'vout': vouttospend2}], {addr0: 349.99})
        recovery_tx = self.nodes[1].signrecoverytransaction(recovery_tx, [self.alert_recovery_privkey], alert_addr1['redeemScript'])

        # broadcast recovery tx and mine block
        tx_id = self.nodes[1].sendrawtransaction(recovery_tx['hex'])
        error = None
        try:
            self.nodes[1].generatetoaddress(1, alert_addr1['address'])
        except Exception as e:
            error = e.error

        # assert
        assert error['code'] == -1
        assert 'Revert transaction check failed' in error['message']
        assert tx_id in error['message']


if __name__ == '__main__':
    AlertsTest().main()

from RPCProxyWrapper import *
from pathlib import Path

import time


rpc_connection1 = RPCProxyWrapper(rpcport=18887, rpcuser='user', rpcpass='pass',
                                  datadir=Path.home() / '.bvault1')

rpc_connection2 = RPCProxyWrapper(rpcport=18888, rpcuser='user', rpcpass='pass',
                                  datadir=Path.home() / '.bvault2')

alert_recovery_pubkey = "02ecec100acb89f3049285ae01e7f03fb469e6b54d44b0f3c8240b1958e893cb8c"
alert_recovery_privkey = "cRfYLWua6WcpGbxuv5rJgA2eDESWxqgzmQjKQuqDFMfgbnEpqhrP"


def construct_atx_from_utxo():
    amount_to_send = 174.99
    addr2 = rpc_connection2.getnewaddress()

    # mine coins to alert address
    alert_addr1 = rpc_connection1.getnewvaultaddress(alert_recovery_pubkey)
    rpc_connection1.generatetoaddress(200, alert_addr1['address'])

    # create and sign tx from alert address
    txtospendhash = rpc_connection1.getblockbyheight(10)['tx'][0]
    txtospend = rpc_connection1.getrawtransaction(txtospendhash)
    vouttospend = find_vout_n(txtospend, 175)
    txtosend = rpc_connection1.createrawtransaction([{'txid': txtospendhash, 'vout': vouttospend}], {addr2: amount_to_send})
    txtosend = rpc_connection1.signrawtransactionwithwallet(txtosend, [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript'], 'amount': amount_to_send}])
    txtosend = rpc_connection1.signrawtransactionwithkey(txtosend, [alert_recovery_privkey], [{'txid': txtospendhash, 'vout': vouttospend, 'scriptPubKey': txtospend['vout'][vouttospend]['scriptPubKey']['hex'], 'redeemScript': alert_addr1['redeemScript'], 'amount': amount_to_send}])
    print_json(txtosend)
    print_json(rpc_connection1.decoderawtransaction(txtosend['hex']))
    print_json(rpc_connection1.sendrawtransaction(txtosend['hex']))

    # generate block with tx above
    rpc_connection1.generatetoaddress(200, alert_addr1['address'])


def atx_from_alert_addr_to_normal_addr():
    addr2 = rpc_connection2.getnewaddress()

    # mine coins to alert address
    alert_addr1 = rpc_connection1.getnewvaultaddress(alert_recovery_pubkey)
    rpc_connection1.generatetoaddress(200, alert_addr1['address'])

    # send from alert address
    txid = rpc_connection1.sendtoaddress(addr2, 10)
    rpc_connection1.generatetoaddress(1, alert_addr1['address'])

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == rpc_connection2.getbestblock()
    assert txid in rpc_connection2.getbestblock()['atx']
    assert rpc_connection2.getbalance() == 0

    # make transaction from alert
    rpc_connection1.generatetoaddress(200, alert_addr1['address'])

    # assert
    time.sleep(5)
    assert rpc_connection2.getbalance() == 10
    assert txid in find_address(rpc_connection2.listreceivedbyaddress(), addr2)['txids']


def tx_from_normal_addr_to_alert_addr():
    alert_addr1 = rpc_connection1.getnewvaultaddress(alert_recovery_pubkey)

    # mine coins to normal address
    addr2 = rpc_connection2.getnewaddress()
    rpc_connection2.generatetoaddress(200, addr2)

    # send to alert address
    txid = rpc_connection2.sendtoaddress(alert_addr1['address'], 10)
    rpc_connection2.generatetoaddress(1, addr2)

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == rpc_connection2.getbestblock()
    assert txid in rpc_connection2.getbestblock()['tx']
    assert rpc_connection1.getbalance() == 10
    assert txid in find_address(rpc_connection1.listreceivedbyaddress(), alert_addr1['address'])['txids']


def tx_from_normal_addr_to_normal_addr():
    addr1 = rpc_connection1.getnewaddress()

    # mine coins to normal address
    addr2 = rpc_connection2.getnewaddress()
    rpc_connection2.generatetoaddress(200, addr2)

    # send to normal address
    txid = rpc_connection2.sendtoaddress(addr1, 10)
    rpc_connection2.generatetoaddress(1, addr2)

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == rpc_connection2.getbestblock()
    assert txid in rpc_connection2.getbestblock()['tx']
    assert rpc_connection1.getbalance() == 10
    assert txid in find_address(rpc_connection1.listreceivedbyaddress(), addr1)['txids']


def test_synchronization_when_restart():
    # generate some blocks
    addr2 = rpc_connection2.getnewaddress()
    rpc_connection2.generatetoaddress(200, addr2)
    bestblock = rpc_connection2.getbestblock()

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == bestblock

    # restart nodes
    RPCProxyWrapper.killall()
    wait_for_bvaultd_and_init([rpc_connection1, rpc_connection2])

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == bestblock == rpc_connection2.getbestblock()


def test_synchronization_when_reset():
    # generate some blocks
    addr2 = rpc_connection2.getnewaddress()
    rpc_connection2.generatetoaddress(200, addr2)
    bestblock = rpc_connection2.getbestblock()

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == bestblock

    # reset 1st node
    RPCProxyWrapper.killall()
    rpc_connection1.reset()
    wait_for_bvaultd_and_init([rpc_connection1, rpc_connection2])

    # assert
    time.sleep(5)
    assert rpc_connection1.getbestblock() == bestblock == rpc_connection2.getbestblock()


if __name__ == '__main__':
    RPCProxyWrapper.killall()
    rpc_connection1.reset()
    rpc_connection2.reset()
    wait_for_bvaultd_and_init([rpc_connection1, rpc_connection2])

    # construct_atx_from_utxo()
    # atx_from_alert_addr_to_normal_addr()
    # tx_from_normal_addr_to_alert_addr()
    # tx_from_normal_addr_to_normal_addr()
    # test_synchronization_when_restart()
    # test_synchronization_when_reset()

    print('all ok!')

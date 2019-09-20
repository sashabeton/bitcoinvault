Manual QA End-to-End Test
=========================

The setup has two nodes, node1 is a miner and node2 is a full node (peer). All transactions take place via the full node.

## Sending coins back and forth

### 1. Start nodes

```shell
cd manual
./1-cleanup-env.sh
./2-start-network.sh
```

The UI should open up with two windows, the top one is wallet2, the bottom one is wallet1 (usually overlapping).

Make sure that wallet1 has 50.0 available coins (many more immature) and wallet2 has 0.0 available coins.

### 2. Send 1.0 coins from wallet1 to wallet2

Manually on wallet2 through the UI do a "Receive" payment.

Manually on wallet1 through the UI do a "Send" payment of 1.0 coins.

Make sure that wallet2 has 1.0 pending coins.

```shell
./3-mine-one.sh
```

Make sure that wallet2 has 1.0 available coins (and 0.0 pending).

### 3. Send 0.5 coins from wallet2 to wallet1

Manually on wallet1 through the UI do a "Receive" payment.

Manually on wallet2 through the UI do a "Send" payment of 0.5 coins.

Make sure that wallet1 has 0.5 pending coins.

```shell
./3-mine-one.sh
```

Make sure that wallet1 has 149.49 available coins (and 0.0 pending).

### 4. Stop nodes

```shell
./4-stop-network.sh
```

#!/usr/bin/env bash

echo --- MINING ONE BLOCK

broyale-cli -regtest -datadir=./node1-miner/ -rpcport=16111 -rpcuser=bitcoinrpc -rpcpassword=123456 generate 1

echo --- DONE
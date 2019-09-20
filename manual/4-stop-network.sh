#!/usr/bin/env bash

echo --- STOPPING NETWORK

bitcoin-cli -regtest -datadir=./node1-miner/ -rpcport=16111 -rpcuser=bitcoinrpc -rpcpassword=123456 stop
bitcoin-cli -regtest -datadir=./node2-peer/ -rpcport=16222 -rpcuser=bitcoinrpc -rpcpassword=123456 stop

echo --- DONE
#!/usr/bin/env bash

echo --- STARTING NETWORK

bitcoin-qt -regtest -datadir=./node1-miner/ -rpcport=16111 -rpcuser=bitcoinrpc -rpcpassword=123456 -listen -port=17111 -connect=localhost:17222 -server -deprecatedrpc=generate &
bitcoin-qt -regtest -datadir=./node2-peer/ -rpcport=16222 -rpcuser=bitcoinrpc -rpcpassword=123456 -listen -port=17222 -connect=localhost:17111 -server &
sleep 4
bitcoin-cli -regtest -datadir=./node1-miner/ -rpcport=16111 -rpcuser=bitcoinrpc -rpcpassword=123456 generate 101

echo --- DONE
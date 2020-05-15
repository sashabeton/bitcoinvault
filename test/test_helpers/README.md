New bvaultd RPC commands:
- `getnewvaultaddress "recovery_key" ( "label" "address_type" )`

  Creates an alert address which generates recoverable transaction alert when signed with 1 signature of 2 keys.
  It returns a json object with the address and redeemScript.
  
- `createvaultalertaddress "alert_key" "recovery_key" ( "address_type" )`
  
  Creates a vault address which generates recoverable transaction alert when signed with 1 signature of 2 keys.
  It returns a json object with the address and redeemScript.
  
- `createvaultinstantaddress "alert_key" "instant_key" "recovery_key" ( "address_type" )`
  
  Creates an instant/alert address which generates: recoverable transaction alert when signed with 1 signature of 3 keys and instant transaction when signed with 2 signatures of 3 keys.
  It returns a json object with the address and redeemScript.

Basic end-user flow:
```bash
$ bvaultd-cli getnewvaultaddress '02ecec100acb89f3049285ae01e7f03fb469e6b54d44b0f3c8240b1958e893cb8c'
  {
    "address": "2Mzr8e7BodXGt17w8MThbHgorpRCQTHMjxr",
    "redeemScript": "635167526821036bf5c93845749e7866a68281023e1c14f244e9cbdca628b6f594c72f0b3bbd3f2102ecec100acb89f3049285ae01e7f03fb469e6b54d44b0f3c8240b1958e893cb8c52ae"
  }
$ # get some coins
$ bvaultd-cli sendtoaddress 'other_addr' 10  # sign with wallet key and send alert transaction from alert address
  ce9a20d9322814128153bbc5231fe88a30f7e7097b46a3fbdb79a5e45a883bf9
```

See `RPCProxyWrapper/main.py` for more advanced usage.

Also see `test/functional/feature_alerts.py` for automated functional tests.

Suggested bvaultd run arguments:
- instance 1: `-regtest -rpcuser=user -rpcpassword=pass -rpcport=18887 -port=18444 -datadir="${HOME}/.bvault1" -addnode=127.0.0.1:18445 -txindex -reindex`
- instance 2: `-regtest -rpcuser=user -rpcpassword=pass -rpcport=18888 -port=18445 -datadir="${HOME}/.bvault2" -addnode=127.0.0.1:18444 -txindex -reindex`

from bitcoinrpc.authproxy import AuthServiceProxy, HTTP_TIMEOUT, JSONRPCException


class RPCProxyWrapper(AuthServiceProxy):
    def __init__(self, rpcport, rpcuser, rpcpass, datadir=None, service_name=None, timeout=HTTP_TIMEOUT, connection=None):
        self.timeout = timeout
        self.connection = connection
        self.service_name = service_name
        self.datadir = datadir
        self.rpcport = rpcport
        self.rpcuser = rpcuser
        self.rpcpass = rpcpass

        self.init()

    def init(self):
        super().__init__(f"http://{self.rpcuser}:{self.rpcpass}@127.0.0.1:{self.rpcport}", self.service_name, self.timeout, self.connection)

    @classmethod
    def killall(cls):
        import psutil
        import signal
        import time

        [p.send_signal(signal.SIGINT) for p in psutil.process_iter() if p.name() == 'bvaultd']
        time.sleep(2)
        [p.kill() for p in psutil.process_iter() if p.name() == 'bvaultd']
        if 'bvaultd' in [p.name() for p in psutil.process_iter()]: raise RuntimeError('looks like bvaultd is still running')

    def reset(self):
        import os
        import shutil

        if os.path.exists(self.datadir): shutil.rmtree(self.datadir)
        os.mkdir(self.datadir)

    def listreceivedbyaddress(self):
        return super().__getattr__('listreceivedbyaddress')(1, True)

    def getblockbyheight(self, height):
        hash = super().__getattr__('getblockhash')(height)
        return super().__getattr__('getblock')(hash)

    def getbestblock(self):
        hash = super().__getattr__('getbestblockhash')()
        return super().__getattr__('getblock')(hash)

    def getrawtransaction(self, txhash):
        return super().__getattr__('getrawtransaction')(txhash, True)

    def getnewvaultaddress(self, recovery_pubkey):
        try:
            return super().__getattr__('getnewvaultaddress')(recovery_pubkey)
        except JSONRPCException as e:
            if e.code == -32601:  # method not found
                return super().__getattr__('getnewalertaddress')(recovery_pubkey)

    def getnewalertaddress(self, recovery_pubkey):
        return self.getnewvaultaddress(recovery_pubkey)


def print_json(*args, **kwargs):
    import simplejson
    print(simplejson.dumps(*args, sort_keys=True, indent=4), **kwargs)


def find_vout_n(rawtransaction, amount):
    for vout in rawtransaction['vout']:
        if vout['value'] == amount: return vout['n']

    raise RuntimeError('vout not found')


def find_address(listreceivedbyaddress, address):
    for addr in listreceivedbyaddress:
        if addr['address'] == address: return addr

    raise RuntimeError('address not found')


def wait_for_bvaultd_and_init(proxy_wrappers):
    import psutil
    num = len(proxy_wrappers)
    input(f'Start {num} bvaultd daemons and input anything to continue...')
    if [p.name() for p in psutil.process_iter()].count('bvaultd') != num: raise RuntimeError('looks like bvaultd is still running')
    for pw in proxy_wrappers: pw.init()

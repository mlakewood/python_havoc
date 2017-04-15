from datetime import datetime, timedelta
from time import sleep

import hvac


class VaultClient():

    def __init__(self, ports):
        self.clients = []
        self.ports = ports
        self.init_result = None


    def is_vault_up(self):
        up = []
        for client in self.clients:
            try:
                init = client.is_initialized()
                up.append(True)
            except RequestException as e:
                up.append(False)
        return any(up)

    def wait_for_vault(self, timeout=10):
        timeout = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() <= timeout:
            up = self.is_vault_up()
            if up is True:
                return True
            sleep(1)
        raise ValueError("Waiting for vault timed out")

    def init_vault(self):
        token = None
        if self.init_result is not None:
            token = self.init_result.get('root_token', None)

        for client in self.clients:
            shares = 5
            threshold = 3

            if self.init_result is None and client.is_initialized() is False:
                self.init_result = client.initialize(shares, threshold)

            # unseal with multiple keys until threshold met
            if client.is_sealed() == True:
                keys = self.init_result['keys']
                client.unseal_multi(keys)

            assert(not client.is_sealed())

        for port in self.ports:
            client = hvac.Client(url='http://localhost:{0}'.format(port),
                                 token=self.init_result['root_token'],
                                 timeout=10)
        self.clients.append(client)

        return self.init_result

    def write_to_vault(self, key, value):
        import ipdb; ipdb.set_trace()
        self.clients[0].write(key, baz=value, lease='1h')

    def read(self, key):
        pass

from datetime import datetime, timedelta
from time import sleep

import hvac
from requests.exceptions import RequestException

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

        for port in self.ports:
            client = hvac.Client(url='http://localhost:{0}'.format(port),
                                 timeout=10)
            self.clients.append(client)

        self.wait_for_vault()

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

        # rebuild clients with auth tokens
        self.clients = []
        for port in self.ports:
            client = hvac.Client(url='http://localhost:{0}'.format(port),
                                 token=self.init_result['root_token'],
                                 timeout=10)
            self.clients.append(client)

        print("Root Token: {}".format(self.init_result['root_token']))
        return self.init_result

    def _get_vault_conn(self):
        vault_conn = None
        for client in self.clients:
            try:
                assert(client.is_sealed() is False)
                vault_conn = client
            except Exception as e:
                pass

        if vault_conn is None:
            raise Exception("Could not detect an unsealed vault instance.")

        return vault_conn

    def write_to_vault(self, path, data, max_retries=3):
        retries = 0
        while retries < max_retries:
            try:
                vault_conn = self._get_vault_conn()
                kwargs = {
                    'lease': '1h'
                }
                kwargs['data'] = data
                return vault_conn.write(path, **kwargs)
            except RequestException as e:
                retries += 1
                pass
        raise Exception("Unable to write to vault")

    def read(self, path, max_retries=3):
        retries = 0
        while retries < max_retries:
            try:
                vault_conn = self._get_vault_conn()
                return vault_conn.read(path)
            except RequestException as e:
                retries += 1
                pass
        raise Exception("Unable to write to vault")

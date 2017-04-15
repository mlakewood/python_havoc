import os
import unittest
from unittest.mock import MagicMock, patch, DEFAULT
from time import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import hvac
import requests
import warnings
from requests.exceptions import RequestException

from python_havoc.system import ContainerSystem, NetworkFaultGen, SystemGen
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.vault_client import VaultClient

# class TestNetworkFaultGen(unittest.TestCase):

# #    @settings(max_examples=1000)
#     @given(NetworkFaultGen.generate_network_fault())
#     def test_generate(self, network_fault):

#         if network_fault.get('impaired', True) == False:
#             self.assertEqual(list(network_fault.keys()), ['impaired'])
#             self.assertEqual(network_fault['impaired'], False)
#         else:
#             all_keys = sorted(['corrupt', 'limit',
#                                'loss_random', 'delay', 'duplicate', 'rate'])
#             self.assertEqual(sorted(list(network_fault.keys())), all_keys)
#             fault_keys = deepcopy(all_keys)

#             for key in fault_keys:
#                 self.assertTrue(network_fault[key] is None or type(network_fault[key]) == dict)

#             # check corrupt
#             if network_fault['limit'] is not None:
#                 limit = network_fault['limit']
#                 self.assertEqual(sorted(list(limit.keys())), ['packets'])
#                 self.assertTrue(limit['packets'] is None or
#                                 limit['packets'] >= 0 and limit['packets'] <= NetworkFaultGen.packet_limit_max)

#             if network_fault['delay'] is not None:
#                 delay = network_fault['delay']
#                 self.assertEqual(sorted(list(delay.keys())), sorted(['time', 'jitter',
#                                                                      'correlation', 'distribution']))
#                 self.assertTrue(delay['time'] is None or
#                                 delay['time'] >= NetworkFaultGen.ms_min and delay['time'] <= NetworkFaultGen.ms_max)

#                 self.assertTrue(delay['jitter'] is None or
#                                 delay['jitter'] >= NetworkFaultGen.ms_min and delay['jitter'] <= NetworkFaultGen.ms_max)

#                 self.assertTrue(delay['correlation'] is None or
#                                 delay['correlation'] >= 0 and delay['correlation'] <= 100)
#                 self.assertTrue(delay['distribution'] is None or
#                                 delay['distribution'] == 'normal')

#             if network_fault['loss_random'] is not None:
#                 loss_random = network_fault['loss_random']
#                 self.assertEqual(sorted(list(loss_random.keys())), ['percent'])
#                 self.assertTrue(loss_random['percent'] is None or
#                                 loss_random['percent'] >= 0 and loss_random['percent'] <= 100)


#             if network_fault['corrupt'] is not None:
#                 corrupt = network_fault['corrupt']
#                 self.assertEqual(sorted(list(corrupt.keys())), ['correlation', 'percent'])
#                 self.assertTrue(corrupt['correlation'] is None or
#                                 corrupt['correlation'] >= 0 and corrupt['correlation'] <= 100)
#                 self.assertTrue(corrupt['percent'] is None or
#                                 corrupt['percent'] >= 0 and corrupt['percent'] <= 100)

#             if network_fault['duplicate'] is not None:
#                 duplicate = network_fault['duplicate']
#                 self.assertEqual(sorted(list(duplicate.keys())), ['correlation', 'percent'])
#                 self.assertTrue(duplicate['correlation'] is None or
#                                 duplicate['correlation'] >= 0 and duplicate['correlation'] <= 100)
#                 self.assertTrue(duplicate['percent'] is None or
#                                 duplicate['percent'] >= 0 and duplicate['percent'] <= 100)

#             # disabled for now
#             # if network_fault['reorder'] is not None:
#             #     reorder = network_fault['reorder']
#             #     self.assertEqual(sorted(list(reorder.keys())), ['correlation', 'distance', 'percent'])
#             #     self.assertTrue(reorder['correlation'] is None or
#             #                     reorder['correlation'] >= 0 and reorder['correlation'] <= 100)
#             #     self.assertTrue(reorder['percent'] is None or
#             #                     reorder['percent'] >= 0 and reorder['percent'] <= 100)
#             #     self.assertTrue(reorder['distance'] is None or
#             #                     reorder['distance'] >= 0)

#             if network_fault['rate'] is not None:
#                 rate = network_fault['rate']
#                 keys = sorted(['rate', 'rate_units']) #, 'packet_overhead', 'cellsize', 'cellsize_overhead'])
#                 self.assertEqual(sorted(list(rate.keys())), keys)
#                 self.assertTrue(rate['rate'] is None or
#                                 rate['rate'] >= NetworkFaultGen.kbit_min and rate['rate'] <= NetworkFaultGen.kbit_max)
#                 self.assertTrue(rate['rate_units'] is None or
#                                 rate['rate_units'] in ['kbit'])
#                 # self.assertTrue(rate['packet_overhead'] is None or
#                 #                 rate['packet_overhead'] >= 0)
#                 # self.assertTrue(rate['cellsize'] is None or
#                 #                 rate['cellsize'] >= 0)
#                 # self.assertTrue(rate['cellsize_overhead'] is None or
#                 #                 rate['cellsize_overhead'] >= 0)


#     @given(NetworkFaultGen.generate_network_fault())
#     def test_convert_to_tc(self, network_fault):
#         if 'impaired' in network_fault.keys():
#             del network_fault['impaired']
#         tc_command = ContainerSystem.build_tc_command(network_fault)
#         if all([value == None for key, value in network_fault.items()]):
#             self.assertEqual(tc_command, "tc qdisc del dev eth0 root;")
#         else:
#             if network_fault['limit'] is not None:
#                 self.assertTrue("limit" in tc_command)
#             if network_fault['delay'] is not None:
#                 self.assertTrue("delay" in tc_command)
#             if network_fault['loss_random'] is not None:
#                 self.assertTrue("loss" in tc_command)
#             if network_fault['corrupt'] is not None:
#                 self.assertTrue("corrupt" in tc_command)
#             if network_fault['duplicate'] is not None:
#                 self.assertTrue("duplicate" in tc_command)
#             # if network_fault['reorder'] is not None:
#             #     self.assertTrue("reorder" in tc_command)
#             #     self.assertTrue("delay" in tc_command)
#             if network_fault['rate'] is not None:
#                 self.assertTrue("rate" in tc_command)



class TestGenerateSystemState(unittest.TestCase):
    project = 'vault'
    compose_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                '../data/docker-compose.yml')
    vault_1 = '{0}_vault_1_1'.format(project)
    consul_agent_1 = 'consul_agent_1'
    vault_2 = '{0}_vault_2_1'.format(project)
    consul_agent_2 = 'consul_agent_2'
    consul1 = 'consul1'
    consul2 = 'consul2'
    consul3 = 'consul3'
    consul4 = 'consul4'
    consul5 = 'consul5'

    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore", ResourceWarning) # suppress unix socket warning from urllib3
        cls.maxDiff = None #pylint: disable=invalid-name
        cls.sys = ContainerSystem(cls.project, cls.compose_file)
        cls.sys._populate_system()
        cls.sys.start_system()

        cls.sys.require_single(cls.consul_agent_1)
        cls.sys.require_single(cls.consul_agent_2)

        cls.sys.require_group([cls.vault_1, cls.vault_2], 1)
        cls.sys.require_group([cls.consul1,
                                cls.consul2,
                                cls.consul3,
                                cls.consul4,
                                cls.consul5], 1)
        cls.init_result = None
        cls.sys.wait_for_converge()
        cls.counter = 0
        cls.vault = VaultClient(['1234', '1235'])


    @classmethod
    def tearDownClass(cls):
        cls.sys.stop_system()



    def init_and_unseal(self):
        try:
            self.vault.init_vault()
            self.vault.wait_for_vault()

            # self.init_result = init_vault(self.init_result)
            # #make standby
            # self.init_result = init_vault(self.init_result, port='1235')
            # self.vault_token = self.init_result['root_token']
        except Exception as e:
            print(self.sys.print_container_logs(self.vault_1))
            print(self.sys.print_container_logs(self.vault_2))
            raise ValueError("Encountered exception '{0}' when initializing vault server".format(e))


    def write_value_and_validate(self, key, value, ports=['1234', '1235']):
        self.vault.write_to_vault(key, value)
        # vault_port = ports[0]
        # client = None
        # try:
        #     client = hvac.Client(url='http://localhost:{0}'.format(vault_port),
        #                          token=self.vault_token,
        #                          timeout=5)
        #     assert(client.is_sealed() is False)
        # except Exception as e:
        #     print(e)
        #     vault_port = ports[1]
        #     client = hvac.Client(url='http://localhost:{0}'.format(vault_port),
        #                          token=self.vault_token,
        #                          timeout=2)
        #     assert(client.is_sealed() is False)

        # key = str(self.counter)
        # client.write(key, baz=value, lease='1h')
        self.counter += 1
        output = self.vault.read(key)
        del output['request_id']

        expected_output = {'auth': None,
                           'data': {'baz': 'bar', 'lease': '1h'},
                           'lease_duration': 3600,
                           'lease_id': '',
                           'renewable': False,
                           'warnings': None,
                           'wrap_info': None}

        self.assertEqual(output, expected_output)


    @settings(max_examples=5)
    @given(st.data())
    def test_next_state(self, data):
        import ipdb; ipdb.set_trace()
        self.sys.restore_system_state()
        self.init_and_unseal()

        generator = SystemGen.generate_next_state(self.sys,
                                                  egress_fault=False,
                                                  link_fail=False,
                                                  node_fail=True)


        next_state = data.draw(SystemGen.generate_next_state(self.sys,
                                                             egress_fault=False,
                                                             link_fail=False,
                                                             node_fail=True
                                                         ))

        print("move to new state: {0}".format([(key, value["status"]) for key, value in next_state.items()]))

        self.sys.change_system_state(next_state)


        self.write_value_and_validate("secret/foo", "bar")




# class TestBasic(unittest.TestCase):

#     project = 'vault'
#     compose_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
#                                 './system/docker-compose.yml')
#     vault = '{0}_vault_1'.format(project)
#     consul_agent = 'consul-agent'
#     consul1 = 'consul1'
#     consul2 = 'consul2'
#     consul3 = 'consul3'
#     consul4 = 'consul4'
#     consul5 = 'consul5'


#     @classmethod
#     def setUpClass(cls):
#         warnings.simplefilter("ignore", ResourceWarning)
#         cls.maxDiff = None #pylint: disable=invalid-name

#         cls.client = hvac.Client(url='http://localhost:1234', token='myroot', timeout=5)
#         cls.sys = ContainerSystem(cls.project, cls.compose_file)
#         cls.sys.require_single(cls.vault)
#         cls.sys.require_single(cls.consul_agent)
#         cls.sys.require_group([cls.consul1, cls.consul2, cls.consul3, cls.consul4, cls.consul5], 1)
#         cls.sys.start_system()

#         retries = 0

#         while retries < 10:
#             try:

#                 print(cls.client.list_audit_backends())

#                 return True
#             except requests.exceptions.RequestException:
#                 retries += 1
#                 sleep(1)
#                 # Maybe try to recover?
#         raise Exception("Could not connect to Vault service")

#     @classmethod
#     def tearDownClass(cls):
#         cls.sys.stop_system()


#     def write_value_and_validate(self, key, value):
#         client.write(key, baz=value, lease='1h')
#         output = self.client.read(key)
#         del output['request_id']

#         expected_output = {'auth': None,
#                            'data': {'baz': 'bar', 'lease': '1h'},
#                            'lease_duration': 3600,
#                            'lease_id': '',
#                            'renewable': False,
#                            'warnings': None,
#                            'wrap_info': None}

#         self.assertEqual(output, expected_output)

#     def test_system_init(self):
#         expected_system = {
#             "vault_vault_1": {"status": "running",
#                                   "links": {
#                                       "consul-agent": {"impaired": False},
#                                       "consul1": {"impaired": False},
#                                       "consul2": {"impaired": False},
#                                       "consul3": {"impaired": False},
#                                       "consul4": {"impaired": False},
#                                       "consul5": {"impaired": False},
#                                   }
#                 },
#                 "consul-agent": {"status": "running",
#                                  "links": {
#                                      "vault_vault_1": {"impaired": False},
#                                      "consul1": {"impaired": False},
#                                      "consul2": {"impaired": False},
#                                      "consul3": {"impaired": False},
#                                      "consul4": {"impaired": False},
#                                      "consul5": {"impaired": False},
#                                  },
#                 },
#                 "consul1": {"status": "running",
#                             "links": {
#                                 "vault_vault_1": {"impaired": False},
#                                 "consul-agent": {"impaired": False},
#                                 "consul2": {"impaired": False},
#                                 "consul3": {"impaired": False},
#                                 "consul4": {"impaired": False},
#                                 "consul5": {"impaired": False},
#                             }
#                 },
#                 "consul2": {"status": "running",
#                             "links": {
#                                 "vault_vault_1": {"impaired": False},
#                                 "consul-agent": {"impaired": False},
#                                 "consul1": {"impaired": False},
#                                 "consul3": {"impaired": False},
#                                 "consul4": {"impaired": False},
#                                 "consul5": {"impaired": False},

#                             }
#                 },
#                 "consul3": {"status": "running",
#                             "links": {
#                                 "vault_vault_1": {"impaired": False},
#                                 "consul-agent": {"impaired": False},
#                                 "consul1": {"impaired": False},
#                                 "consul2": {"impaired": False},
#                                 "consul4": {"impaired": False},
#                                 "consul5": {"impaired": False},
#                             }
#                 },
#                 "consul4": {"status": "running",
#                             "links": {
#                                 "vault_vault_1": {"impaired": False},
#                                 "consul-agent": {"impaired": False},
#                                 "consul1": {"impaired": False},
#                                 "consul2": {"impaired": False},
#                                 "consul3": {"impaired": False},
#                                 "consul5": {"impaired": False},

#                             }
#                 },
#                 "consul5": {"status": "running",
#                             "links": {
#                                 "vault_vault_1": {"impaired": False},
#                                 "consul-agent": {"impaired": False},
#                                 "consul1": {"impaired": False},
#                                 "consul2": {"impaired": False},
#                                 "consul3": {"impaired": False},
#                                 "consul4": {"impaired": False},
#                             }
#                 }
#         }

#         for k, v in self.sys.system.items():
#             self.assertEqual(sorted(list(v.keys())), ['ip', 'links', 'status'])
#             del v['ip']

#         self.assertEqual(self.sys.system, expected_system)


#         expected_required = {
#             "singletons": ['vault_vault_1', 'consul-agent'],
#             "groups": [{"minimum": 1, "containers": ['consul1', 'consul2', 'consul3', 'consul4', 'consul5']}]
#         }

#         self.assertEqual(self.sys.required, expected_required)

#     @unittest.skip("demonstrating skipping")
#     def test_required_containers(self):
#         full_container_list = deepcopy(self.sys.required['singletons'])
#         full_container_list.extend([li['containers'] for li in self.sys.required['groups']])

#         containers = self.sys.required_containers().example()
#         print(containers)
#         for singleton in self.sys.required['singletons']:
#             self.assertTrue(singleton in containers)

#         # are we unique?
#         self.assertEqual(len(containers), len(set(containers)))
#         self.assertTrue(len(containers) >= 3)
#         exists = [True for c in containers if c in full_container_list]
#         self.assertTrue(all(exists))

#     @unittest.skip("demonstrating skipping")
#     def test_next_state(self):
#         from pprint import pprint
#         pprint(self.sys.generate_next_state().example())


#     def test_all_tc(self):
#         self.write_value_and_validate('secret/foo', 'bar')

#         self.sys.link_cut(self.consul_agent, self.consul1)

#         self.write_value_and_validate('secret/foo', 'bar')

#         self.sys.link_fix(self.consul_agent, self.consul1)

#         # time for recovery
#         sleep(5)

#         commands = {
#             "limit": {
#                 "packets": 1000
#             },
#             "delay": {
#                 "time": 1500,
#                 "jitter": 20,
#                 "correlation": 20,
#                 "distribution": "normal",
#             },
#             "loss_random": {
#                 "percent": 10
#             },
#             # "loss_state": {
#             #     "p13": 10,
#             #     "p31": 11,
#             #     "p32": 12,
#             #     "p23": 13,
#             #     "p14": 14,
#             # },
#             "corrupt": {
#                 "percent": 10,
#                 "correlation": 25,
#             },
#             "duplicate": {
#                 "percent": 10,
#                 "correlation": 25,
#             },
#             "reorder": {
#                 "percent": 20,
#                 "correlation": 20,
#                 "distance": 5,
#             },
#             "rate": {
#                 "rate": 10,
#                 "rate_units": 'mbit',
#                 "packet_overhead": 5,
#                 "cellsize": 5,
#                 "cellsize_overhead": 5,
#             }
#         }

#         self.sys.dump_tc_rules(self.consul_agent)

#         self.sys.link_flaky(self.consul_agent, self.consul1, commands)

#         self.sys.dump_tc_rules(self.consul_agent)

#         self.write_value_and_validate('secret/foo', 'bar')

#         self.sys.link_fix(self.consul_agent, self.consul1)

#         self.sys.dump_tc_rules(self.consul_agent)

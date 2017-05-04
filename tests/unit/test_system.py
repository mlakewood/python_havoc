import os
import unittest
from unittest.mock import MagicMock, patch, DEFAULT
from time import sleep
from copy import deepcopy
from datetime import datetime

import hvac
import requests
import warnings

from tempest.system import ContainerSystem, NetworkFaultGen, SystemGen
from tests.unit.base import BaseTest
from hypothesis import given, settings
from hypothesis import strategies as st

class TestNetworkFaultGen(BaseTest):

#    @settings(max_examples=1000)
    @unittest.skip
    @given(NetworkFaultGen.generate_network_fault())
    def test_generate(self, network_fault):

        if network_fault.get('impaired', True) == False:
            self.assertEqual(list(network_fault.keys()), ['impaired'])
            self.assertEqual(network_fault['impaired'], False)
        else:
            all_keys = sorted(['corrupt', 'limit',
                               'loss_random', 'delay', 'duplicate', 'rate'])
            self.assertEqual(sorted(list(network_fault.keys())), all_keys)
            fault_keys = deepcopy(all_keys)

            for key in fault_keys:
                self.assertTrue(network_fault[key] is None or type(network_fault[key]) == dict)

            # check corrupt
            if network_fault['limit'] is not None:
                limit = network_fault['limit']
                self.assertEqual(sorted(list(limit.keys())), ['packets'])
                self.assertTrue(limit['packets'] is None or
                                limit['packets'] >= 0 and limit['packets'] <= NetworkFaultGen.packet_limit_max)

            if network_fault['delay'] is not None:
                delay = network_fault['delay']
                self.assertEqual(sorted(list(delay.keys())), sorted(['time', 'jitter',
                                                                     'correlation', 'distribution']))
                self.assertTrue(delay['time'] is None or
                                delay['time'] >= NetworkFaultGen.ms_min and delay['time'] <= NetworkFaultGen.ms_max)

                self.assertTrue(delay['jitter'] is None or
                                delay['jitter'] >= NetworkFaultGen.ms_min and delay['jitter'] <= NetworkFaultGen.ms_max)

                self.assertTrue(delay['correlation'] is None or
                                delay['correlation'] >= 0 and delay['correlation'] <= 100)
                self.assertTrue(delay['distribution'] is None or
                                delay['distribution'] == 'normal')

            if network_fault['loss_random'] is not None:
                loss_random = network_fault['loss_random']
                self.assertEqual(sorted(list(loss_random.keys())), ['percent'])
                self.assertTrue(loss_random['percent'] is None or
                                loss_random['percent'] >= 0 and loss_random['percent'] <= 100)


            if network_fault['corrupt'] is not None:
                corrupt = network_fault['corrupt']
                self.assertEqual(sorted(list(corrupt.keys())), ['correlation', 'percent'])
                self.assertTrue(corrupt['correlation'] is None or
                                corrupt['correlation'] >= 0 and corrupt['correlation'] <= 100)
                self.assertTrue(corrupt['percent'] is None or
                                corrupt['percent'] >= 0 and corrupt['percent'] <= 100)

            if network_fault['duplicate'] is not None:
                duplicate = network_fault['duplicate']
                self.assertEqual(sorted(list(duplicate.keys())), ['correlation', 'percent'])
                self.assertTrue(duplicate['correlation'] is None or
                                duplicate['correlation'] >= 0 and duplicate['correlation'] <= 100)
                self.assertTrue(duplicate['percent'] is None or
                                duplicate['percent'] >= 0 and duplicate['percent'] <= 100)

            # disabled for now
            # if network_fault['reorder'] is not None:
            #     reorder = network_fault['reorder']
            #     self.assertEqual(sorted(list(reorder.keys())), ['correlation', 'distance', 'percent'])
            #     self.assertTrue(reorder['correlation'] is None or
            #                     reorder['correlation'] >= 0 and reorder['correlation'] <= 100)
            #     self.assertTrue(reorder['percent'] is None or
            #                     reorder['percent'] >= 0 and reorder['percent'] <= 100)
            #     self.assertTrue(reorder['distance'] is None or
            #                     reorder['distance'] >= 0)

            if network_fault['rate'] is not None:
                rate = network_fault['rate']
                keys = sorted(['rate', 'rate_units']) #, 'packet_overhead', 'cellsize', 'cellsize_overhead'])
                self.assertEqual(sorted(list(rate.keys())), keys)
                self.assertTrue(rate['rate'] is None or
                                rate['rate'] >= NetworkFaultGen.kbit_min and rate['rate'] <= NetworkFaultGen.kbit_max)
                self.assertTrue(rate['rate_units'] is None or
                                rate['rate_units'] in ['kbit'])
                # self.assertTrue(rate['packet_overhead'] is None or
                #                 rate['packet_overhead'] >= 0)
                # self.assertTrue(rate['cellsize'] is None or
                #                 rate['cellsize'] >= 0)
                # self.assertTrue(rate['cellsize_overhead'] is None or
                #                 rate['cellsize_overhead'] >= 0)


    @unittest.skip
    @given(NetworkFaultGen.generate_network_fault())
    def test_convert_to_tc(self, network_fault):
        if 'impaired' in network_fault.keys():
            del network_fault['impaired']
        tc_command = ContainerSystem.build_tc_command(network_fault)
        if all([value == None for key, value in network_fault.items()]):
            self.assertEqual(tc_command, "tc qdisc del dev eth0 root;")
        else:
            if network_fault['limit'] is not None:
                self.assertTrue("limit" in tc_command)
            if network_fault['delay'] is not None:
                self.assertTrue("delay" in tc_command)
            if network_fault['loss_random'] is not None:
                self.assertTrue("loss" in tc_command)
            if network_fault['corrupt'] is not None:
                self.assertTrue("corrupt" in tc_command)
            if network_fault['duplicate'] is not None:
                self.assertTrue("duplicate" in tc_command)
            # if network_fault['reorder'] is not None:
            #     self.assertTrue("reorder" in tc_command)
            #     self.assertTrue("delay" in tc_command)
            if network_fault['rate'] is not None:
                self.assertTrue("rate" in tc_command)



def init_vault(init_result=None, port='1234'):
    token = None
    if init_result is not None:
        token = init_result.get('root_token', None)

    client = hvac.Client(url='http://localhost:{0}'.format(port), token=token, timeout=10)

    shares = 5
    threshold = 3

    if init_result is None and client.is_initialized() != True:
        init_result = client.initialize(shares, threshold)

    # unseal with multiple keys until threshold met
    if client.is_sealed() == True:
        keys = init_result['keys']
        client.unseal_multi(keys)

    assert(not client.is_sealed())
    return init_result


class TestMockGenerateSystemState(BaseTest):

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

    def setUp(self):
        self.maxDiff = None

        self.sys = ContainerSystem(self.project, self.compose_file)
        self.sys.system = {'consul_agent_2': {'ip': '172.18.0.8',
                                              'links': {'egress': {'impaired': False},
                                                        'ingress': {'impaired': False}},
                                              'status': 'running',
                                              'logs': None,
                                          },
                           'consul1': {'ip': '172.18.0.2',
                                       'links': {'egress': {'impaired': False},
                                                 'ingress': {'impaired': False}},
                                       'status': 'running',
                                       'logs': None,
                                   },
                           'consul2': {'ip': '172.18.0.4',
                                       'links': {'egress': {'impaired': False},
                                                 'ingress': {'impaired': False}},
                                       'status': 'running',
                                       'logs': None,
                                   },
                           'consul3': {'ip': '172.18.0.3',
                                       'links': {'egress': {'impaired': False},
                                                 'ingress': {'impaired': False}},
                                       'status': 'running',
                                       'logs': None,
                                   },
                           'consul4': {'ip': '172.18.0.5',
                                       'links': {'egress': {'impaired': False},
                                                 'ingress': {'impaired': False}},
                                       'status': 'running',
                                       'logs': None,
                                   },
                           'consul5': {'ip': '172.18.0.6',
                                       'links': {'egress': {'impaired': False},
                                                 'ingress': {'impaired': False}},
                                       'status': 'running',
                                       'logs': None,
                                   },
                           'consul_agent_1': {'ip': '172.18.0.7',
                                              'links': {'egress': {'impaired': False},
                                                        'ingress': {'impaired': False}},
                                              'status': 'running',
                                              'logs': None,
                                          },
                           'vault_vault_1_1': {'ip': '172.18.0.9',
                                               'links': {'egress': {'impaired': False},
                                                         'ingress': {'impaired': False}},
                                               'status': 'running',
                                               'logs': None,
                                           },
                           'vault_vault_2_1': {'ip': '172.18.0.10',
                                               'links': {'egress': {'impaired': False},
                                                         'ingress': {'impaired': False}},
                                               'status': 'running',
                                               'logs': None,
                                           }}

        self.sys.require_single(self.consul_agent_1)
        self.sys.require_single(self.consul_agent_2)

        self.sys.require_group([self.vault_1, self.vault_2], 1)
        self.sys.require_group([self.consul1,
                               self.consul2,
                               self.consul3,
                               self.consul4,
                               self.consul5], 1)

    @given(st.data())
    def test_next_state_link_fail(self, data):
        with patch.multiple(ContainerSystem,
                            stop_container=DEFAULT,
                            start_container=DEFAULT,
                            link_fix=DEFAULT,
                            wait_for_converge=DEFAULT):
            start = datetime.utcnow()
            next_state = data.draw(SystemGen.generate_next_state(self.sys,
                                                                 egress_fault=False,
                                                                 link_fail=True
                                                             ))
            self.sys.change_system_state(next_state)

            self.assertEqual(sorted(self.sys.system.keys()), sorted(next_state.keys()))
            self.assertTrue(all([v['status'] == 'running' for k, v in next_state.items()]))

            for key, value in next_state.items():
                self.assertTrue(value.get('ip', False))
                self.assertFalse(value['links']['egress']['impaired'])
                self.assertTrue((value['links']['ingress']['impaired'] is False) or
                                (value['links']['ingress']['impaired'] is True))

            self.sys.restore_system_state()

    @given(st.data())
    def test_next_state_egress_fault(self, data):
        with patch.multiple(ContainerSystem,
                            stop_container=DEFAULT,
                            start_container=DEFAULT,
                            link_fix=DEFAULT,
                            wait_for_converge=DEFAULT):
            start = datetime.utcnow()
            next_state = data.draw(SystemGen.generate_next_state(self.sys,
                                                                 egress_fault=True,
                                                                 link_fail=False
                                                             ))
            self.sys.change_system_state(next_state)

            self.assertEqual(sorted(self.sys.system.keys()), sorted(next_state.keys()))
            self.assertTrue(all([v['status'] == 'running' for k, v in next_state.items()]))

            for key, value in next_state.items():
                self.assertTrue(value.get('ip', False))
                if value['links']['egress'].get('impaired', None) == None:
                    keys = sorted(['corrupt', 'duplicate', 'rate', 'limit', 'delay', 'loss_random'])
                    self.assertEqual(sorted(value['links']['egress'].keys()), keys)
                self.assertFalse(value['links']['ingress']['impaired'])

            self.sys.restore_system_state()

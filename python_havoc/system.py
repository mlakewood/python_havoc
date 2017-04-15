from time import sleep
from subprocess import run
from copy import deepcopy
from datetime import datetime

import docker
from python_havoc.tc import Tc
from hypothesis import strategies as st
from hypothesis import find, given, assume
from requests.exceptions import RequestException

class ContainerSystem():
    def __init__(self, project_name, compose_file):
        self.client = docker.from_env()
        self.compose_file = compose_file
        self.project_name = project_name
        self.containers = []
        self.system = {}

        self.required = {
            "singletons": [],
            "groups": [],
        }



    def start_system(self, debug=False):
        command = "docker-compose --verbose -p {0} -f {1} up -d --build --force-recreate".format(
            self.project_name, self.compose_file)
        if debug is True:
            print(command)
        output = run(command.split(" "), check=True)
        self._populate_system()


    def _populate_system(self):
        self.containers = self.collect_containers()
        self.system = self.system_containers(self.containers)

        #populate system with memoised values.
        for container in self.containers:
            name = container.name
            self.system[name]['ip'] = self._fetch_ip(container)


    def stop_system(self, debug=False):
        command = "docker-compose -p {0} -f {1} down -v --remove-orphans".format(
            self.project_name, self.compose_file)
        if debug is True:
            print(command)
        return run(command.split(" "), check=True)

    def start_container(self, container_name):
        retries = 0
        max_retries = 3
        while retries <= max_retries:
            try:
                container = self.client.containers.get(container_name)
                container.start()
                return
            except RequestException as e:
                retries +=1
                sleep(1)
                pass
        raise Exception("Was not able to communicate to docker to start container.")


    def stop_container(self, container_name):
        retries = 0
        max_retries = 3
        while retries <= max_retries:
            try:
                container = self.client.containers.get(container_name)
                self.system[container_name]['logs'] = container.logs()
                container.stop()
                return
            except RequestException as e:
                retries +=1
                sleep(1)
                pass
        raise Exception("Was not able to communicate to docker to stop container.")

    def print_container_logs(self, container_name):
        self.client.containers.get(container_name).logs()

    def collect_containers(self):
        return [c for c in self.client.containers.list()
                if self._get_project(c) == self.project_name]

    def system_containers(self, containers):
        data = {}
        for cont in containers:
            container = {}
            container["status"] = cont.status
            container["logs"] = ""
            links = {"ingress": {"impaired": False},
                     "egress": {"impaired": False},
            }
            container["links"] = links
            data[cont.name] = container
        return data

    def require_single(self, container):
        if container not in self.system.keys():
            raise ValueError("Container {0} not defined in current system. Candidates are {1}".format(container,
                                                                                                      sorted(self.system.keys())))
        self.required['singletons'].append(container)

    def require_group(self, containers, minimum):
        group = {'minimum': minimum, 'containers': containers}
        for container in containers:
            if container not in self.system.keys():
                raise ValueError("Container {0} not defined in current system. Candidates are {1}".format(container,
                                                                                                          sorted(self.system.keys())))

        self.required['groups'].append(group)

    def change_system_state(self, new_state):
        # shut down any containers not in new state
        all_containers = self.system.keys()
        new_state_containers = new_state.keys()
        stop_containers = [s_cont for s_cont in all_containers if s_cont not in new_state_containers]
        for cont in stop_containers:
            self.stop_container(cont)

        self.wait_for_converge()

        # for any container running update its links


    def wait_for_converge(self):
        sleep(1)

    def restore_system_state(self):
        for cont in self.system.keys():
            self.start_container(cont)
            # this as a sideeffect blocks starting the next container until the
            # commands are done.
            #self.link_fix(cont, cont)



    # Util Methods
    @staticmethod
    def _get_project(container):
        return container.attrs["Config"]["Labels"].get("com.docker.compose.project", None)

    def _fetch_ip(self, container):
        network_name = "{0}_default".format(self.project_name)

        return container.attrs['NetworkSettings']['Networks'][network_name][
            'IPAddress']

    def fetch_ip(self, container_name):
        return self.system[container_name]['ip']

    def container_from_name(self, name):
        container = [c for c in self.containers if c.name == name]
        if len(container) == 0:
            return None
        if len(container) > 1:
            raise Exception("More than one container in project with name: {0}".format(name))
        return container[0]

    # Generate new states



    # Network methods

    def dump_ip_tables_rules(self, container_name):
        command = 'iptables -S'.split(" ")

        cont = self.client.containers.get(container_name)
        return cont.exec_run(command, privileged=True)

    def dump_tc_rules(self, container_name):
        cont = self.client.containers.get(container_name)

        command = 'tc -s qdisc'
        qdisc_output = cont.exec_run(command, privileged=True)


        command = 'tc class show dev eth0'
        class_output = cont.exec_run(command, privileged=True)


        command = 'tc filter show dev eth0'
        filter_output = cont.exec_run(command, privileged=True)

        output = '{0} \n######\n {1} \n######\n {2} \n######\n'.format(qdisc_output.decode("utf-8"),
                                                                       class_output.decode("utf-8"),
                                                                       filter_output.decode("utf-8"))
        return output

    def link_fix(self, src, dest, recovery_time=5):
        src_ip = self.fetch_ip(src)
        output = []

        command = "iptables -D INPUT -s {0} -j DROP".format(src_ip).split(" ")
        rc = self._mutate_link(dest, command)
        output.append(rc)

        tc_clean = Tc().clean()
        rc = self._mutate_link(src, tc_clean)
        output.append(rc)
        sleep(recovery_time)
        return output

    def link_cut(self, src, dest):
        """
            iptables
               ^
        src -> |  dest



        """
        src_ip = self.fetch_ip(src)

        command = 'iptables -A INPUT -s {0} -j DROP'.format(src_ip).split(" ")
        return self._mutate_link(dest, command)

    def link_flaky(self, src, dest, commands):
        """
        {
            "limit": "",
            "delay": {
                "time": "",
                "jitter": "",
                "distribution": "",
            }
            "loss_random": {
                "percent": 10
            },
            "loss_state": {
                "percent": 10,
                "p31": 11,
                "p32": 12,
                "p23": 13,
                "p14": 14,
            },
            "corrupt": {
                "percent": "",
                "correlation": "",
            },
            "duplication": {
                "percent": "",
                "correlation": "",
            },
            "reordering": {
                "percent": "",
                "correlation": "",
                "distance": "",
            },
            "rate": {
                "rate": "",
                "rate_units": "",
                "packet_overhead": "",
                "cellsize": "",
                "cellsize_overhead": ""
            }
        }

        """
        # tc = Tc()
        # command_dispatch = {
        #     "limit": tc.limit,
        #     "delay": tc.delay,
        #     "loss_random": tc.loss_random,
        #     "loss_state": tc.loss_state,
        #     "corrupt": tc.corrupt,
        #     "duplicate": tc.duplicate,
        #     "reorder": tc.reorder,
        #     "rate": tc.rate
        # }
        # tc = tc.filter()
        # for key in commands:
        #     tc = command_dispatch[key](**commands[key])

        output = ''
        tc_command = self.build_tc_command(commands, self.fetch_ip(dest))
        for command in tc_command.split(';'):
            split_command = [el for el in command.replace("\n", "").split(" ") if el != '']
            if split_command == []:
                continue
            output += self._mutate_link(src, split_command)

        if output != '':
            raise Exception("Failed to make link flaky. Message: {0}".format(output))
        return output

    @staticmethod
    def build_tc_command(commands, filter_ip=None):
        tc = Tc()
        command_dispatch = {
            "limit": tc.limit,
            "delay": tc.delay,
            "loss_random": tc.loss_random,
            "loss_state": tc.loss_state,
            "corrupt": tc.corrupt,
            "duplicate": tc.duplicate,
            "reorder": tc.reorder,
            "rate": tc.rate
        }

        # If all values are None, then we should clean.

        if all([value is None for value in commands.values()]):
            return tc.clean()

        tc = tc.filter(filter_ip)
        for key in commands:
            if commands[key] is not None:
                tc = command_dispatch[key](**commands[key])

        return tc.command()

    def _mutate_link(self, src, command):
        cont = self.client.containers.get(src)
        return cont.exec_run(command, privileged=True).decode('utf-8')



class SystemGen():

    @staticmethod
    @st.composite
    def generate_next_state(draw, sys, egress_fault=True, link_fail=True, node_fail=True):
        containers = draw(SystemGen.required_containers(sys, node_fail=node_fail))

        new_state = {}

        for cont in sys.system.keys():

            if cont in containers:
                new_state[cont] = deepcopy(sys.system[cont])
                # remove logs if present as this isnt generatable.
                del new_state[cont]['logs']
                new_state[cont]['status'] = st.just(new_state[cont]['status'])
                new_state[cont]['ip'] = st.just(new_state[cont]['ip'])
                no_fault = st.just({"impaired": False})

                if link_fail == True:
                    ingress = st.one_of(no_fault,
                                        st.just({"impaired": True}))
                else:
                    ingress = no_fault

                if egress_fault == True:
                    egress = st.one_of(no_fault,
                                       NetworkFaultGen.generate_network_fault())
                else:
                    egress = no_fault

                links = st.fixed_dictionaries({"ingress": ingress,
                                               "egress": egress})

                new_state[cont]['links'] = links
                new_state[cont] = st.fixed_dictionaries(new_state[cont])

        return draw(st.fixed_dictionaries(new_state))

    @st.composite
    def required_containers(draw, system, node_fail=True):
        containers = []
        containers.extend(system.required['singletons'])

        for group in system.required['groups']:
            if node_fail == True:
                min_size = group['minimum']
            else:
                min_size = len(group['containers'])
            containers.extend(draw(st.lists(elements=st.sampled_from(group['containers']),
                                                                     min_size=min_size,
                                                                     unique=True)))
        return containers



class NetworkFaultGen():

    ms_min = 0
    ms_max = 5000
    kbit_min = 0
    kbit_max = 1000000
    packet_limit_max = 100000

    @staticmethod
    @st.composite
    def generate_network_fault(draw):
        no_fault = {"impaired": False}

        fault = draw(draw(NetworkFaultGen.generate_network_fault_only()))
        no_fault = st.just(no_fault)

        # import ipdb; ipdb.set_trace()
        if all([value is None for key, value in fault.items()]):
            return draw(draw(st.just(no_fault)))

        #assume(generated_value['delay'] is not None and generated_value['reorder'] is not None)
        return fault

    @staticmethod
    @st.composite
    def generate_network_fault_only(draw):

        fault = {
            "limit": draw(NetworkFaultGen.generate_limit()),
            "delay": draw(NetworkFaultGen.generate_delay()),
            "loss_random": draw(NetworkFaultGen.generate_loss_random()),
            "corrupt": draw(NetworkFaultGen.generate_corrupt()),
            "duplicate": draw(NetworkFaultGen.generate_duplicate()),
#            "reorder": draw(NetworkFaultGen.generate_reorder()),
            "rate": draw(NetworkFaultGen.generate_rate()),
        }


        return st.fixed_dictionaries(fault)

    @staticmethod
    @st.composite
    def generate_limit(draw):
        packets = st.integers(min_value=0,
                              max_value=NetworkFaultGen.packet_limit_max)
        return st.one_of(st.fixed_dictionaries({"packets": packets}),
                         st.none())

    @staticmethod
    @st.composite
    def generate_delay(draw):
        delay = {
            "time": st.integers(min_value=NetworkFaultGen.ms_min, max_value=NetworkFaultGen.ms_max),
            "jitter": st.one_of(st.integers(min_value=0, max_value=5000), st.none()),
            "correlation": st.one_of(st.integers(min_value=0, max_value=100), st.none()),
            "distribution": st.one_of(st.just("normal"), st.none())
        }
        return st.one_of(st.fixed_dictionaries(delay), st.none())

    @staticmethod
    @st.composite
    def generate_loss_random(draw):
        return st.one_of(st.fixed_dictionaries({"percent": st.integers(min_value=0, max_value=100)}),
                         st.none())
    @staticmethod
    @st.composite
    def generate_corrupt(draw):
        return st.one_of(st.fixed_dictionaries({"percent": st.integers(min_value=0, max_value=100),
                                                "correlation": st.integers(min_value=0, max_value=100)}),
                         st.none())

    @staticmethod
    @st.composite
    def generate_duplicate(draw):
        return st.one_of(st.fixed_dictionaries({"percent": st.integers(min_value=0, max_value=100),
                                                "correlation": st.integers(min_value=0, max_value=100)}),
                         st.none())

    # @staticmethod
    # @st.composite
    # def generate_reorder(draw):
    #     """
    #     This must only happen if delay is applied
    #     """
    #     return st.one_of(st.fixed_dictionaries({"percent": st.integers(min_value=0, max_value=100),
    #                                             "correlation": st.integers(min_value=0, max_value=100),
    #                                             "distance": st.integers(min_value=0)}),
    #                      st.none())

    @staticmethod
    @st.composite
    def generate_rate(draw):
        """
        This must only happen if delay is applied
        """
        return st.one_of(st.fixed_dictionaries({"rate": st.integers(min_value=0,
                                                                    max_value=NetworkFaultGen.kbit_max),
                                                "rate_units": st.just("kbit")}),
                         st.none())

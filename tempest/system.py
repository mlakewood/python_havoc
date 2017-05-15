from time import sleep
from subprocess import run
from copy import deepcopy
from datetime import datetime

import docker
from tempest.tc import Tc
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
        verbose = ""
        if debug is True:
            verbose = " --verbose"
        command = "docker-compose{0} -p {1} -f {2} up -d --build --force-recreate".format(
            verbose,
            self.project_name,
            self.compose_file)
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

    def change_system_state(self, new_state):
        for cont, state in new_state.items():
            if self.ingress_impaired(state):
                print("Making ingress impaired for container: {0}".format(cont))
                self.fail_ingress(cont)

            if self.egress_impaired(state):
                print("Making egress impaired for container: {0}".format(cont))
                self.fault_egress(cont, state["links"]["egress"])

    def ingress_impaired(self, state):
        return state["links"]["ingress"].get("impaired", True)

    def egress_impaired(self, state):
        return state["links"]["egress"].get("impaired", True)

    def wait_for_converge(self):
        sleep(1)


    def restore_system_state(self):
        for cont in self.system.keys():
            self.fix_network(cont)

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

    def fix_network(self, container, recovery_time=1):
        print("fixing network for container: {0}".format(container))
        output = []

        command = "iptables -D INPUT -j DROP".split(" ")
        rc = self._mutate_link(container, command)
        output.append(rc)

        tc_clean = Tc().clean()
        rc = self._mutate_link(container, tc_clean)
        output.append(rc)
        sleep(recovery_time)
        return output

    def fail_ingress(self, container):
        """
            iptables
               ^
        src -> |  container

        drop all incoming traffic to the container.

        """

        command = 'iptables -A INPUT -j DROP'.split(" ")
        return self._mutate_link(container, command)

    def fault_egress(self, src, commands, dest=None):
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
        if dest != None:
            filter_ip = self.fetch_ip(dest)
        else:
            filter_ip = None
        tc_command = self.build_tc_command(commands, filter_ip)
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
    def generate_next_state(draw, sys, egress_fault=True, ingress_fail=True):

        new_state = {}

        for cont in sys.system.keys():
            new_state[cont] = deepcopy(sys.system[cont])
            # remove logs if present as this isnt generatable.
            del new_state[cont]['logs']
            new_state[cont]['status'] = st.just(new_state[cont]['status'])
            new_state[cont]['ip'] = st.just(new_state[cont]['ip'])
            no_fault = st.just({"impaired": False})

            if ingress_fail == True:
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

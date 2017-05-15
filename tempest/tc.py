class Tc():
    """
    helpful links:
    - https://www.systutorials.com/docs/linux/man/8-tc-netem/

    """



    def __init__(self):
        """
        tc qdisc add dev eth0 root handle 1: htb default 1;
        tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
        tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
        tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
        tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
        tc qdisc add dev eth0 parent 1:2 handle 3: netem delay 1500ms;
        """

        self.initial_command = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
{filter}tc qdisc add dev eth0 parent {parent_handle} handle {child_handle} netem{limit}{delay}{loss_random}{loss_state}{corrupt}{duplicate}{reorder}{rate};
"""

        self.filter_command = ""
        self.limit_command = ""
        self.delay_command = ""
        self.loss_random_command = ""
        self.loss_state_command = ""
        self.corrupt_command = ""
        self.duplicate_command = ""
        self.reorder_command = ""
        self.rate_command = ""
        self.root = "1:"
        self.handle = "1:"
        self.class_id = "1:1"
        self.flow_id = ""
        self.filter_applied = False


    def filter(self, ip):
        if ip is not None:
            qdisc_1_parent = self._inc_minor(self.root)
            qdisc_handle = self._inc_major(qdisc_1_parent)
            self.handle = qdisc_handle
            class_id = self._inc_minor(self.class_id)
            self.class_id = class_id
            self.handle = self.class_id

            self.filter_command = """tc qdisc add dev eth0 parent {parent} handle {handle} pfifo limit 5000;
tc class add dev eth0 parent {root} classid {class_id} htb rate 1000mbit;
tc filter add dev eth0 parent {root} protocol ip prio 2 u32 flowid {class_id} match ip dst {ip};
""".format(root=self.root,
           parent=qdisc_1_parent,
           handle=qdisc_handle,
           class_id=class_id,
           ip=ip)
            self.filter_applied = True
        else:
            self.filter_applied = False
        return self

    def _inc_major(self, handle):
        major, minor = handle.split(":")
        major = int(major) + 1
        return "{major}:".format(major=major, minor=minor)

    def _inc_minor(self, handle):
        major, minor = handle.split(":")
        if minor == '':
            minor = 0
        minor = int(minor) + 1
        return "{major}:{minor}".format(major=major, minor=minor)

    def limit(self, packets):
        self.limit_command = ' limit {0}'.format(packets)
        return self

    def delay(self, time, jitter=None, correlation=None, distribution=None):
        command = " delay {time}ms".format(time=time)
        if jitter is not None:
            correlation = correlation or 0
            jitter = jitter or 1
            command += " {jitter}ms {correlation}%".format(
                jitter=jitter, correlation=correlation)

        if distribution is not None:
            command += " distribution {distribution}".format(
                distribution=distribution)

        self.delay_command = command
        return self

    def loss_random(self, percent):
        command = " loss random {percent}%".format(percent=percent)
        self.loss_random_command = command
        return self

    def loss_state(self, p13, p31=False, p32=False, p23=False, p14=False):
        command = " loss state {p13}%".format(p13=p13)
        if p31 is not False:
            command += " {p31}%".format(p31=p31)
        if p32 is not False:
            command += " {p32}%".format(p32=p32)
        if p23 is not False:
            command += " {p23}%".format(p23=p23)
        if p14 is not False:
            command += " {p14}%".format(p14=p14)

        self.loss_state_command = command
        return self

    def corrupt(self, percent, correlation=None):
        command = " corrupt {percent}%".format(percent=percent)
        if correlation is not None:
            command += " {correlation}%".format(correlation=correlation)
        self.corrupt_command = command
        return self

    def duplicate(self, percent, correlation=None):
        command = " duplicate {percent}%".format(percent=percent)
        if correlation is not None:
            command += " {correlation}%".format(correlation=correlation)
        self.duplicate_command = command
        return self

    def reorder(self, percent, correlation=None, distance=None):
        command = " reorder {percent}%".format(percent=percent)
        if correlation is not None:
            command += " {correlation}%".format(correlation=correlation)
        if distance is not None:
            command += " gap {distance}".format(distance=distance)
        self.reorder_command = command
        return self

    def rate(self,
             rate,
             rate_units,
             packet_overhead=None,
             cellsize=None,
             cellsize_overhead=None):
        command = " rate {rate}{rate_units}".format(rate=rate, rate_units=rate_units)
        if packet_overhead is not None:
            command += " {packet_overhead}".format(packet_overhead=packet_overhead)
        if cellsize is not None:
            command += " {cellsize}".format(cellsize=cellsize)
        if cellsize_overhead is not None:
            command += " {cellsize_overhead}".format(cellsize_overhead=cellsize_overhead)

        self.rate_command = command
        return self

    def command(self):
        attrs = [
            self.filter_command,
            self.limit_command,
            self.delay_command,
            self.loss_random_command,
            self.loss_state_command,
            self.corrupt_command,
            self.duplicate_command,
            self.reorder_command,
            self.rate_command,
        ]

        if all([value == "" for value in attrs]):
            return self.clean()

        if self.delay_command is "" and self.reorder_command is not "":
            raise Exception("The delay function must be specified when using reorder")
        qdisc_parent = self.handle
        if self.filter_applied is True:
            qdisc_handle = self._inc_major(qdisc_parent)
            qdisc_handle = self._inc_major(qdisc_handle)
        else:
            qdisc_parent = self._inc_minor(qdisc_parent)
            qdisc_handle = self._inc_major(qdisc_parent)

        raw = self.initial_command.format(
            parent_handle=qdisc_parent,
            child_handle=qdisc_handle,
            filter=self.filter_command,
            limit=self.limit_command,
            delay=self.delay_command,
            loss_random=self.loss_random_command,
            loss_state=self.loss_state_command,
            corrupt=self.corrupt_command,
            duplicate=self.duplicate_command,
            reorder=self.reorder_command,
            rate=self.rate_command)
        raw = raw.rstrip()
        return raw

    def clean(self):
        return 'tc qdisc del dev eth0 root;'

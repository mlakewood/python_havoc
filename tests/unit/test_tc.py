import unittest

from tempest.tc import Tc

class TestTc(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None #pylint: disable=invalid-name


    def test_tc_with_filter_all(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem limit 1000 delay 1500ms 20ms 20% \
distribution normal loss random 50% loss state 10% 11% 12% 13% 14% corrupt 10% 25% \
duplicate 10% 25% reorder 10% 25% gap 10 rate 100mbit 5 5 5;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').limit(1000).\
                                          delay(1500, 20, 20, 'normal').\
                                          loss_random(50).\
                                          loss_state(10, p31=11, p32=12, p23=13, p14=14).\
                                          corrupt(10, correlation=25).\
                                          duplicate(10, correlation=25).\
                                          reorder(10, correlation=25, distance=10).\
                                          rate(100,
                                               'mbit',
                                               packet_overhead=5,
                                               cellsize=5,
                                               cellsize_overhead=5).\
                                          command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem delay 1500ms 20ms 20% distribution normal;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').delay(1500, 20, 20, 'normal').command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_limit(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem limit 1000;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').limit(1000).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_loss_random(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem loss random 50%;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').loss_random(50).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_loss_state(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem loss state 10% 11% 12% 13% 14%;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').loss_state(10, p31=11, p32=12, p23=13, p14=14).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_corrupt(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem corrupt 10% 25%;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').corrupt(10, correlation=25).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_duplication(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem duplicate 10% 25%;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').duplicate(10, correlation=25).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_reordering(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem delay 1000ms reorder 10% 25% gap 10;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').delay(1000).\
                 reorder(10, correlation=25, distance=10).command()
        self.assertEqual(expected_output, output)

    def test_tc_with_filter_rate(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: pfifo limit 5000;
tc class add dev eth0 parent 1: classid 1:2 htb rate 1000mbit;
tc filter add dev eth0 parent 1: protocol ip prio 2 u32 flowid 1:2 match ip dst 8.8.4.4;
tc qdisc add dev eth0 parent 1:2 handle 3: netem rate 100mbit 5 5 5;"""

        tc_obj = Tc()
        output = tc_obj.filter('8.8.4.4').rate(100,
                                               'mbit',
                                               packet_overhead=5,
                                               cellsize=5,
                                               cellsize_overhead=5).command()

        self.assertEqual(expected_output, output)


    def test_tc_without_filter(self):
        expected_output = """tc qdisc add dev eth0 root handle 1: htb default 1;
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit;
tc qdisc add dev eth0 parent 1:1 handle 2: netem delay 1500ms;"""

        tc_obj = Tc()
        output = tc_obj.delay(1500).command()

        self.assertEqual(expected_output, output)

    def test_tc_reorder_without_delay(self):
        """
        There is a validation in the command() method that makes sure
        that if the reorder command is given that the delay is supplied as well.
        This test makes sure that this works as designed.
        """
        tc_obj = Tc()
        with self.assertRaises(Exception) as context:
            tc_obj.reorder(15).command()

        self.assertEqual("The delay function must be specified when using reorder",
                         str(context.exception))

        tc_obj = Tc()
        tc_obj.delay(1500).reorder(15).command()

        tc_obj = Tc()
        tc_obj.delay(1500).command()

        tc_obj = Tc()
        tc_obj.limit(1000).command()


    def test_tc_empty(self):
        """
        There is a validation in the command() method that makes sure
        that if the reorder command is given that the delay is supplied as well.
        This test makes sure that this works as designed.
        """
        tc_obj = Tc()
        expected_output = 'tc qdisc del dev eth0 root;'
        self.assertEqual(tc_obj.command(), expected_output)

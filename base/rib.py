import netaddr
import time
import datetime

from ryu.lib.dpid import dpid_to_str
from ryu.lib.port_no import port_no_to_str

class RoutingTable(dict):
    """
        base class for RoutingTable,
        the protocol should implement the following two methods.
    """
    def update_entry(self, subnet, receive_port, neighbor_port=None, metric=0):
        raise NotImplementedError

    def update_by_neighbor(self, receive_port, neighbor_port, tbl):
        raise NotImplementedError

class RoutingEntry(object):
    """
        base class for RoutingEntry.
    """
    def __init__(self, receive_port, neighbor_port, metric=0):
        self.receive_port = receive_port
        self.neighbor_port = neighbor_port
        self.metric = metric
        self.last_update = time.time()
        self.flow_entry = None

    def to_dict(self):
        r = {}
        if self.receive_port.port_no:
            r['out_port'] = port_no_to_str(self.receive_port.port_no)
        if self.metric != 0:
            r['next_hop'] = dpid_to_str(self.neighbor_port.dpid)
        r['metric'] = self.metric
        r['last_update'] = datetime.datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S')
        r['flow_entry'] = self.flow_entry

        return r
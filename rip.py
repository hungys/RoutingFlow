import netaddr
import time
import datetime
import random
import logging
from threading import Thread

from ryu.lib.dpid import dpid_to_str
from ryu.lib.port_no import port_no_to_str

import base.rib as rib

logger = logging.getLogger(__name__)

TIMER_BASE_MIN = 25
TIMER_BASE_MAX = 35

class RIPRoutingTable(rib.RoutingTable):
    def __init__(self, dpid):
        """
            set advertise_interval with a random value between
            TIMER_BASE_MIN and TIMER_BASE_MAX to prevent all the
            swtiches broadcast and update in the same time.
        """
        self.dpid = dpid
        self.advertise_interval = random.randint(TIMER_BASE_MIN, TIMER_BASE_MAX + 1)
        self.gc_interval = self.advertise_interval * 2
        self.expire_time = self.advertise_interval * 3
        self.updating = False

        self.init_thread()

    def init_thread(self):
        """
            create a thread to do garbage collect.
        """
        logger.info('garbage collector thread start with interval %ds (dpid=%s)', self.gc_interval, dpid_to_str(self.dpid))
        gc_thread = Thread(target=self.garbage_collect)
        gc_thread.setDaemon(True)
        gc_thread.start()

    # override
    def update_entry(self, subnet, receive_port, neighbor_port=None, metric=0):
        """
            update single routing entry.
        """
        try:
            r = self[subnet]
            r.receive_port = receive_port
            r.neighbor_port = neighbor_port
            r.metric = metric
            r.last_update = time.time()
        except KeyError:
            self[subnet] = RIPRoutingEntry(receive_port, neighbor_port, metric)

    # override
    def update_by_neighbor(self, receive_port, neighbor_port, tbl):
        """
            (1) mark the expired entry as invalid entry.
            (2) update self routing table by comparing with routing table
            advertised by neighbors.
        """
        if self.updating:
            return
        self.updating = True

        self.mark_invalid_route()

        for subnet, entry in tbl.items():
            if subnet in self.keys():
                if self[subnet].metric == 0:
                    self[subnet].last_update = time.time()
                elif entry.metric + 1 < self[subnet].metric:
                    self.update_entry(subnet, receive_port, neighbor_port, entry.metric + 1)
                else:
                    # self[subnet].last_update = time.time()
                    continue
            else:
                self.update_entry(subnet, receive_port, neighbor_port, entry.metric + 1)
        self.updating = False

    def mark_invalid_route(self):
        """
            set metric to 16 if the routing entry expired.
            metric=16 is regarded as disconnected.
        """
        last_valid_time = time.time() - self.expire_time

        for subnet, entry in self.items():
            if entry.last_update < last_valid_time:
                entry.metric = 16

    def garbage_collect(self):
        """
            iterate the whole routing table and delete routing entries
            with metric=16.
        """
        for subnet, entry in self.items():
            if entry.metric == 16:
                logger.info('GC: route from dpid=%s to %s', dpid_to_str(self.dpid), str(subnet))
                del self[subnet]

        time.sleep(self.gc_interval)

class RIPRoutingEntry(rib.RoutingEntry):
    def __init__(self, receive_port, neighbor_port, metric=0):
        self.receive_port = receive_port
        self.neighbor_port = neighbor_port
        self.metric = metric
        self.last_update = time.time()

    def to_dict(self):
        r = {}
        if self.receive_port.port_no:
            r['out_port'] = port_no_to_str(self.receive_port.port_no)
        if self.metric != 0:
            r['next_hop'] = dpid_to_str(self.neighbor_port.dpid)
        r['metric'] = self.metric
        r['last_update'] = datetime.datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S')

        return r
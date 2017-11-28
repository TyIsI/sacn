# This file is under MIT license. The license file can be obtained in the root directory of this module.

import threading
import socket
import time
from .output import Output

DEFAULT_PORT = 5568
SEND_OUT_INTERVAL_ms = 1000


class OutputThread(threading.Thread):
    def __init__(self, outputs, bind_address, bind_port: int = DEFAULT_PORT, fps: int = 30):
        super().__init__(name='sACN sending/sender thread')
        self._outputs = outputs
        self._bindAddress = bind_address
        self.enabled_flag: bool = True
        self.fps: int = fps
        self._bind_port = bind_port
        self._socket: socket.socket = None

    def run(self):
        self._socket = socket.socket(socket.AF_INET,  # Internet
                                 socket.SOCK_DGRAM)  # UDP
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:  # Not all systems support multiple sockets on the same port and interface
            pass
        self._socket.bind((self._bindAddress, self._bind_port))

        self.enabled_flag = True
        while self.enabled_flag:
            # go through the list of outputs and send everything out that has to be send out
            for output in self._outputs.values():
                # send out when the 1 second interval is over
                if abs(current_time_millis() - output._last_time_send) > SEND_OUT_INTERVAL_ms or output._changed:
                    # make socket multicast-aware: (set TTL)
                    self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, output.ttl)
                    self.send_out(output)
            time.sleep(1 / self.fps)  # this is just a rough temp solution
        self._socket.close()

    def send_out(self, output: Output):
        # 1st: Destination (check if multicast)
        if output.multicast:
            udp_ip = output._packet.calculate_multicast_addr()
            # make socket multicast-aware: (set TTL) for some reason that does not work here,
            # so its in the run method from above
            # socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, sending.ttl)
        else:
            udp_ip = output.destination

        MESSAGE = bytearray(output._packet.getBytes())
        self._socket.sendto(MESSAGE, (udp_ip, DEFAULT_PORT))
        output._last_time_send = current_time_millis()
        # increase the sequence counter
        output._packet.sequence_increase()
        # the changed flag is not necessary any more
        output._changed = False


def current_time_millis():
    return int(round(time.time() * 1000))

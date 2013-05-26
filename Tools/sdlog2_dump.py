#!/usr/bin/env python

"""Parse and dump binary log generated by sdlog2
    
    Usage: python sdlog2_dump.py <log.bin>"""

__author__  = "Anton Babushkin"
__version__ = "0.2"

import struct, sys

class BufferUnderflow(Exception):
    pass

class SDLog2Parser:
    BLOCK_SIZE = 8192
    MSG_HEADER_LEN = 3
    MSG_HEAD1 = 0xA3
    MSG_HEAD2 = 0x95
    MSG_FORMAT_PACKET_LEN = 89
    MSG_FORMAT_STRUCT = "BB4s16s64s"
    MSG_TYPE_FORMAT = 0x80
    FORMAT_TO_STRUCT = {
        "b": ("b", None),
        "B": ("B", None),
        "h": ("h", None),
        "H": ("H", None),
        "i": ("i", None),
        "I": ("I", None),
        "f": ("f", None),
        "n": ("4s", None),
        "N": ("16s", None),
        "Z": ("64s", None),
        "c": ("h", 0.01),
        "C": ("H", 0.01),
        "e": ("i", 0.01),
        "E": ("I", 0.01),
        "L": ("i", 0.0000001),
        "M": ("b", None),
        "q": ("q", None),
        "Q": ("Q", None),
    }
    
    def __init__(self):
        return

    def reset(self):
        self.msg_descrs = {}
        self.buffer = ""
        self.ptr = 0
    
    def process(self, fn):
        self.reset()
        f = open(fn, "r")
        while True:
            chunk = f.read(self.BLOCK_SIZE)
            if len(chunk) == 0:
                break
            self.buffer = self.buffer[self.ptr:] + chunk
            self.ptr = 0
            while self._bytes_left() >= self.MSG_HEADER_LEN:
                head1 = ord(self.buffer[self.ptr])
                head2 = ord(self.buffer[self.ptr+1])
                if (head1 != self.MSG_HEAD1 or head2 != self.MSG_HEAD2):
                    raise Exception("Invalid header: %02X %02X, must be %02X %02X" % (head1, head2, self.MSG_HEAD1, self.MSG_HEAD2))
                msg_type = ord(self.buffer[self.ptr+2])
                if msg_type == self.MSG_TYPE_FORMAT:
                    self._parse_msg_descr()
                else:
                    msg_descr = self.msg_descrs[msg_type]
                    if msg_descr == None:
                        raise Exception("Unknown msg type: %i" % msg_type)
                    msg_length = msg_descr[0]
                    if self._bytes_left() < msg_length:
                        break
                    self._parse_msg(msg_descr)
        f.close()

    def _bytes_left(self):
        return len(self.buffer) - self.ptr

    def _parse_msg_descr(self):
        if self._bytes_left() < self.MSG_FORMAT_PACKET_LEN:
            raise BufferUnderflow("Data is too short: %i bytes, need %i" % (self._bytes_left(), self.MSG_FORMAT_PACKET_LEN))
        data = struct.unpack(self.MSG_FORMAT_STRUCT, self.buffer[self.ptr + 3 : self.ptr + self.MSG_FORMAT_PACKET_LEN])
        msg_type = data[0]
        msg_length = data[1]
        msg_name = data[2].strip('\0')
        msg_format = data[3].strip('\0')
        msg_labels = data[4].strip('\0').split(",")
        # Convert msg_format to struct.unpack format string
        msg_struct = ""
        msg_mults = []
        for c in msg_format:
            try:
                f = self.FORMAT_TO_STRUCT[c]
                msg_struct += f[0]
                msg_mults.append(f[1])
            except KeyError as e:
                raise Exception("Unsupported format char: %s in message %s (0x%02X)" % (c, msg_name, msg_type))
        msg_struct = "<" + msg_struct
        print msg_format, msg_struct
        print "MSG FORMAT: type = %i, length = %i, name = %s, format = %s, labels = %s, struct = %s, mults = %s" % (msg_type, msg_length, msg_name, msg_format, str(msg_labels), msg_struct, msg_mults)
        self.msg_descrs[msg_type] = (msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults)
        self.ptr += self.MSG_FORMAT_PACKET_LEN

    def _parse_msg(self, msg_descr):
        msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults = msg_descr
        data = list(struct.unpack(msg_struct, self.buffer[self.ptr+self.MSG_HEADER_LEN:self.ptr+msg_length]))
        s = []
        for i in xrange(len(data)):
            if type(data[i]) is str:
                data[i] = data[i].strip('\0')
            m = msg_mults[i]
            if m != None:
                data[i] = data[i] * m
            s.append(msg_labels[i] + "=" + str(data[i]))
        
        print "MSG %s: %s" % (msg_name, ", ".join(s))
        self.ptr += msg_length
    
def _main():
    if len(sys.argv) < 2:
        print "Usage:\npython sdlog2_dump.py <log.bin>"
        return
    fn = sys.argv[1]
    parser = SDLog2Parser()
    parser.process(fn)

if __name__ == "__main__":
    _main()

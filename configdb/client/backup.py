import logging
import pickle
import struct
import zlib
from configdb import exceptions

log = logging.getLogger(__name__)


class RecordError(Exception):
    pass


def crc32(s):
    return zlib.adler32(s) & 0xffffffff


def record_write(fd, entity_name, obj):
    data = pickle.dumps((entity_name, obj),
                        pickle.HIGHEST_PROTOCOL)
    fd.write(struct.pack('I', len(data)))
    fd.write(data)
    fd.write(struct.pack('I', crc32(data)))


def record_read(fd):
    data_len_str = fd.read(4)
    if not data_len_str:
        raise EOFError()
    data_len, = struct.unpack('I', data_len_str)
    data = fd.read(data_len)
    if len(data) != data_len:
        raise RecordError('short data')
    data_crc, = struct.unpack('I', fd.read(4))
    if crc32(data) != data_crc:
        raise RecordError('corrupted record')
    return pickle.loads(data)


class Dumper(object):

    def __init__(self, conn):
        self.conn = conn

    def dump(self, fd):
        for entity in self.conn.schema.get_entities():
            for obj in self.conn.find(entity.name, {}):
                record_write(fd, entity.name, obj)

    def restore(self, fd):
        while True:
            try:
                entity_name, obj = record_read(fd)
                self.conn.create(entity_name, obj)
            except EOFError:
                break
            except Exception, e:
                log.error('skipped record: %s', e)


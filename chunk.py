""" Chunks a file into a bunch of files based on a delimiter and a size limit """

from io import RawIOBase

DEFAULT_LIMIT = 1024 * 1024
DEFAULT_BUFFER_SIZE = 4 * 1024
DEFAULT_DELIMITER = b'\n'

def chunk(
        source,
        limit=DEFAULT_LIMIT,
        delimiter=DEFAULT_DELIMITER,
        buffer_size=DEFAULT_BUFFER_SIZE
):
    last = LimitedReader(source, limit=limit, delimiter=delimiter, buffer_size=buffer_size)
    yield last

    while True:
        if not last.eof:
            raise ValueError("You have not finished reading the previous chunk")
        if last.source_eof and not last.remainder:
            break

        current = LimitedReader(
            source,
            limit=limit,
            delimiter=delimiter,
            buffer_size=buffer_size,
            remainder=last.remainder
        )
        yield current
        last = current

class LimitedReader(RawIOBase):

    def __init__(
            self,
            source,
            limit=DEFAULT_LIMIT,
            delimiter=DEFAULT_DELIMITER,
            buffer_size=DEFAULT_BUFFER_SIZE,
            remainder=b''
    ):
        super().__init__()
        self.source = source
        self.limit = limit
        self.delimiter = delimiter
        self.buffer = bytearray(buffer_size)
        self.remainder = remainder
        self.eof = False
        self.source_eof = False

    def readinto(self, output):
        if self.eof:
            return 0

        output_size = len(output)
        raw_data = self._read(output_size)
        read_size = len(raw_data)

        if read_size > self.limit:
            delimiter_index = raw_data.find(self.delimiter, max(self.limit - 1, 0))
            if delimiter_index != -1:
                self.eof = True
                return self._write(output, delimiter_index + 1, raw_data)

        if read_size < output_size:
            self.eof = True

        return self._write(output, read_size, raw_data)

    def _read(self, size):
        if len(self.remainder) >= size:
            raw_data = self.remainder
        else:
            raw_data = self._read_source()

        data, self.remainder = raw_data[:size], raw_data[size:]
        return data

    def _read_source(self):
        read_size = self.source.readinto(self.buffer)
        if read_size < len(self.buffer):
            self.source_eof = True
        return self.remainder + self.buffer[:read_size]

    def _write(self, output, output_size, data):
        output[:], self.remainder = data[:output_size], data[output_size:]
        read_size = min(len(data), output_size)
        self.limit = self.limit - read_size
        return read_size

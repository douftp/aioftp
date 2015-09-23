import time

import nose

import aioftp
from common import *


@aioftp_setup(
    client_args=(
        [],
        {
            "read_speed_limit": 100 * 1024  # 100 Kib
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_read_throttle(loop, client, server, *, tmp_dir):

    big_file = tmp_dir / "foo.txt"
    with big_file.open("wb") as fout:

        fout.write(b"-" * (3 * 100 * 1024))  # 300 Kib

    start = time.perf_counter()
    yield from client.login()
    stream = yield from client.download_stream("tests/foo/foo.txt")
    count = 0
    while True:

        data = yield from stream.read()
        if not data:

            yield from stream.finish()
            break

        count += len(data)

    nose.tools.eq_(count, 3 * 100 * 1024)
    nose.tools.ok_(2.5 < (time.perf_counter() - start) < 3.5)
    big_file.unlink()


@aioftp_setup(
    client_args=(
        [],
        {
            "read_speed_limit": 100 * 1024  # 100 Kib
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_write_with_read_throttle(loop, client, server, *, tmp_dir):

    start = time.perf_counter()
    big_file = tmp_dir / "foo.txt"
    yield from client.login()
    stream = yield from client.upload_stream("tests/foo/foo.txt")
    count = 0
    for _ in range(3 * 100):  # 300 Kib

        yield from stream.write(b"-" * 1024)

    yield from stream.finish()

    with big_file.open() as fin:

        data = fin.read()

    nose.tools.eq_(len(data), 3 * 100 * 1024)
    nose.tools.ok_((time.perf_counter() - start) < 0.1)
    big_file.unlink()


@aioftp_setup(
    client_args=(
        [],
        {
            "write_speed_limit": 100 * 1024  # 100 Kib
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_read_with_write_throttle(loop, client, server, *, tmp_dir):

    big_file = tmp_dir / "foo.txt"
    with big_file.open("wb") as fout:

        fout.write(b"-" * (3 * 100 * 1024))  # 300 Kib

    start = time.perf_counter()
    yield from client.login()
    stream = yield from client.download_stream("tests/foo/foo.txt")
    count = 0
    while True:

        data = yield from stream.read()
        if not data:

            yield from stream.finish()
            break

        count += len(data)

    nose.tools.eq_(count, 3 * 100 * 1024)
    nose.tools.ok_((time.perf_counter() - start) < 0.1)
    big_file.unlink()


@aioftp_setup(
    client_args=(
        [],
        {
            "write_speed_limit": 100 * 1024  # 100 Kib
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_write_throttle(loop, client, server, *, tmp_dir):

    start = time.perf_counter()
    big_file = tmp_dir / "foo.txt"
    yield from client.login()
    stream = yield from client.upload_stream("tests/foo/foo.txt")
    count = 0
    for _ in range(3 * 100):  # 300 Kib

        yield from stream.write(b"-" * 1024)

    yield from stream.finish()

    with big_file.open() as fin:

        data = fin.read()

    nose.tools.eq_(len(data), 3 * 100 * 1024)
    nose.tools.ok_(2.5 < (time.perf_counter() - start) < 3.5)
    big_file.unlink()


class SlowPathIO(aioftp.PathIO):

    @aioftp.with_timeout
    @asyncio.coroutine
    def write(self, fout, data):

        timeout = len(data) / (100 * 1024)  # sleep as 100 Kib per second write
        print("sleep for", timeout)
        yield from asyncio.sleep(timeout, loop=self.loop)
        yield from super().write(fout, data)


@aioftp_setup(
    client_args=(
        [],
        {
            "write_speed_limit": 100 * 1024,  # 100 Kib per second
            "path_io_factory": SlowPathIO,
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_write_throttle_with_slow_io(loop, client, server, *, tmp_dir):

    start = time.perf_counter()
    big_file = tmp_dir / "foo.txt"
    with big_file.open("wb") as fout:

        fout.write(b"-" * 3 * 100 * 1024)

    yield from client.login()
    yield from client.download(
        "tests/foo/foo.txt",
        "tests/foo/bar.txt",
        write_into=True
    )

    nose.tools.ok_(2.5 < (time.perf_counter() - start) < 3.5)
    big_file.unlink()
    received = tmp_dir / "bar.txt"
    received.unlink()


@aioftp_setup(
    client_args=(
        [],
        {
            "read_speed_limit": 200 * 1024,  # 200 Kib per second
            "path_io_factory": SlowPathIO,
        },
    ))
@with_connection
@with_tmp_dir("foo")
def test_client_read_throttle_with_too_slow_io(loop, client, server, *,
                                               tmp_dir):

    start = time.perf_counter()
    big_file = tmp_dir / "foo.txt"
    with big_file.open("wb") as fout:

        fout.write(b"-" * 3 * 100 * 1024)

    yield from client.login()
    yield from client.download(
        "tests/foo/foo.txt",
        "tests/foo/bar.txt",
        write_into=True
    )

    nose.tools.ok_(2.5 < (time.perf_counter() - start) < 3.5)
    big_file.unlink()
    received = tmp_dir / "bar.txt"
    received.unlink()


if __name__ == "__main__":

    import logging
    import os

    os.environ["AIOFTP_TESTS"] = "PathIO"
    logging.basicConfig(
        level=logging.INFO
    )

    test_client_write_throttle()
    print("done")
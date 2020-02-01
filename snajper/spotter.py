"""
Watches for file changes,
looks up the tests for those files in coverage's measurement contexts ("who-tests-what") database,
and then runs these tests.
"""

import logging
from pathlib import Path
import subprocess
import sys
import sqlite3
import time
from typing import List

from watchdog.observers import Observer
import watchdog.events

# TODO also trigger tests if the tests change

# TODO what about the coverage DB changing when you rerun tests?
# After we run a subset of tests we dump the broader coverage info, so we'll just be detecting
# changes in the files related to that small changeset.

# Notes
# =========
# sometimes, tests just start taking too long.
# And then you're reluctant to run them, and then you make goofs.
#
# Yeah... you should keep your tests short, but that's effort.
# Maybe there's not time for that always.
#
# Would be better if we could pick out the lines changed in the file, then we wouldn't run
# all the tests for that file, just the ones for the lines changed.
# Is this possible in the general case?

class SelectiveTestRunner(watchdog.events.FileSystemEventHandler):
    """Logs all the events captured."""

    def on_moved(self, event):
        what = 'directory' if event.is_directory else 'file'
        if event.dest_path.endswith('.py'):
            # TODO implement
            logging.info("Moved %s: from %s to %s", what, event.src_path,
                         event.dest_path)

    def on_deleted(self, event):
        what = 'directory' if event.is_directory else 'file'
        if event.src_path.endswith('.py'):
            # TODO implement
            logging.info("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        what = 'directory' if event.is_directory else 'file'
        if event.src_path.endswith('.py'):
            logging.info(">>> Modified %s: %s", what, event.src_path)
            run_tests_for_file(event.src_path)


def run_tests_for_file(file: str):
    # TODO why can't we have this before logging in on_modified?
    subprocess.run('clear')

    tests_for_the_file = _get_tests_to_run(file)

    pytest_command = subprocess.check_output('which pytest'.split()).decode().strip()
    subprocess.run(
        [pytest_command,  '-v'] + tests_for_the_file,
        env={'PYTHONPATH': 'tests/sample_project'},
    )


def _get_tests_to_run(file: str):
    con = sqlite3.connect('.coverage')
    sql = """
select f.path, c.context
from file f
join line_bits l
on f.id = l.file_id
join context c
on l.context_id = c.id
where c.context <> '';
"""
    data = con.execute(sql).fetchall()
    file_abs_path = str(Path(file).absolute())
    # col 0: path, col 1: test as dotted function notation
    tests_for_the_file = [row[1] for row in data if row[0] == file_abs_path]
    return [_get_test_for_pytest(test, data) for test in tests_for_the_file]


def _get_test_for_pytest(test: str, files: List[str]):
    path_bit = '/'.join(test.split('.')[:-1])
    test_file = next(row[0] for row in files if path_bit in row[0])
    test_name = test.split('.')[-1]
    return f'{test_file}::{test_name}'


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    observer = Observer()
    # TODO filter to only python files
    observer.schedule(SelectiveTestRunner(), path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

import contextlib
import pathlib
import sys
import os
import json


def read_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


@contextlib.contextmanager
def smart_open(filename=None, mode='w', binary=False, create_parent_dirs=True):
    fh = get_file_handle(filename, mode, binary, create_parent_dirs)

    try:
        yield fh
    finally:
        fh.close()


def delete_file(filename: str):
    if os.path.isfile(filename):
        os.remove(filename)
    else:
        raise FileNotFoundError(f"Can't delete: file not found: {filename}")


def get_file_handle(filename, mode='w', binary=False, create_parent_dirs=True):
    if create_parent_dirs and filename is not None:
        dirname = os.path.dirname(filename)
        pathlib.Path(dirname).mkdir(parents=True, exist_ok=True)
    full_mode = mode + ('b' if binary else '')
    is_file = filename and filename != '-'
    if is_file:
        fh = open(filename, full_mode)
    elif filename == '-':
        fd = sys.stdout.fileno() if mode == 'w' else sys.stdin.fileno()
        fh = os.fdopen(fd, full_mode)
    else:
        raise FileNotFoundError(filename)
    return fh


def write_to_file(file, content):
    with smart_open(file, 'w') as file_handle:
        file_handle.write(content)


# Utils for last_synced_files
def init_last_synced_file(value, last_synced_file):
    if os.path.isfile(last_synced_file):
        raise ValueError(
            f'{last_synced_file} should not exist if any --start option is specified. '
            f'Either remove the {last_synced_file} file or the --start-block option.')
    write_last_synced_file(last_synced_file, value)


def write_last_synced_file(file, last_synced_value):
    write_to_file(file, str(last_synced_value) + '\n')


def read_last_synced_file(file):
    with smart_open(file, 'r') as file_handle:
        return int(file_handle.read())


# Utils for log files
def init_log_file(log_file):
    if os.path.exists(log_file):
        os.remove(log_file)


def append_log_file(line, log_file):
    _file = open(log_file, 'a+')
    _file.write(f"{line}\n")
    _file.close()



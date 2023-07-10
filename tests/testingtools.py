import inspect
import os


def data_dir():
    current_file_path = os.path.dirname(inspect.getfile(inspect.currentframe()))
    data_dir = os.path.join(current_file_path, "data")
    data_dir = os.path.abspath(data_dir)
    assert os.path.isdir(data_dir), data_dir + " does not exist."
    return data_dir

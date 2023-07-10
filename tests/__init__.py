from .testingtools import data_dir


def setup_package():
    """Nosetests package setup function (run when tests are done).
    See http://nose.readthedocs.org/en/latest/writing_tests.html#test-packages

    - Copies the original data files to be restored after testing.
    - Sets a non-interactive backend for matplotlib (even though we don't
    show any figures, it can import PyQt, for example).
    """

    # Create backups of the data files
    import os
    import shutil
    from glob import glob
    from os.path import isdir, join

    data_path = data_dir()

    target_paths = glob(join(data_path, "*.h5"))
    target_paths.append(join(data_path, "random_csv"))

    for original_fn in target_paths:
        target_fn = original_fn + ".original"
        if isdir(original_fn):
            shutil.copytree(original_fn, target_fn)
        else:
            shutil.copyfile(original_fn, target_fn)

    # Use the most basic Matplotlib backend
    import matplotlib

    matplotlib.use("AGG")


def teardown_package():
    """Nosetests package teardown function (run when tests are done).
    See http://nose.readthedocs.org/en/latest/writing_tests.html#test-packages

    Closes remaining open HDF5 files to avoid warnings and resets the
    files in data_dir to their original states.
    """

    # Workaround for open .h5 files on Windows
    from tables.file import _open_files

    _open_files.close_all()

    # Restore the original copies of the data files
    import os
    import shutil
    from glob import glob
    from os.path import isdir, join

    for original_fn in glob(join(data_dir(), "*.original")):
        target_fn = original_fn[: original_fn.rfind(".original")]
        try:
            if isdir(target_fn):
                shutil.rmtree(target_fn)
            else:
                os.remove(target_fn)

            os.rename(original_fn, target_fn)

        except:
            warnings.warn('Could not restore file or directory "{}"'.format(target_fn))

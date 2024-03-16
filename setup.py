#!/usr/bin/env python

import sys
import os
import time
import shutil
import tempfile

# configurables

install_to = "/var/ordinance"
source_url = "https://github.com/Kalamuwu/Ordinance"



download_into_tmpdir = '--skip-download' not in sys.argv
verbose = '-v' in sys.argv or '--verbose' in sys.argv
quiet = '-q' in sys.argv or '--quiet' in sys.argv

_print = print
def print(*args, loud: bool = False, **kwargs):
    if loud or not quiet: _print(*args, **kwargs)

def run(cmd) -> None:
    if verbose: print(f"> {cmd}")
    assert os.system(cmd) == 0



total_start = time.time()
try:  # permissions check!
    if not os.path.exists(install_to):
        run(f"mkdir '{install_to}'")
    permissions_check = os.path.join(install_to, 'permissions_check')
    run(f"touch '{permissions_check}'")
    run(f"rm '{permissions_check}'")
except:
    raise PermissionError(f"User cannot write to install directory")
print(f"Installing to path {install_to}")



if download_into_tmpdir:
    print("Downloading new source...")
    download_dir = tempfile.mkdtemp()
    dl_start = time.time()
    try:
        ret = os.system(f"git clone '{source_url}' '{download_dir}'")
        assert ret == 0
    except:
        print("Downloading new source failed!", loud=True)
        run(f"rm -rf '{download_dir}'")
        exit(2)
    dl_time = time.time() - dl_start
    print(f"Download step took {dl_time:.3f} seconds.")

else:
    print(f"Skipping new download, using current directory.")
    download_dir = os.getcwd()



print("Copying new source...")
try:
    for file in ['core', 'ordinance', 'README.md', 'run.py', 'setup.py']:
        old_path = os.path.join(download_dir, file)
        new_path = os.path.join(install_to, file)

        if os.path.exists(new_path):
            run(f"rm -rf '{new_path}'")
        run(f"cp -r '{old_path}' '{new_path}'")
    
    for folder in ['storage', 'extensions', 'logs']:
        path = os.path.join(install_to, folder)
        if not os.path.exists(path):
            run(f"mkdir '{path}'")

except:
    print("Copying new source failed. Ordinance could be in corrupted state.", loud=True)
    exitcode = 3

else:
    total_time = time.time() - total_start
    print(f"Done. Setup took total {total_time:.3f} seconds.")
    exitcode = 0

finally:
    if download_into_tmpdir:
        run(f"rm -rf {download_dir}")
    exit(exitcode)

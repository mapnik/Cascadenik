import os
import os.path as systempath
import posixpath
from hashlib import md5

drives = {}

# sketchy windows only mucking to handle translating between
# native cascadenik storage of posix paths and the filesystem.
# to_posix() and un_posix() are called in cascadenik/compile.py
# but only impact non-posix systems (windows)

def get_posix_root(valid_posix_path):
    if posixpath.isdir(valid_posix_path) and not valid_posix_path.endswith(posixpath.sep):
        valid_posix_path += posixpath.sep
    else:
        valid_posix_path = posixpath.dirname(valid_posix_path)
    return valid_posix_path.split(posixpath.sep)[1] or valid_posix_path

def add_drive(drive,valid_posix_path):
    root = get_posix_root(valid_posix_path)
    if not drives.get(root):
        drives[root] = drive
        #print 'pushing drive: %s | %s | %s' % (drive,root, valid_posix_path)

def get_drive(valid_posix_path):
    return drives.get(get_posix_root(valid_posix_path))

# not currently used
def add_drive_by_hash(drive,valid_posix_path):
    # cache the drive so we can try to recreate later
    global drives
    hash = md5(valid_posix_path).hexdigest()[:8]
    drives[hash] = drive
    #print 'pushing drive: %s | %s | %s' % (drive,valid_posix_path,hash)

# not currently used
def get_drive_by_hash(valid_posix_path):
    # todo - make this smarter
    hash = md5(valid_posix_path).hexdigest()[:8]
    drive = drives.get(hash)
    if not drive:
        hash = md5(posixpath.dirname(valid_posix_path)).hexdigest()[:8]
        drive = drives.get(hash)

def to_posix(path_name):
    
    if os.name == "posix":
        return path_name
    
    else:
        drive, path = systempath.splitdrive(path_name)
        valid_posix_path = path.replace(os.sep,posixpath.sep)
        if drive:
            #add_drive_by_hash(drive,valid_posix_path)
            add_drive(drive,valid_posix_path)
        return valid_posix_path

def un_posix(valid_posix_path,drive=None):
    
    if os.name == "posix":
        return valid_posix_path
    
    else:
        global drives
        if not posixpath.isabs(valid_posix_path):
            return valid_posix_path# what to do? for now assert
        assert posixpath.isabs(valid_posix_path), "un_posix() needs an absolute posix style path, not %s" % valid_posix_path
        #drive = get_drive_by_hash(valid_posix_path)
        drive = get_drive(valid_posix_path)
        
        assert drive, "We cannot make this path (%s) local to the platform without knowing the drive" % valid_posix_path
        path = systempath.join(drive,systempath.normpath(valid_posix_path))
        return path
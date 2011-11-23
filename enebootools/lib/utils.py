# encoding: UTF-8
import os, fnmatch, os.path


def one(iterable, default=None):
    if iterable:
        for item in iterable:
            return item
    return default
    
def read_file_list(filepath, filename, errlog = None):
    fullfilename = os.path.join(filepath, filename)
    try:
        file1 = open(fullfilename, "rb")
    except Exception, e:
        if errlog: errlog("Error al abrir el fichero %s" % fullfilename)
        return []
    txt = [ line.strip() for line in file1 ]
    file1.close()
    txt2 = [ line for line in txt if len(line) and not line.startswith("#") ]
    return txt2
    
    

def find_files(basedir, glob_pattern = "*", abort_on_match = False):
    ignored_files = [
        "*~",
        ".*",
        "*.bak",
        "*.bakup",
        "*.tar.gz",
        "*.tar.bz2",
        "*.BASE.*",
        "*.LOCAL.*",
        "*.REMOTE.*",
        "*.*.rej",
        "*.*.orig",
    ]
    retfiles = []
    
    for root, dirs, files in os.walk(basedir):
        baseroot = os.path.relpath(root,basedir)
        for pattern in ignored_files:
            delfiles = fnmatch.filter(files, pattern)
            for f in delfiles: files.remove(f)
            deldirs = fnmatch.filter(dirs, pattern)
            for f in deldirs: dirs.remove(f)
        pass_files = [ os.path.join( baseroot, filename ) for filename in fnmatch.filter(files, glob_pattern) ]
        if pass_files and abort_on_match:
            dirs[:] = [] 
        retfiles += pass_files
    return retfiles

def get_max_mtime(path, filename):
    ignored_files = [
        "*~",
        ".*",
        "*.bak",
        "*.bakup",
        "*.tar.gz",
        "*.tar.bz2",
        "*.BASE.*",
        "*.LOCAL.*",
        "*.REMOTE.*",
        "*.*.rej",
        "*.*.orig",
    ]
    
    basedir = os.path.join(path, os.path.dirname(filename))
    max_mtime = 0
    for root, dirs, files in os.walk(basedir):
        for pattern in ignored_files:
            delfiles = fnmatch.filter(files, pattern)
            for f in delfiles: files.remove(f)
            deldirs = fnmatch.filter(dirs, pattern)
            for f in deldirs: dirs.remove(f)
        for filename in files:
            filepath = os.path.join(root,filename)
            file_stat = os.stat(filepath)
            if file_stat.st_mtime > max_mtime:
                max_mtime = file_stat.st_mtime
    return max_mtime

    
    

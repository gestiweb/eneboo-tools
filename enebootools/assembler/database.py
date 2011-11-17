# encoding: UTF-8
from enebootools.assembler.config import cfg
import os.path, fnmatch

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

def update_database(iface):
    iface.info("Actualizando base de datos de módulos y funcionalidades . . . ")
    module_root = {}
    for path in cfg.module.modulefolders:
        if not os.path.exists(path):
            iface.warn("Directorio inexistente %s" % repr(path))
            continue
        modules = find_files(path,"*.mod", True)
        if not modules:
            iface.warn("Directorio no contiene módulos %s" % repr(path))
            continue
        module_root[path] = modules

    feature_root = {}
    for path in cfg.module.featurefolders:
        if not os.path.exists(path):
            iface.warn("Directorio inexistente %s" % repr(path))
            continue
        features = find_files(path,"*.feature.ini", True)
        if not features:
            iface.warn("Directorio no contiene funcionalidades %s" % repr(path))
            continue
        feature_root[path] = features
        





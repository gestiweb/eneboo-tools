# encoding: UTF-8
import hashlib
import os
import os.path


import lxml
from M2Crypto import EVP


def hash_file(hashobj, filepath):
    File = open(filepath)
    while True:
        buf = File.read(0x10000)
        if not buf:
            break
        hashobj.update(buf)
    return hashobj


def module_checksum(iface, module):
    print u"Module checksum for %s . . ." % repr(module)
    module = os.path.realpath(module)
    if not os.path.exists(module):
        raise AssertionError, "File does not exist: %s" % module
    if not module.endswith(".mod"):
        raise AssertionError, "File does not end in '.mod': %s" % module
        
    dirname = os.path.dirname(module)
    valid_ext = [
        ".xml", 
        ".qs",
        ".mtd",
        ".kut",
        ".qry",
        ".ui",
        ".ts",
        ".mod",
        ".xpm",
    ]
    
    for root, dirs, files in os.walk(dirname):
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext not in valid_ext: continue
            hashobj = hashlib.sha256()
            filepath = os.path.join(root, filename)
            hash_file(hashobj, filepath)
            print filename, hashobj.hexdigest()
            

            
            
        
        
    
    
    

# encoding: UTF-8
import hashlib
import re
import datetime
import os
import os.path
from StringIO import StringIO

from lxml import etree
from M2Crypto import EVP


def hash_file(hashobj, filepath):
    File = open(filepath)
    while True:
        buf = File.read(0x10000)
        if not buf:
            break
        hashobj.update(buf)
    return hashobj

def format_checksum_filename(modulename, serial):
    letters = list('abcdefghijklmnopqrstuvwxyz')
    strdate = datetime.date.today().isoformat()
    return '%s-%s%s.checksum' % (modulename, strdate, letters[serial])
    

def get_new_checksum_filename(iface, dirname, modulename):
    checksumfiles = [ entry for entry in os.listdir(dirname) if entry.endswith(".checksum") and entry.startswith(modulename) ]
    for serial in range(27):
        filename = format_checksum_filename(modulename, serial)
        if filename not in checksumfiles: break
    if checksumfiles:
        if filename < max(checksumfiles):
             print "WARN: Fichero de firma a generar es alfabeticamente menor a otro ya existente."
    return filename, checksumfiles
    

def module_checksum(iface, module):
    # TODO: Esta funcion no esta preparada para ejecutarse en una carpeta distinta a la del .mod;
    print u"Module checksum for %s . . ." % repr(module)
    module = os.path.realpath(module)
    if not os.path.exists(module):
        raise AssertionError, "File does not exist: %s" % module
    if not module.endswith(".mod"):
        raise AssertionError, "File does not end in '.mod': %s" % module
        
    dirname = os.path.dirname(module)
    modulefile = os.path.basename(module)
    modulename = os.path.splitext(modulefile)[0]
    
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
    checksumfile, olderfiles = get_new_checksum_filename(iface,dirname,modulename)
    checksum_format = "SHA-256:hex"
    checksum_version = "1.0"

    xmlroot = etree.Element("eneboo-checksums")
    xmlroot.set("file-scope","module:%s" % modulename)
    xmlroot.set("format",checksum_format)
    xmlroot.set("version",checksum_version)
    #print checksumfile
    file_keypairs = []
    for root, dirs, files in os.walk(dirname):
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext not in valid_ext: continue
            hashobj = hashlib.sha256()
            filepath = os.path.join(root, filename)
            hash_file(hashobj, filepath)
            file_keypairs.append( (filename, hashobj.hexdigest()) ) 
    
    for filename, digest in sorted(file_keypairs):
        xmlfile = etree.SubElement(xmlroot,"file")
        xmlfile.set("name",filename)
        xmlfile.text = digest
    
    xmlparser = etree.XMLParser(ns_clean=True, remove_blank_text=True,remove_comments=True,remove_pis=True)

    xmltext = etree.tostring(xmlroot, pretty_print=True)         
    newtree = etree.parse(StringIO(xmltext), parser = xmlparser)
    xmlc14n = etree.tostring(xmlroot, method='c14n')         
    xmlc14n_digest = hashlib.sha256()
    xmlc14n_digest.update(xmlc14n)
    xmlc14n_digest = xmlc14n_digest.hexdigest()
    for oldfile in olderfiles:
        try:
            oldtree = etree.parse(oldfile, parser = xmlparser)
        except Exception, e:
            continue
        oldxmlc14n = etree.tostring(oldtree.getroot(), method='c14n')         
        oldxmlc14n_digest = hashlib.sha256()
        oldxmlc14n_digest.update(oldxmlc14n)
        oldxmlc14n_digest = oldxmlc14n_digest.hexdigest()
        if xmlc14n_digest == oldxmlc14n_digest:
            print "INFO: El fichero de checksum %s ya era valido." % oldfile
            return oldfile
    
    
    f1 = open(checksumfile, "w")
    f1.write(xmltext)
    f1.close()
    print "Se ha generado el fichero %s" % checksumfile
    

            
            
        
        
    
    
    

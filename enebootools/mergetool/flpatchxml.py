# encoding: UTF-8
u"""
    Módulo de cálculo y aplicación de parches XML emulando flpatch.
"""
from enebootools.lib.etree.ElementTree import ElementTree, XMLParser, Element
import os.path, re

latin2_files = "mtd,kut,qry,mod".split(",")
utf8_files = "ui,ts".split(",")

def auto_detect_encoding(text, mode = None):
    global latin2_files, utf8_files
    if type(mode) == list: try_encodings = mode
    elif mode in latin2_files:
        try_encodings = ['ISO-8859-15','UTF-8']
    elif mode in utf8_files:
        try_encodings = ['UTF-8','ISO-8859-15']
    else:
        try_encodings = ['UTF-8','ISO-8859-15']
        
    try_encoding = try_encodings.pop(0)
    try:
        utxt = unicode(text, try_encoding)
        return try_encoding
    except UnicodeDecodeError:
        if try_encodings:
            return auto_detect_encoding(text, try_encodings)
        else:
            return None
            
def element_repr(self):
    MAX_CHARS = 32
    key = self.tag
    name = getattr(self, "idelem", None)
    if name: key += ".%s" % name
    if self.text.strip():
        value = repr(self.text.strip()[:MAX_CHARS])
        if len(self.text.strip()) > MAX_CHARS: value += "(...)"
        text = "<Element %s=%s>" % (key, value )
    else:
        text = "<Element %s>" % (key)
        
    return text
    
Element.__repr__ = element_repr

class FLXMLParser(object):
    def __init__(self, rootelement):
        self.root = rootelement
        self.xmltype = self.root.tag
        self.flpathlist = {}
        self.stdpathlist = {}
                
        self.analyze_tree()
        
    def get_std_path(self, path):
        pathlist = path.split("/")
        stdpathlist = []
        for part in pathlist:
            idx = part.find(":")
            if idx > -1:
                key = part[:idx]
            else:
                key = part
            stdpathlist.append(key)
        return "/".join(stdpathlist)
    
    def get_stdpath_to_id(self,path, tag = ""):
        if tag: path+="/"+tag
        stdpath = self.get_std_path(path)
        if re.search("TMD/field$",stdpath): return "name"
        if re.search("field/relation$",stdpath): return "table"
        return None
    
    def analyze_tree(self, elem = None, parent_path = "", number = None):
        if elem == None: elem = self.root
        elem.stdpath = parent_path+"/"+elem.tag
        if elem.stdpath not in self.stdpathlist:
            self.stdpathlist[elem.stdpath] = []
        
        elem.tag_number = len(self.stdpathlist[elem.stdpath])        
        elem.child_number = number
        elem.idelem = None
        if elem.child_number is None: idkey = None
        else:
            idkey = "%02X" % elem.tag_number
            path_to_id = self.get_stdpath_to_id(parent_path, elem.tag)
            if path_to_id:
                idelem = elem.find(path_to_id)
                if idelem is not None:
                    elem.idelem = idelem.text.strip()
                    idkey = elem.idelem
                else:
                    print elem.flpath, path_to_id
                
        
        format = "%s/%s:%s"
        elem.fltag = elem.tag
        if idkey:
            elem.fltag = elem.tag + ":" + idkey
            
        path = "%s/%s" % (parent_path,elem.fltag)
        
        elem.idkey = idkey
        elem.flpath = path
        elem.prev_elem = None
        elem.next_elem = None
    
        self.flpathlist[path] = elem
        self.stdpathlist[elem.stdpath].append(elem)
        

        for n,child in enumerate(elem):
            self.analyze_tree(child, path, n)
            child.parent_elem = elem
        
        prev_elem = None
        for child in elem:
            child.prev_elem = prev_elem
            prev_elem = child
            
        next_elem = None
        for child in reversed(elem):
            child.next_elem = next_elem 
            next_elem = child
            
        
        
        
    

def diff_xml(iface, base, final): 
    iface.debug(u"Procesando Diff XML $base:%s -> $final:%s" % (base, final))
    try:
        fbase = open(base, "r").read()
        ffinal = open(base, "r").read()
    except IOError, e:
        iface.error("Error al abrir el fichero base o final: " + str(e))
        return
    
    root, ext1 = os.path.splitext(base)
    encoding_base = auto_detect_encoding(fbase, ext1)
    if encoding_base is None:
        iface.error("La codificación del fichero base %s se desconoce" % base)
        return
    xmlp_base = XMLParser(encoding = encoding_base)
    xmlp_base.feed(fbase)
    tbase = xmlp_base.close()
    
    root, ext2 = os.path.splitext(final)
    encoding_final = auto_detect_encoding(fbase, ext2)
    if encoding_final is None:
        iface.error("La codificación del fichero final %s se desconoce" % base)
        return
    if ext1 != ext2:
        iface.warn("Las extensiones de $base y $final son distintas (%s != %s)." % (ext1, ext2))
    if encoding_base != encoding_final:
        iface.warn("El encoding difiere entre $base y $final (%s != %s)." % (encoding_base, encoding_final))
        
    xmlp_final = XMLParser(encoding = encoding_final)
    xmlp_final.feed(ffinal)
    tfinal = xmlp_final.close()

    flxml_base = FLXMLParser(tbase)
    flxml_final = FLXMLParser(tfinal)
    
    for elem in tbase:
        print elem
    
    print "---"

    for elem in tfinal:
        print elem



# encoding: UTF-8
u"""
    Módulo de cálculo y aplicación de parches XML emulando flpatch.
"""
from enebootools.lib.etree.ElementTree import ElementTree, XMLParser
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
    
    def analyze_tree(self, elem = None, parent_path = ""):
        if elem == None: elem = self.root
        path_to_id = self.get_stdpath_to_id(parent_path, elem.tag)
        elem.stdpath = parent_path+"/"+elem.tag
        if elem.stdpath not in self.stdpathlist:
            self.stdpathlist[elem.stdpath] = []
        pos = len(self.stdpathlist[elem.stdpath])        
        idkey = None
        idkey = "%02X" % pos
        if path_to_id:
            idelem = elem.find(path_to_id)
            if idelem is not None:
                idkey += ":" + idelem.text.strip()
        format = "%s/%s:%s"
        path = format % (parent_path,elem.tag,idkey)
        
        elem.flpath = path
        elem.prev_elem = None
        elem.next_elem = None
        self.flpathlist[path] = elem.text.strip()
        self.stdpathlist[elem.stdpath].append(idkey)
        

        for child in elem:
            self.analyze_tree(child, path)
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
    fbase = open(base, "r").read()
    root, ext = os.path.splitext(base)
    encoding_base = auto_detect_encoding(fbase, ext)
    if encoding_base is None:
        iface.error("La codificación del fichero %s se desconoce" % base)
        return
    xmlp_base = XMLParser(encoding = encoding_base)
    xmlp_base.feed(fbase)
    tbase = xmlp_base.close()
    
    iface.debug2r(tbase=tbase, roottag = tbase.tag)
    # etbase = ElementTree(tbase)
    """
    for element in tbase:
        text = element.text
        if element.tag == 'field':
            text = element.find('name').text
        text = text.strip()
        print element.tag, repr(text)
        """
    fxmlbase = FLXMLParser(tbase)
    iface.debug2r(fxmlbase.stdpathlist)
    #for fieldname in tbase.findall('field/name'):
    #    print fieldname.text



# encoding: UTF-8
u"""
    Módulo de cálculo y aplicación de parches XML emulando flpatch.
"""
from enebootools.lib.etree.ElementTree import ElementTree, XMLParser, Element
import os.path, re
from collections import defaultdict
import difflib

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
    if self.text and self.text.strip():
        value = repr(self.text.strip()[:MAX_CHARS])
        if len(self.text.strip()) > MAX_CHARS: value += "(...)"
        text = "<Element %s=%s>" % (key, value )
    else:
        text = "<Element %s>" % (key)
        
    return text
    
Element.__repr__ = element_repr

class FLXMLParser(object):
    def __init__(self, rootelement, iface):
        self.root = rootelement
        self.xmltype = self.root.tag
        self.flpathlist = {}
        self.stdpathlist = {}
        self.iface = iface
        self.setup_tree()
        self.analyze_tree()
        
    def get_tag_path(self, path):
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
    
    def elem_find(self, elem, path, attr, validator = None):
        if path == ".": listelem = [elem]
        else: listelem = elem.findall(path)
        idfound_list = []
        for idelem in listelem:
            if validator:
                try:
                    if validator(idelem) == False: continue
                except Exception,e:
                    self.iface.exception("Validating", str(e))
                    continue
            if attr == "#text": 
                idfound_list.append(idelem.text_value)
            else:
                try: idfound_list.append(idelem.attrib[attr])
                except KeyError: pass
        if len(idfound_list) == 0: return None
        if len(idfound_list) == 1: return idfound_list[0]
        iface.warn("Se encontró más de un ID candidato para %s: %s" % (elem.stdpath, repr(idfound_list)))
            
        return idfound_list[0]
    def elem_get_uiproperty(self, elem, property_name):
        def _is_this_property(e):
            if e.parent_elem.attrib["name"] == property_name: 
                return True
            else:
                return False
        elem = self.elem_find(elem, "property/cstring" ,"#text", 
                            validator = _is_this_property )
        if elem is None:
            elem = self.elem_find(elem, "property" ,"#text", 
                                validator = _is_this_property )
        
        return elem
        
    def get_elem_id(self,elem, parent_path):
        path = elem.tagpath
        if self.xmltype == "TMD":
            if re.search("/field$",path): return self.elem_find(elem, "name", "#text")
            if re.search("/field/relation$",path): return self.elem_find(elem, "table", "#text")
        elif self.xmltype == "UI":
            if re.search("/tabstops/tabstop$",path): return self.elem_find(elem, ".", "#text")
            if re.search("/property$",path): return self.elem_find(elem, ".", "name")
            if elem.find("property") is not None:
                value = self.elem_get_uiproperty(elem, "name")
                if value == "unnamed" or value == "": return None
                else: return value
        else:
            self.iface.debug("root desconocido: " + self.xmltype)
        
        return None
    
    def setup_tree(self, elem = None, parent_path = "", number = None):
        if elem == None: elem = self.root
        elem.tagpath = parent_path+"/"+elem.tag
        elem.child_number = number
        elem.idelem = None
        elem.prev_elem = None
        elem.next_elem = None
        elem.fltag = elem.tag
        elem.idelem = None
        elem.idpath = ""
        elem.text_value = ""
        elem.parent_elem = None
        if elem.text: elem.text_value = elem.text.strip()
        
        for n,child in enumerate(elem):
            self.setup_tree(child, elem.tagpath, n)
            child.parent_elem = elem
        
        prev_elem = None
        for child in elem:
            child.prev_elem = prev_elem
            prev_elem = child
            
        next_elem = None
        for child in reversed(elem):
            child.next_elem = next_elem 
            next_elem = child
    
    
    def analyze_tree(self, elem = None, parent_path = ""):
        if elem == None: elem = self.root
        elem.stdpath = parent_path+"/"+elem.tag
        if elem.stdpath not in self.stdpathlist:
            self.stdpathlist[elem.stdpath] = []
        
        elem.tag_number = len(self.stdpathlist[elem.stdpath])        

        idkey = "%02X" % elem.tag_number
        elem.idelem = self.get_elem_id(elem, parent_path)
        if elem.idelem: idkey = elem.idelem
        if parent_path == "": idkey = None
        
        if idkey: elem.fltag = elem.tag + ":" + idkey
            
        path = "%s/%s" % (parent_path,elem.fltag)
        
        elem.idkey = idkey
        elem.flpath = path
        if elem.parent_elem is not None:
            elem.idpath = elem.parent_elem.idpath
        if elem.idelem:
            elem.idpath += "/" + elem.idelem
    
        self.flpathlist[path] = elem
        self.stdpathlist[elem.stdpath].append(elem)

        for child in elem:
            self.analyze_tree(child, path)
            
        
        
        
    

def diff_xml(iface, base, final): 
    iface.debug(u"Procesando Diff XML $base:%s -> $final:%s" % (base, final))
    try:
        fbase = open(base, "r").read()
        ffinal = open(final, "r").read()
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
    encoding_final = auto_detect_encoding(ffinal, ext2)
    if encoding_final is None:
        iface.error("La codificación del fichero final %s se desconoce" % final)
        return
    if ext1 != ext2:
        iface.warn("Las extensiones de $base y $final son distintas (%s != %s)." % (ext1, ext2))
    if encoding_base != encoding_final:
        iface.warn("El encoding difiere entre $base y $final (%s != %s)." % (encoding_base, encoding_final))
        
    xmlp_final = XMLParser(encoding = encoding_final)
    xmlp_final.feed(ffinal)
    tfinal = xmlp_final.close()

    if tbase.tag != tfinal.tag:
        iface.warn("Los documentos XML son de estructura diferente (root tag: %s != %s)" % (tbase.tag,tfinal.tag))
    else:
        iface.debug2r(xml_base_root_tag=tbase)
    
    
    flxml_base = FLXMLParser(tbase, iface)
    flxml_final = FLXMLParser(tfinal, iface)
    
    """ TODO: Falta intentar manejar los movimientos de ID en la jerarquía. 
        Por ejemplo, convertir un vbox en un grid. Parecerá que se borra <vbox>
        con sus widgets y que se crea todo nuevo. Hay que intentar que rescate
        los controles antiguos que coincidan por ID.
        Pero para realizar esto, el patch deberá contener una referencia al ID,
        no su contenido XML, y luego gestionar el patch para ese ID por otro lado. 
        Hay que analizar si ensambla cubre esto.
        
        Otra acción que no sabemos si cubrir es la de cambio de tagName o idElem.
        Un simple cambio de hbox por vbox podría ser detectada como un cambio en
        el tagname.
    """
    
    recursive_compare(iface,tbase,tfinal)
    

def compare_subelems(iface, base_elem, final_elem):
    base = [ "%s:%s" % (subelem.tag,subelem.idelem) for subelem in base_elem ]
    final = [ "%s:%s" % (subelem.tag,subelem.idelem) for subelem in final_elem ]
    s = difflib.SequenceMatcher(None, base, final)
    opcodes = s.get_opcodes()
    insert_opcodes = [ (b1, b2) 
                        for action, a1, a2 , b1, b2 in opcodes
                            if action == "insert" ]
    delete_opcodes = [ (a1, a2) 
                        for action, a1, a2 , b1, b2 in opcodes
                            if action == "delete" ]
                            
    accept_move_ratio = 0.7 # 70% igual que original para aceptar move.
    
    for a1, a2 in delete_opcodes:
        # Para cada borrado, intentar encontrar un buen insert equivalente.
        s_list = []
        for b1, b2 in insert_opcodes:
            s_list.append((difflib.SequenceMatcher(None, base[a1:a2], final[b1:b2]),(b1,b2)))
        
        # Descartemos rápidamente los que estarán por debajo de move_ratio
        s_list = [ (s1,b12) for s1,b12 in s_list if s1.quick_ratio() > accept_move_ratio]
        if not s_list: continue
        # Calculemos todos los ratios:
        s_ratios = [ s1[0].ratio() for s1 in s_list ]
        max_ratio = max(s_ratios)
        if max_ratio < accept_move_ratio: continue
        idx = s_ratios.index(max_ratio)
        s1 = s_list[idx][0]
        b1,b2 = s_list[idx][1]
        
        new_opcodes = s1.get_opcodes()
        # Se acepta el move, procedemos a borrar los movimientos originales:
        insert_opcodes.remove( (b1,b2) ) # evitar que vuelva a salir.
        for action_, a1_, a2_, b1_, b2_ in opcodes[:]:
            delete = False
            if (action_,b1_,b2_) == ("insert",b1,b2): delete = True
            if (action_,a1_,a2_) == ("delete",a1,a2): delete = True
            if delete:
                opcodes.remove( (action_, a1_, a2_, b1_, b2_) )
                
        # Procedemos a insertar nuestros movimientos generados:    
        for action_, a1_, a2_, b1_, b2_ in new_opcodes:
            if action_ == "equal": action_ = "move"
            a1_ += a1
            a2_ += a1
            b1_ += b1
            b2_ += b1
            # Ver la posición donde agregar esto...
            for n, x in enumerate(opcodes):
                if action == "delete": # mirar por la izq (A/Base)
                    if x[1] > a1_: break
                else: # mirar por la der (B/Final)
                    if x[3] > b1_: break
            opcodes.insert(n, (action_, a1_, a2_, b1_, b2_) )
            
        
            
        
    
    ratio = s.ratio()
    return ratio, opcodes

def get_elem_contents(iface, elem):
    if elem.text: text = elem.text
    else: text = ""
    textvalue = text.strip()
    textnfixes = text.replace(textvalue, "*") # Nos deja algo como '\n\t*\n\t'
    textdepth = "" # -> para indicar el string de prefijo común por linea.
    items = {}
    items["#t"] = textvalue
    items["#textnfixes"] = textnfixes
    items["#textdepth"] = textdepth
    for k,v in elem.attrib.items():
        items["@%s" % k] = v
    
    return items
    


def compare_elems(iface, base_elem, final_elem):
    base = get_elem_contents(iface, base_elem)
    final = get_elem_contents(iface, final_elem)
    if base == final: return True
    for k, v in base.items()[:]:
        if final[k] == v: 
            del final[k]
            del base[k]
    iface.debug2r(_=shpath(base_elem), base = base, final = final)
    return None

def _compare_subelems(iface, base_elem, final_elem):
    base = [ "%s:%s" % (subelem.tag,subelem.idelem) for subelem in base_elem ]
    final = [ "%s:%s" % (subelem.tag,subelem.idelem) for subelem in final_elem ]
    equal = bool( base == final )
    d = defaultdict(int)
    for x in final: d[x] += 1    
    for x in base: d[x] -= 1    
    d = dict(d)
    for k,v in d.items():
        if v == 0: del d[k]
    
    if not equal and d == {}:
        iface.debug2r(path=base_elem.flpath)
        iface.debug2r(base=base)
        iface.debug2r(final=final)
    
    # Debería devolver un zip() de base_elem y final_elem alineados.
    # None - valor -> agrega
    # valor - None -> borra
    # ordenado según base o final, es indiferente. Preferiblemente que siga un orden.
    
    
    return equal, d
        

def shpath(elem):
    path = elem.flpath
    path = path.replace(":00","")
    size = 64
    if len(path) > size:
        path = path[-size:]
        idx = path.find("/")
        if idx >-1:
            path = path[idx+1:]
    return path
            

def recursive_compare(iface, base_elem, final_elem, depth = 0):
    compare_elems(iface, base_elem, final_elem)
    
    ratio, opcodes = compare_subelems(iface, base_elem, final_elem)
    #if base_elem.idelem:
    #    iface.debug2("%s {%s} => %s" % (base_elem.flpath, ", ".join([ "%s=%s" % (k,repr(v)) for k,v in sorted(base_elem.items())]) ,repr(base_elem.text_value)))
    # if ratio < 1.0: iface.debug2(">> %s .. %.1f%%" % (base_elem.flpath, ratio*100.0))
            
    for action, a1, a2 , b1, b2 in opcodes:
        if action == "move": 
            iface.debug2r(_=shpath(base_elem), move=final_elem[b1:b2], zdelta = b1 - a1)
        if action == "insert" :
            iface.debug2r(_=shpath(base_elem), insert=final_elem[b1:b2], zpos = b1)
        if action == "delete":
            iface.debug2r(_=shpath(base_elem), delete=base_elem[a1:a2], zpos = a1)

        if action == "equal" or action == "move":
            for base_subelem, final_subelem in zip(base_elem[a1:a2], final_elem[b1:b2]):
                recursive_compare(iface, base_subelem, final_subelem, depth + 1)
                

    # if ratio < 1.0: iface.debug2("<< %s .. %.1f%%" % (base_elem.flpath, ratio*100.0))

#encoding: UTF-8
from lxml import etree
import os.path
import difflib

def filepath(): return os.path.abspath(os.path.dirname(__file__))
def filedir(x): return os.path.abspath(os.path.join(filepath(),x))

config_tree = etree.parse(filedir("config/index.xml"))    
config_tree.xinclude()

def _xf(x): #xml-format
    if type(x) is list: return "\n---\n\n".join([ _xf(x1) for x1 in x ])
    return unicode(etree.tostring(x,pretty_print=True, encoding = "UTF8"), "UTF8")

class XMLFormatParser(object):
    def __init__(self, iface, format, file1):
        self.iface = iface
        self.format = format
        self.encoding = self.format.xpath("@encoding")[0]
        self.parser = etree.XMLParser(
                        ns_clean=True,
                        encoding=self.encoding,
                        recover=False, # .. recover funciona y parsea cuasi cualquier cosa.
                        remove_blank_text=True,
                        )
        self.tree = etree.parse(file1, self.parser)
        self.root = self.tree.getroot()
        self.context_items = [] # Lista de los elementos insertados
        
    def output(self):
        return _xf(self.tree.getroot())
        
    def clean(self):
        for item in self.context_items:
            parent = item.getparent()
            parent.remove(item)
    
    def validate(self):
        for elem in self.format.xpath("assert/*"):
            result = self.evaluate(elem)
            if type(result) is object: result = bool(result is None)
            if not result: 
                self.iface.debug("Fallo al validar la regla %s" % etree.tostring(elem))
                return False
            else:
                self.iface.debug2("OK Regla %s:%s" % (elem.tag,elem.text.strip()))
        return True
        
    def evaluate(self, elem, from_elem = None):
        if elem is None: return None
        text = elem.text.strip()
        if from_elem is None: from_elem = self.tree
        
        def sxpath(text,**kwargs):
            try:
                xlist = from_elem.xpath(text,**kwargs)
            except Exception, e:
                self.iface.exception("EvaluateError","Error evaluando  %s  %s" % (text, repr(kwargs)))
                return None
            if isinstance(xlist, list):
                if len(xlist): return xlist[0]
                else: return None
            else: return xlist
            
        try:
            if elem.tag == "xpath": 
                kwvars = {}
                for elem in elem.xpath("*[@name]"):
                    kwvars[elem.get("name")] = self.evaluate(elem,from_elem)
                return sxpath(text,**kwvars)
            elif elem.tag == "format": 
                format_string = elem.get("text")
                args = []
                kwargs = {}
                for elem in elem.xpath("*"):
                    name = elem.get("name")
                    value = self.evaluate(elem,from_elem)
                    if name: kwargs[name] = value
                    else: args.append(value)
                return format_string.format(*args,**kwargs)
            elif elem.tag == "value": return text
            elif elem.tag == "if-then-else": 
                kwvars = {}
                for elem in elem.xpath("*[@name]"):
                    kwvars[elem.get("name")] = self.evaluate(elem,from_elem)
                if kwvars['if']:
                    return kwvars['then']
                else:
                    return kwvars['else']
            else: self.iface.warn("Descartando tag de evaluación desconocido: %s:%s" % (elem.tag,text))
        except Exception, e:
            self.iface.exception("EvaluateError","Error evaluando  %s:%s" % (elem.tag,text))
            return None
            
    def load_entity(self, entity_name, context_info, search_xpath):
        self.iface.debug2("Aplicando entidad %s a los elementos %s" % (entity_name,search_xpath))
        for element in self.tree.xpath(search_xpath):
            if element.xpath("context-information"): continue
            if element.xpath("ancestor-or-self::context-information"): continue
            ctx = etree.SubElement(element, "context-information", entity = entity_name)
            self.context_items.append(ctx)
            ctx_pending_names = set([])
            ctxdict = {}
            for ctxopt in context_info:
                name = ctxopt.get("name")
                ctx_pending_names.add(name)
                if name:
                    if name not in ctxdict:
                        value = self.evaluate(ctxopt, element)
                        if value is not None:
                            ctxdict[name] = value
                            ctx.set(name,unicode(value))
                        
            for name, value in ctxdict.items():
                ctx_pending_names.remove(name)
                
            for name in ctx_pending_names:
                self.iface.debug("Regla de contexto sin valor: %s" % name)
                
        return True
        
    def load_entities(self):
        default_ctx = self.format.xpath("entities/default/context-information/*")
        for entity in self.format.xpath("entities/entity"):
            entity_name = entity.get("name")
            context_info = entity.xpath("context-information/*")
            self.iface.debug2("Cargando entidad %s" % entity_name)
            for search_xpath in entity.xpath("search/xpath"):
                ret = self.load_entity(entity_name, context_info + default_ctx, search_xpath.text.strip())
                if not ret: return False
                
        return True
    
        
def diff_lxml(iface, base, final):
    iface.debug(u"Diff LXML $base:%s $final:%s" % (base,final))
    root, ext1 = os.path.splitext(base)
    root, ext2 = os.path.splitext(final)
    if ext1 != ext2:
        iface.warn("Comparando ficheros de extensiones diferentes.")
    
    formats = config_tree.xpath("/etc/formats/format[filetype/text()=$ext]/@name", ext=ext1)
    if len(formats) == 0:
        iface.error("No tenemos ningún plugin que reconozca esta extensión")
        return
    if len(formats) > 1:
        iface.warn("Había más de un formato y hemos probado el primero %s" % (repr(formats)))
    format_name = formats[0]        
    format = config_tree.xpath("/etc/formats/format[@name=$format_name]", format_name=format_name)[0]
    
    try:
        file_base = open(base, "r")
        file_final = open(final, "r")
    except IOError, e:
        iface.error("Error al abrir el fichero base o final: " + str(e))
        return
    
    xbase = XMLFormatParser(iface, format, file_base)
    
    if not xbase.validate():
        iface.error(u"El fichero base no es válido para el formato %s" % (format_name))
        return
    if not xbase.load_entities():
        iface.error(u"Error al cargar entidades del formato %s (fichero base)" % (format_name))
        return

    xfinal = XMLFormatParser(iface, format, file_final)

    if not xfinal.validate():
        iface.error(u"El fichero final no es válido para el formato %s" % (format_name))
        return
    if not xfinal.load_entities():
        iface.error(u"Error al cargar entidades del formato %s (fichero final)" % (format_name))
        return
    
    #xbase.clean()
    #iface.output.write(xbase.output().encode(xbase.encoding))
    recursive_compare(iface, xbase.root, xfinal.root)
    

def get_elem_contents(iface, elem):
    if elem.text: text = elem.text
    else: text = ""
    textvalue = text.strip()
    if textvalue:
        textnfixes = text.replace(textvalue, "*") # Nos deja algo como '\n\t*\n\t'
    else:
        textnfixes = text
    textdepth = "" # -> para indicar el string de prefijo común por linea.
    items = {}
    items["#t"] = textvalue
    #items["#textnfixes"] = textnfixes
    #items["#textdepth"] = textdepth
    for k,v in elem.attrib.items():
        items["@%s" % k] = v
    return items

def compare_elems(iface, base_elem, final_elem):
    base = get_elem_contents(iface, base_elem)
    final = get_elem_contents(iface, final_elem)
    if base == final: return True
    for k, v in base.items()[:]:
        if k not in final: final[k] = None
        if final.get(k, None) == v: 
            del final[k]
            del base[k]
    iface.debug2r(_=shpath(base_elem), base = base, final = final)
    return None                    

def shpath(elem):
    if elem is None: return ""
    eclass = elem.xpath("context-information/@class")
    name = elem.xpath("context-information/@name")
    scope = elem.xpath("context-information/@scope")
    if eclass: eclass = eclass[0]
    else: eclass = elem.tag
    if scope: scope = scope[0]
    else: scope = "none"
    if name: name = name[0]
    else: name = None
    fullname = [eclass]
    if name: fullname.append(name)
    fullname = ":".join(fullname)
    if name and scope == "global": return fullname
    
    return shpath(elem.getparent()) + "/" + fullname

    
def recursive_compare(iface, base_elem, final_elem, depth = 0):
    compare_elems(iface, base_elem, final_elem)
    if len(base_elem.getchildren()) == 0 and len(base_elem.getchildren()) == 0: return
    
    ratio, opcodes = compare_subelems(iface, base_elem, final_elem)

    for action, a1, a2 , b1, b2 in opcodes:
        if action == "equal": 
            if a2-a1-b2+b1 != 0:
                iface.debug2r(_=shpath(base_elem), equal=final_elem[b1:b2], zdelta = b1 - a1, zsize = a2-a1, zdisc = a2-a1-b2+b1  )
        elif action == "move": 
            iface.debug2r(_=shpath(base_elem), move=final_elem[b1:b2], zdelta = b1 - a1, zsize = a2-a1, zdisc = a2-a1-b2+b1  )
        elif action == "insert" :
            iface.debug2r(_=shpath(base_elem), insert=final_elem[b1:b2], zpos = b1)
        elif action == "delete":
            iface.debug2r(_=shpath(base_elem), delete=base_elem[a1:a2], zpos = a1)
        else:
            iface.error("Acción %s desconocida" % action)
            raise ValueError
        if action == "equal" or action == "move":
            for base_subelem, final_subelem in zip(base_elem[a1:a2], final_elem[b1:b2]):
                recursive_compare(iface, base_subelem, final_subelem, depth + 1)
    

def fix_replace_opcode(opcodes):
    """
        Convierte un replace en un delete+insert.
    """
    new_opcodes = []
    for action, a1, a2 , b1, b2 in opcodes:
        if action == "replace":
            new_opcodes.append( ("delete", a1, a2 , b1, b1) )        
            new_opcodes.append( ("insert", a2, a2 , b1, b2) )        
            continue
        new_opcodes.append( (action, a1, a2 , b1, b2) )
    return new_opcodes

def get_ctxinfo(iface, elem):
    ctx = elem.xpath("context-information")
    if len(ctx) == 0: ctx = elem.tag
    else: ctx = ";".join(["%s=%s" % (k,v) for k,v in sorted(dict(ctx[0].attrib).items())])
    return ctx

def compare_subelems(iface, base_elem, final_elem):
    base = [ get_ctxinfo(iface, subelem) for subelem in base_elem if subelem.tag != "context-information"]
    final = [ get_ctxinfo(iface, subelem) for subelem in final_elem if subelem.tag != "context-information"]
    s = difflib.SequenceMatcher(None, base, final)
    opcodes = fix_replace_opcode(s.get_opcodes())    
    ratio = s.ratio()
    return ratio, opcodes

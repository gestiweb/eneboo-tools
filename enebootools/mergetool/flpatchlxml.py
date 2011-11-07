#encoding: UTF-8
from lxml import etree
import os.path

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
        
    def output(self):
        return _xf(self.tree.getroot())
        
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
                            ctx_elem = etree.SubElement(ctx, name, value=unicode(value))
                        
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
        file_final = open(base, "r")
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
    
    iface.output.write(xbase.output().encode(xbase.encoding))
                    
    
    
    
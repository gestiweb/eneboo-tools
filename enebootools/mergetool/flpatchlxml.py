#encoding: UTF-8
from lxml import etree
from copy import deepcopy
import os.path
import difflib

def filepath(): return os.path.abspath(os.path.dirname(__file__))
def filedir(x): return os.path.abspath(os.path.join(filepath(),x))

config_tree = etree.parse(filedir("etc/index.xml"))    
config_tree.xinclude()

def _xf(x, cstring = False, **kwargs): #xml-format
    if type(x) is list: return "\n---\n\n".join([ _xf(x1) for x1 in x ])
    if 'encoding' not in kwargs: 
        kwargs['encoding'] = "UTF8"
    if 'pretty_print' not in kwargs: 
        kwargs['pretty_print'] = True
        
    value = etree.tostring(x, **kwargs)
    if cstring:
        return value
    else:
        return unicode(value , kwargs['encoding'])

class XMLFormatParser(object):
    def __init__(self, iface, format, style, file1, rbt = True):
        self.iface = iface
        self.format = format
        self.style = style
        self.encoding = self.format.xpath("@encoding")[0]
        self.parser = etree.XMLParser(
                        ns_clean=True,
                        encoding=self.encoding,
                        recover=False, # .. recover funciona y parsea cuasi cualquier cosa.
                        remove_blank_text=rbt,
                        )
        file1.seek(0)
        self.tree = etree.parse(file1, self.parser)
        self.root = self.tree.getroot()
        self.context_items = [] # Lista de los elementos insertados
        self.namespaces = {
            'xsl' : "http://www.w3.org/1999/XSL/Transform", 
            'xupdate' : "http://www.xmldb.org/xupdate",
            'ctx' : "context-information",
        }
        
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
        if elem.text: text = elem.text.strip()
        else: text = ""
        if from_elem is None: from_elem = self.tree
        elem_patch_style = elem.get("patch-style")
        if elem_patch_style and self.style.attrib['name'] not in elem_patch_style.split(" "):
            return None
        elem_except_style = elem.get("except-style")
        if elem_except_style and self.style.attrib['name'] in elem_except_style.split(" "):
            return None
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
            if elem.tag == "empty": return ""
            elif elem.tag == "xpath": 
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
            elif elem.tag == "implode": 
                join_string = elem.get("join")
                args = []
                for elem in elem.xpath("*"):
                    value = self.evaluate(elem,from_elem)
                    if value is not None and value != "": args.append(value)
                return join_string.join(args)
            elif elem.tag == "value": return text
            elif elem.tag == "if-then-else": 
                kwvars = {}
                for elem in elem.xpath("*[@name]"):
                    kwvars[elem.get("name")] = self.evaluate(elem,from_elem)
                if kwvars['if']:
                    return kwvars.get('then')
                else:
                    return kwvars.get('else')
            else: self.iface.warn("Descartando tag de evaluación desconocido: %s:%s" % (elem.tag,text))
        except Exception, e:
            self.iface.exception("EvaluateError","Error evaluando  %s:%s" % (elem.tag,text))
            return None

    def load_default_entity(self, elem):
        tree = elem.getroottree()
        search_xpath = tree.getpath(elem) + "/../*"
        entity_name = "default"
        default_ctx = self.format.xpath("entities/default/context-information/*")
        self.load_entity(entity_name, default_ctx, search_xpath, self.context_items)
    
    def load_entity(self, entity_name, context_info, search_xpath, context_items = []):
        self.iface.debug2("Aplicando entidad %s a los elementos %s" % (entity_name,search_xpath))
        for element in self.tree.xpath(search_xpath):
            if element.xpath("context-information"): continue
            if element.xpath("ancestor-or-self::context-information"): continue
            ctx = etree.SubElement(element, "context-information", entity = entity_name)
            context_items.append(ctx)
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
                ret = self.load_entity(entity_name, context_info + default_ctx, search_xpath.text.strip(), self.context_items)
                if not ret: return False
                
        return True
    
    def sname(self, elem, key, default = None):
        if len(elem.xpath("context-information")) == 0:
            self.load_default_entity(elem)
            
        for entity in self.style.xpath("entities/*[@name=$key]",key = key):
            val = self.evaluate(entity,from_elem=elem)
            if val is not None: return val
        return default
    
    def clean_ctxid(self):
            
        for element in self.root.xpath("//delete-me-when-cleaning"):
            parent = element.getparent()
            parent.remove(element)
            
        for element in self.root.xpath("//*[@ctx-id]"):
            del element.attrib["ctx-id"]

        for element in self.root.xpath("//*[not(text()) and ./*]"):
            parent_level = None
            parent = element.getparent()
            if parent is not None: parent_level = parent.text
            if parent_level is None: 
                parent_level = ""
                increment = "    "
            else:
                grandparent_level = None
                grandparent = parent.getparent()
                if grandparent is not None: grandparent_level = grandparent.text
            
                if grandparent_level : increment = parent_level.replace(grandparent_level,"")
                else: increment = "    "
            
            child_level = parent_level + increment            
            
            self.iface.debug2("Reindentando: %s" % self.tree.getpath(element))
            element.text = child_level
            for child in element[:-1]: child.tail = child_level
            element[-1].tail = parent_level
            
            
            

    
    def apply_one_id(self, elem):
        idname = elem.get("ctx-id")
        if idname: return
        idname = self.sname(elem, "id", elem.tag)
        elem.set("ctx-id",idname)
            
    def add_context_id(self, root = None):
        if root is None: 
            root = self.root
            
        self.apply_one_id(root)
            
        for element in root:
            if element.tag == "context-information": continue
            self.add_context_id(element)

# ^ ^ ^ ^ ^ ^     / class XMLFormatParser



class XMLDiffer(object):
    def __init__(self, iface, format, style, file_base, file_final = None, file_patch = None):
        self.iface = iface
        self.namespaces = {
            'xsl' : "http://www.w3.org/1999/XSL/Transform", 
            'xupdate' : "http://www.xmldb.org/xupdate",
        }
        self.format = format
        self.style = style
        
        if file_patch: rbt = False # Remove Blank Text 
        else: rbt = True
        self.xbase = XMLFormatParser(self.iface, self.format, self.style, file_base, rbt)
    
        if not self.xbase.validate():
            self.iface.error(u"El fichero base no es válido para el formato %s" % (format_name))
            return
        if not self.xbase.load_entities():
            self.iface.error(u"Error al cargar entidades del formato %s (fichero base)" % (format_name))
            return
            
        self.xfinal = XMLFormatParser(self.iface, self.format, self.style, file_final, rbt)

        if not self.xfinal.validate():
            self.iface.error(u"El fichero final no es válido para el formato %s" % (format_name))
            return
        if not self.xfinal.load_entities():
            self.iface.error(u"Error al cargar entidades del formato %s (fichero final)" % (format_name))
            return
        if file_patch:
            parser = etree.XMLParser(
                            ns_clean=True,
                            remove_blank_text=True,
                            recover=True,
                            )
            self.patch_tree = etree.parse(file_patch, parser)
            self.patch = self.patch_tree.getroot()

        else:            
            self.patch = None
            self.patch_tree = None
        
    def patch_output(self):
        if self.patch is not None: 
            doc = self.apply_pre_save_patch(self.patch)
            if isinstance(doc, etree._Element):
                return _xf(doc,xml_declaration=True,cstring=True)
            else:
                return str(doc)
            
        else: return ""
        
    def final_output(self):
        if self.xfinal.root is not None: 
            doc = self.apply_pre_save_final(self.xfinal.root)
            doctype = unicode(self.xfinal.tree.docinfo.doctype).encode(self.xfinal.encoding)
            if isinstance(doc, etree._Element):
                return doctype + _xf(doc,xml_declaration=False,cstring=True, encoding=self.xfinal.encoding)
            else:
                return doctype + str(doc)
        else: 
            return ""
        
    def compare(self):
        self.patch = etree.Element("xml-patch")
        self.patch.set("generator", "eneboo")
        self.patch.set("version", "0.01")
        self.patch.set("format", self.format.get("name")) 
        self.patch.set("style",self.style.get("name"))
        self.patch_tree = self.patch.getroottree()
        
        self.recursive_compare(self.xbase.root, self.xfinal.root)
        
        return self.patch
    
    def sname(self, elem, key, default = None):
        if len(elem.xpath("context-information")) == 0:
            self.xbase.load_default_entity(elem)
            self.xfinal.load_default_entity(elem)
            
        for entity in self.style.xpath("entities/*[@name=$key]",key = key):
            val = self.xbase.evaluate(entity,from_elem=elem)
            if val is not None: return val
        return default
    
    def _sname(self, elem):
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
        return scope, name, fullname
        
    def shpath(self, elem):
        if elem is None: raise AssertionError
        fullname = self.sname(elem, key="id")
        is_root = self.sname(elem, key="is-root")
        if not fullname:
            self.iface.debug("Elemento %s no recibió nombre" % elem.getroottree().getpath(elem))
            fullname = elem.tag 
        if not fullname:
            raise AssertionError
        if is_root: return fullname
        parent = elem.getparent()
        if parent is not None:
            return self.shpath(parent) + "/" + fullname
        else:
            return "/" + fullname
    
    def get_elem_contents(self, elem):
        if elem.text: text = elem.text
        else: text = ""
        textvalue = text.strip()
        if textvalue:
            textnfixes = text.replace(textvalue, "*") # Nos deja algo como '\n\t*\n\t'
        else:
            textnfixes = text
        textdepth = "" # -> para indicar el string de prefijo común por linea.
        items = {}
        items["#text"] = textvalue
        #items["#textnfixes"] = textnfixes
        #items["#textdepth"] = textdepth
        for k,v in elem.attrib.items():
            items["@%s" % k] = v
        return items
             
    def create_diff(self, tagname, select, **kwargs):
        select_path = self.shpath(select)
        patchelem = etree.SubElement(self.patch, tagname, select=select_path, **kwargs)
        return patchelem 
      
    def compare_elems(self, base_elem, final_elem):
        base = self.get_elem_contents(base_elem)
        final = self.get_elem_contents(final_elem)
        if base == final: return True
        for k, v in base.items()[:]:
            if k not in final: final[k] = None
            if final.get(k, None) == v: 
                del final[k]
                del base[k]
                
        patchelem = self.create_diff("patch-node",select=base_elem)
        for k, v in sorted(base.items()):
            tag = "unknown"
            kwargs = {}
            if k[0] == "#": tag = "text"
            if k[0] == "@": 
                tag = "attribute"
                kwargs["name"] = k[1:]
            op = "update"
            if v is None: op = "create"
            if final[k] is None: op = "delete"
            tag = op + "-" + tag
            subelem = etree.SubElement(patchelem, tag, **kwargs)
            if v: subelem.set("old", v)
            if final[k]: subelem.set("new",final[k])
        
        # self.iface.debug2r(_=self.shpath(base_elem), base = base, final = final)
        return None     
        
    def get_ctxinfo(self, elem):
        ctx = elem.xpath("context-information")
        if len(ctx) == 0: ctx = elem.tag
        else: ctx = ";".join(["%s=%s" % (k,v) for k,v in sorted(dict(ctx[0].attrib).items())])
        return ctx

    def compare_subelems(self, base_elem, final_elem):
        base = [ self.get_ctxinfo(subelem) for subelem in base_elem if subelem.tag != "context-information"]
        final = [ self.get_ctxinfo(subelem) for subelem in final_elem if subelem.tag != "context-information"]
        s = difflib.SequenceMatcher(None, base, final)
        opcodes = fix_replace_opcode(s.get_opcodes())    
        ratio = s.ratio()
        return ratio, opcodes
    
    def add_subnode(self, patchelem, subelem, action):
        if patchelem is None: return
        mode = "full"
        if action == "noop": mode = "short"
        
        fullname = self.sname(subelem, key="id", default=subelem.tag)
        updelem = etree.SubElement(patchelem, "subnode", action=action, select=fullname)
        if mode == "full":
            updelem.append( deepcopy(subelem) )
            for elem in updelem.xpath(".//context-information[@entity]"):
                parent = elem.getparent()
                parent.remove(elem)
    
    def recursive_compare(self, base_elem, final_elem, depth = 0):
        self.compare_elems(base_elem, final_elem)
        if len(base_elem.getchildren()) == 0 and len(base_elem.getchildren()) == 0: return

        ratio, opcodes = self.compare_subelems(base_elem, final_elem)
        if len(opcodes) == 0:
            #self.iface.debug("Opcodes vacío. ?")
            return
        if len(opcodes) > 1 or opcodes[0][0] != "equal":
            patchelem = self.create_diff("patch-node",select=base_elem)
        else:
            patchelem = None
        for action, a1, a2 , b1, b2 in opcodes:
            if action == "equal": 
                if a2-a1-b2+b1 != 0:
                    self.iface.debug2r(_=self.shpath(base_elem), equal=final_elem[b1:b2], zdelta = b1 - a1, zsize = a2-a1, zdisc = a2-a1-b2+b1  )
            elif action == "move": 
                self.iface.debug2r(_=self.shpath(base_elem), move=final_elem[b1:b2], zdelta = b1 - a1, zsize = a2-a1, zdisc = a2-a1-b2+b1  )
            elif action == "insert" :
                self.iface.debug2r(_=self.shpath(base_elem), insert=final_elem[b1:b2], zpos = b1)
                for final_subelem in final_elem[b1:b2]:
                    self.add_subnode(patchelem, final_subelem, "insert")
                        
                
            elif action == "delete":
                self.iface.debug2r(_=self.shpath(base_elem), delete=base_elem[a1:a2], zpos = a1)
                for base_subelem in base_elem[a1:a2]:
                    self.add_subnode(patchelem, base_subelem, "delete")
            else:
                self.iface.error("Acción %s desconocida" % action)
                raise ValueError
            if action == "equal" or action == "move":
                for base_subelem, final_subelem in zip(base_elem[a1:a2], final_elem[b1:b2]):
                    self.add_subnode(patchelem, base_subelem, "noop")
                    self.recursive_compare(base_subelem, final_subelem, depth + 1)
            if patchelem is not None:
                # Agregar las modificaciones del padre, después de modificar los hijos.
                parent = patchelem.getparent()
                parent.remove(patchelem)
                parent.append(patchelem)
                
                    
    def apply_pre_save_patch(self, doc):
        for elem in self.style.xpath("pre-save-patch/*"):
            if elem.tag == "{http://www.w3.org/1999/XSL/Transform}stylesheet":
                doc = self.apply_xsl(elem, doc)
        return doc
    
    def apply_pre_save_final(self, doc):
        
        for elem in self.style.xpath("pre-save-final/*"):
            if elem.tag == "{http://www.w3.org/1999/XSL/Transform}stylesheet":
                doc = self.apply_xsl(elem, doc)
        return doc
    
    def apply_xsl(self, xsl_elem, doc):
        xsl_tree = etree.ElementTree( deepcopy(xsl_elem) )
        xsl_root = xsl_tree.getroot()
        xsl_output = xsl_root.xpath("xsl:output",  namespaces=self.namespaces)[0]
        if "encoding" not in xsl_output.attrib:
            xsl_output.set("encoding",self.xbase.encoding)
            
        transform = etree.XSLT(xsl_root)
        newdoc = transform(doc)
        return newdoc
    
    def select_patch_applyfn(self):
    
        known_tags = {
            '{http://www.xmldb.org/xupdate}modifications' : self.patch_xupdate,
            'modifications' : self.patch_xupdate,
        }
        if self.patch.tag not in known_tags:
            self.iface.error("Tipo de parche desconocido: " + repr(self.patch.tag))
            return None
        else:
            return known_tags[self.patch.tag]
    

    def apply_patch(self):
        # Aplica el parche sobre "final", teniendo en cuenta que se ha 
        # cargado el mismo fichero que en base.
        # self.iface.info("Aplicando informacion contextual . . .")
        # self.xfinal.add_context_id()
        
        self.iface.debug("Aplicando parche . . .")
        patch_fn = self.select_patch_applyfn()
        if patch_fn is None: return
        patch_fn()
        
        self.iface.debug("Limpiando . . .")
        self.xfinal.clean()
        self.xfinal.clean_ctxid()
        self.iface.debug("OK")
        
    def resolve_select(self, element, select):
        path = select.split("/")
        while path:
            p0 = path.pop(0) 
            if p0 == "": 
                newelement = element.getroottree().getroot()
                p0 = path.pop(0) 
                continue
            else:
                newelement = element.xpath("*[@ctx-id=$ctxid]",ctxid = p0)
                if newelement: 
                    newelement = newelement[-1]
                else: 
                    newelement = None
                    toupdate = element.xpath("*[not(@ctx-id)]")
                    for e in toupdate:
                        self.xfinal.apply_one_id(e)
                        if e.get("ctx-id") == p0: newelement = e
                        
            if newelement is None: return element, "/".join([p0] + path)
            element = newelement
        self.xfinal.apply_one_id(element)
        return element, "."
    
    def resolve_select2(self, element, select):
        element, select = self.resolve_select(element, select)
        if select.startswith("text()"): select = "text()"
        elif select == ".": select = "."
        return element, select
    

    def patch_xupdate(self):
        ns = "{http://www.xmldb.org/xupdate}"
        for action in self.patch:
            actionname = None
            if not action.tag.startswith("{"):
                actionname = action.tag
            if action.tag.startswith(ns):
                actionname = action.tag.replace(ns,"")

            if actionname is None:
                self.iface.warn("Tipo de tag no esperado: " + action.tag)
                continue
            select = _select = action.get("select")
            
            element, select = self.resolve_select2(self.xfinal.root, select)
            if actionname == "update" and select == "text()":
                element.text = action.text
            elif actionname == "delete" and select == ".":
                previous = element.getprevious()
                if previous is not None:
                    previous.tail = element.tail
                parent = element.getparent()
                if parent is not None:
                    newelement  = etree.Element("delete-me-when-cleaning")
                    newelement.tail = element.tail
                    newelement.set("ctx-id" , element.get("ctx-id"))
                    parent.replace(element,newelement)
            elif actionname == "insert-after" and select == ".":
                added = deepcopy(action[0])
                tail = element.tail
                if tail is None: tail = ""
                element.addnext(added)
                element.tail = tail + "    "
                self.xfinal.load_entities()
                parent = element.getparent()
                parent.text = None
                for subn in parent:
                    subn.tail = None
                
            elif actionname == "insert-after" and select != ".":
                self.iface.info("No se encontró el elemento y se agregó al final -> %s\t%s\t%s" % (actionname, element.get("ctx-id"), select))
                added = deepcopy(action[0])
                tail = element.text
                try: previous = element.getchildren()[-1]; prev_tail = previous.tail
                except IndexError: previous = None; prev_tail = ""
                element.append(added)
                if previous is not None:
                    print "#" ,repr(prev_tail),repr(tail)
                    added.tail = prev_tail
                    previous.tail = tail
                self.xfinal.load_entities()
            elif actionname == "append-first" and select != ".":
                added = deepcopy(action[0])
                tail = element.text
                element.insert(0,added)
                self.xfinal.load_entities()
            else:
                self.iface.warn("Accion no aplicada -> %s\t%s\t%s" % (actionname, element.get("ctx-id"), select))
                print _select
                
                
            
            
        
        
    
    
#   ^ ^ ^ ^ ^ ^ ^ ^ ^  / class XMLDiffer 


    
    
    
    
    
def diff_lxml(iface, base, final):
    iface.debug(u"Diff LXML $base:%s $final:%s" % (base,final))
    root, ext1 = os.path.splitext(base)
    root, ext2 = os.path.splitext(final)
    if ext1 != ext2:
        iface.warn(u"Comparando ficheros de extensiones diferentes.")
    
    formats = config_tree.xpath("/etc/formats/format[filetype/text()=$ext]/@name", ext=ext1)
    if len(formats) == 0:
        iface.error(u"No tenemos ningún plugin que reconozca esta extensión")
        return
    if len(formats) > 1:
        iface.warn(u"Había más de un formato y hemos probado el primero %s" % (repr(formats)))
    format_name = formats[0]        
    format = config_tree.xpath("/etc/formats/format[@name=$format_name]", format_name=format_name)[0]
    
    try:
        file_base = open(base, "r")
        file_final = open(final, "r")
    except IOError, e:
        iface.error("Error al abrir el fichero base o final: " + str(e))
        return
        
    
    style_name = iface.patch_xml_style_name
    styles = config_tree.xpath("/etc/patch-styles/patch-style[@name=$name]", name=style_name)
    if len(styles) == 0:
        iface.error(u"No tenemos ningún estilo de patch que se llame %s" % style_name)
        return
    if len(styles) > 1:
        iface.warn(u"Había más de un estilo con el nombre %s y hemos cargado el primero." % (repr(style_name)))
    
    style= styles[0]
    
    
    xmldiff = XMLDiffer(iface, format, style, file_base = file_base, file_final = file_final)
    xmldiff.compare()
    #xbase.clean()
    iface.output.write(xmldiff.patch_output())







            
    
def patch_lxml(iface, patch, base):
    iface.debug(u"Patch LXML $patch:%s $base:%s " % (patch, base))
    root, ext1 = os.path.splitext(base)
    
    formats = config_tree.xpath("/etc/formats/format[filetype/text()=$ext]/@name", ext=ext1)
    if len(formats) == 0:
        iface.error("No tenemos ningún plugin que reconozca esta extensión")
        return
    if len(formats) > 1:
        iface.warn(u"Había más de un formato y hemos probado el primero %s" % (repr(formats)))
    format_name = formats[0]        
    format = config_tree.xpath("/etc/formats/format[@name=$format_name]", format_name=format_name)[0]
    
    try:
        file_base = open(base, "r")
        file_final = open(base, "r")
        file_patch = open(patch, "r")
    except IOError, e:
        iface.error(u"Error al abrir el fichero base o parche: " + str(e))
        return
        
    
    style_name = iface.patch_xml_style_name
    styles = config_tree.xpath("/etc/patch-styles/patch-style[@name=$name]", name=style_name)
    if len(styles) == 0:
        iface.error(u"No tenemos ningún estilo de patch que se llame %s" % style_name)
        return
    if len(styles) > 1:
        iface.warn(u"Había más de un estilo con el nombre %s y hemos cargado el primero." % (repr(style_name)))
    
    style= styles[0]
    
    
    xmldiff = XMLDiffer(iface, format, style, file_base = file_base, file_final = file_final, file_patch = file_patch)
    xmldiff.apply_patch()
    iface.output.write(xmldiff.final_output())
    




    
    

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


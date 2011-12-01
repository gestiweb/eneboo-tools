#encoding: UTF-8
from lxml import etree
from copy import deepcopy
import os.path, time
import difflib, re

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
    def __init__(self, iface, format, style, file1, rbt = True, recover = False):
        self.iface = iface
        self.format = format
        self.style = style
        self.default_ctx = None
        self.entities = None
        self.encoding = self.format.xpath("@encoding")[0]
        self.time_sname = 0
        self.time_evaluate = 0
        self.parser = etree.XMLParser(
                        ns_clean=True,
                        encoding=self.encoding,
                        recover=recover, # .. recover funciona y parsea cuasi cualquier cosa.
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
        if from_elem is None: from_elem = self.tree
        t1 = time.time()
        ret = self._evaluate(elem, from_elem)
        t2 = time.time()
        tdelta = (t2-t1) 
        self.time_evaluate += tdelta

        return ret
        
    def _evaluate(self, elem, from_elem = None):
        if elem is None: return None
        if not isinstance(elem.tag, basestring): return None
        if elem.text: text = elem.text.strip()
        else: text = ""
        
        elem_patch_style = elem.get("patch-style")
        if elem_patch_style and self.style.attrib['name'] not in elem_patch_style.split(" "):
            return None
        elem_except_style = elem.get("except-style")
        if elem_except_style and self.style.attrib['name'] in elem_except_style.split(" "):
            return None
            
        def sxpath(text,from_elem,**kwargs):
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
            elif elem.tag == "ctx": 
                name = "ctx-info-"+text
                value = from_elem.get(name)
                return value
            elif elem.tag == "xpath": 
                kwvars = {}
                for subelem in elem:
                    name = subelem.get("name")
                    kwvars[name] = self._evaluate(subelem,from_elem)
                return sxpath(text,from_elem,**kwvars)
            elif elem.tag == "format": 
                format_string = elem.get("text")
                args = []
                kwargs = {}
                for subelem in elem:
                    name = subelem.get("name")
                    value = self._evaluate(subelem,from_elem)
                    if name: kwargs[name] = value
                    else: args.append(value)
                return format_string.format(*args,**kwargs)
            elif elem.tag == "format2": 
                format_string = elem.get("text")
                args = []
                for subelem in elem:
                    value = self._evaluate(subelem,from_elem)
                    if not isinstance(subelem.tag, basestring): continue
                    args.append(value)
                try:
                    retval = format_string % tuple(args)
                except TypeError, e:
                    self.iface.error("Error ejecutando format2: %s %% %s" % (repr(format_string), repr(args)))
                    raise
                return retval
            elif elem.tag == "implode": 
                join_string = str(elem.get("join"))
                args = []
                for subelem in elem:
                    value = self._evaluate(subelem,from_elem)
                    if value is not None and value != "": args.append(str(value))
                return join_string.join(args)
            elif elem.tag == "value": return text
            elif elem.tag == "if-then-else": 
                kwvars = {}
                for subelem in elem:
                    kwvars[subelem.get("name")] = self._evaluate(subelem,from_elem)
                if kwvars['if']:
                    return kwvars.get('then')
                else:
                    return kwvars.get('else')
            else: self.iface.warn("Descartando tag de evaluación desconocido: %s:%s" % (elem.tag,text))
        except Exception, e:
            self.iface.exception("EvaluateError","Error evaluando  %s:%s" % (elem.tag,text))
            return None

    def load_default_entity(self, elem):
        search_xpath = "."
        entity_name = "default"
        if self.default_ctx is None:
            self.default_ctx = self.format.xpath("entities/default/context-information/*")
        self.load_entity(entity_name, self.default_ctx, search_xpath, self.context_items, elem)
    
    def load_entity(self, entity_name, context_info, search_xpath, context_items = [], root = None):
        # self.iface.debug2("Aplicando entidad %s a los elementos %s" % (entity_name,search_xpath))
        #tstart = time.time()
        if root is None: root = self.root
        #search_xpath = "(%s)[not(ancestor-or-self::context-information)]" % search_xpath
        try:
            search = list(root.xpath(search_xpath))
        except Exception, e:
            self.iface.error("search_xpath: " + search_xpath)
            raise
        nsz = len(search)
        processed = 0
        #tinit = time.time()
        for element in search:
            if not isinstance(element.tag, basestring): continue
            parent = element.getparent()
            if parent is not None:
                if parent.tag == "context-information": continue
            # if element.xpath("context-information"): continue
            if element.get("ctx-info-created") is not None: continue
            element.set("ctx-info-created", "yes")
            
            ctx_pending_names = set([])
            ctxdict = {}
            for ctxopt in context_info:
                name = ctxopt.get("name")
                if not name: continue
                
                ctx_pending_names.add(name)
                if name in ctxdict: continue
                
                value = self.evaluate(ctxopt, element)
                if value is None: continue
                
                ctxdict[name] = unicode(value)
                element.set("ctx-info-" + name,unicode(value))
                        
            #ctx = etree.SubElement(element, "context-information", entity = entity_name, **ctxdict)
            #context_items.append(ctx)

            for name, value in ctxdict.items():
                ctx_pending_names.remove(name)
                
            for name in ctx_pending_names:
                self.iface.debug("Regla de contexto sin valor: %s" % name)
            processed += 1
                
        #tend = time.time()
        #tinitms = (tinit - tstart) * 1000
        #tdeltams = (tend - tinit) * 1000
        #if tdeltams + tinitms > 50:
        #    self.iface.info2("%s:  %d/%d items, search_xpath: %s (time %.2fms + %.2fms)" % (entity_name, processed, nsz , search_xpath, tinitms, tdeltams))
        
                
        return True
        
    def load_entities(self, root = None, tag = None):
        self.iface.debug2("Cargando entidades . . . " +  repr(root))
        if self.default_ctx is None:
            self.default_ctx = self.format.xpath("entities/default/context-information/*")
        if self.entities is None:
            self.entities = self.format.xpath("entities/entity")
            self.entities_ctx= {}
            self.entities_tags= {}
            
        for entity in self.entities:
            entity_name = entity.get("name")
            if tag:
                if entity_name not in self.entities_tags:
                    self.entities_tags[entity_name] = entity.xpath("tags/tag/text()")
                if ( tag not in self.entities_tags[entity_name]
                    and tag != entity_name
                    ): 
                    continue
            if entity_name not in self.entities_ctx:
                self.entities_ctx[entity_name] = entity.xpath("context-information/*")
                
            for search_xpath in entity.xpath("search/xpath"):
                ret = self.load_entity(entity_name, self.entities_ctx[entity_name] + self.default_ctx, search_xpath.text.strip(), self.context_items, root)
                if not ret: return False
                
        return True
    
    def sname(self, elem, key, default = None):
        tstart = time.time()
        if elem.get("ctx-info-created") is None: 
            self.load_default_entity(elem)
            
        assert(elem.get("ctx-info-created") is not None)
        ret = None
        for entity in self.style.xpath("entities/*[@name=$key]",key = key):
            val = self.evaluate(entity,from_elem=elem)
            if val is not None: 
                ret = val
                break
        tend = time.time()
        tdelta = tend - tstart
        self.time_sname += tdelta
                
        if ret is None: ret = default
        return ret
    
    def clean_ctxid(self):
            
        for element in self.root.xpath("//delete-me-when-cleaning"):
            parent = element.getparent()
            parent.remove(element)
            
        for element in self.root.iter():
            for k in element.attrib.keys()[:]:
                if k.startswith("ctx-"):
                    del element.attrib[k]
            # del element.attrib["ctx-id"]
        
        reindent_items = self.root.xpath("//*[not(text()) and ./*]")
        if reindent_items:
            # Detectar indentado:
            indent = None
            parent_text = None
            depth = -1
            for element in self.root.iter():
                if len(element) == 0 : continue
                parent_text = element.text 
                subelement = None
                for sub in element:
                    if sub.tail and parent_text is None: parent_text = sub.tail
                    if len(sub) == 0 : continue
                    if sub.text is None: continue
                    subelement = sub
                    break
                if subelement is None: continue
                if parent_text is None: continue
                child_text = subelement.text
                parent_text = parent_text[parent_text.find("\n"):]
                child_text = child_text[child_text.find("\n"):]
                indent = child_text[len(parent_text):] 
                depth = int(element.xpath("count(ancestor::*)"))
                if child_text.startswith(parent_text):
                    break
            if parent_text: parent_text = parent_text[1:]
            else: parent_text =  ""
            reindent_config = depth, parent_text, indent
            #print depth, repr(parent_text), repr(indent)
            
        for element in reindent_items:
            re_depth, re_parent, re_indent = reindent_config
            if depth == -1:
                parent_level = None
                parent = element.getparent()
                if parent is not None: parent_level = parent.text
                if parent_level is None: 
                    parent_level = "\n"
                    increment = "    "
                else:
                    grandparent_level = None
                    grandparent = parent.getparent()
                    if grandparent is not None: grandparent_level = grandparent.text
            
                    if grandparent_level : increment = parent_level.replace(grandparent_level,"")
                    else: increment = "    "
                child_level = parent_level + increment     
                re_indent = increment       
            else:
                depth = int(element.xpath("count(ancestor::*)"))
                def create_indent(depth):
                    ind_sz = len(re_indent)
                    diff = int(depth - re_depth)
                    if diff < 0:
                        txt = "\n" + re_parent[:ind_sz*(diff)]
                        # return "{" + txt
                        return txt
                    if diff > 0:
                        txt = "\n" + re_parent + (re_indent * diff)
                        #return "}" + txt
                        return txt
                    if diff == 0:
                        txt = "\n" + re_parent 
                        #return "=" + txt 
                        return txt
                parent_level = create_indent(depth-1)
                child_level = create_indent(depth)
                
            #increment = "    "
            #parent_level = "\n" + increment * (depth-1)
            
            #self.iface.debug2("Reindentando: %s" % self.tree.getpath(element))
            element.text = child_level
            for child in element[:-1]: child.tail = child_level
            element[-1].tail = parent_level
            if element.tail is None:
                element.tail = parent_level
            
            

    
    def apply_one_id(self, elem, le = True):
        idname = elem.get("ctx-id")
        if idname: return idname
        #if le: self.load_entities(elem)
        if not isinstance(elem.tag,basestring): 
            return elem.text
        else:
            idname = self.sname(elem, "id", elem.tag)
        elem.set("ctx-id",idname)
        #for sub in elem: self.apply_one_id(sub, False)
        return idname
            
    def add_context_id(self, root = None):
        if root is None: 
            root = self.root
            
        self.apply_one_id(root)
            
        for element in root:
            if element.tag == "context-information": continue
            self.add_context_id(element)

# ^ ^ ^ ^ ^ ^     / class XMLFormatParser



class XMLDiffer(object):
    def __init__(self, iface, format, style, file_base, file_final = None, file_patch = None, recover = False):
        self.iface = iface
        self.namespaces = {
            'xsl' : "http://www.w3.org/1999/XSL/Transform", 
            'xupdate' : "http://www.xmldb.org/xupdate",
        }
        self.format = format
        self.style = style
        self.time_resolve_select = 0
        if file_patch: rbt = False # Remove Blank Text 
        else: rbt = True
        self.xbase = XMLFormatParser(self.iface, self.format, self.style, file_base, rbt, recover = recover)
    
        if not self.xbase.validate():
            self.iface.error(u"El fichero base no es válido para el formato %s" % (self.format.get("name")))
            raise ValueError
        if not self.xbase.load_entities():
            self.iface.error(u"Error al cargar entidades del formato %s (fichero base)" % (self.format.get("name")))
            raise ValueError
            
        self.xfinal = XMLFormatParser(self.iface, self.format, self.style, file_final, rbt, recover = recover)

        if not self.xfinal.validate():
            self.iface.error(u"El fichero final no es válido para el formato %s" % (self.format.get("name")))
            raise ValueError
        if not self.xfinal.load_entities():
            self.iface.error(u"Error al cargar entidades del formato %s (fichero final)" % (self.format.get("name")))
            raise ValueError
        if file_patch:
            parser = etree.XMLParser(
                            ns_clean=True,
                            remove_blank_text=True,
                            recover=True,
                            encoding = self.xbase.encoding
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
            if doctype: doctype += "\n"
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
        #if len(elem.xpath("context-information")) == 0:
        if elem.get("ctx-info-created") is None:
            self.xbase.load_default_entity(elem)
            self.xfinal.load_default_entity(elem)
            
        for entity in self.style.xpath("entities/*[@name=$key]",key = key):
            val = self.xbase.evaluate(entity,from_elem=elem)
            if val is not None: return val
        return default
        
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
        try:
            if elem.text: 
                    text = elem.text
            else: text = ""
        except UnicodeDecodeError:
            text = "**UNICODE_DECODE_ERROR**"
            self.iface.warn("Error al leer el texto de un elemento.")
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
                if kwargs["name"].startswith("ctx-info-"): continue
            op = "update"
            if v is None: op = "create"
            if final[k] is None: op = "delete"
            tag = op + "-" + tag
            subelem = etree.SubElement(patchelem, tag, **kwargs)
            if v: subelem.set("old", v)
            if final[k]: subelem.set("new",final[k])
        
        # self.iface.debug2r(_=self.shpath(base_elem), base = base, final = final)
        return None     
        
    def _get_ctxinfo_old(self, elem):
        ctx = elem.xpath("context-information")
        if len(ctx) == 0: ctx = elem.tag
        else: ctx = ";".join(["%s=%s" % (k,v) for k,v in sorted(dict(ctx[0].attrib).items())])
        return ctx

    def get_ctxinfo(self, elem):
        ctx = ";".join(["%s=%s" % (k[9:],v) for k,v in sorted(dict(elem.attrib).items())])
        return ctx

    def compare_subelems(self, base_elem, final_elem):
        base = [ self.xbase.apply_one_id(subelem) for subelem in base_elem if subelem.tag != "context-information"]
        final = [ self.xfinal.apply_one_id(subelem) for subelem in final_elem if subelem.tag != "context-information"]
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
            newelem = deepcopy(subelem)
            updelem.append( newelem )
            for ie in newelem.iter():
                for k in ie.attrib.keys():
                    if k.startswith("ctx-info-"): 
                        del ie.attrib[k]
                    if k.startswith("ctx-id"): 
                        del ie.attrib[k]
                    
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
        if self.patch is None:
            self.iface.warn("Sin parche que aplicar (vacío o inexistente)")
            return None
        elif self.patch.tag not in known_tags:
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
                    newelement = newelement[0]
                else: 
                    newelement = None
                    toupdate = element.xpath("*[not(@ctx-id)]")
                    for e in toupdate:
                        self.xfinal.apply_one_id(e)
                        if e.get("ctx-id") == p0: newelement = e
                    
                    if newelement is None: # Intentar mas a fondo:
                        m = re.match("(\w+)\[(\w+),(\d+)\]", p0)
                        if m:
                            tagname = m.group(1)
                            number = int(m.group(3))-1
                            elist = element.xpath(tagname)
                            
                            try: newelement = elist[number]
                            except Exception, e: 
                                self.iface.warn(e)
                                newelement = None
                                
                    if newelement is None: # Intentar con nombre *muy* parecido:
                        alternatives = element.xpath("*/@ctx-id")
                        close_matches = difflib.get_close_matches(p0, alternatives, 1, 0.92)
                        if close_matches:
                            newelement = element.xpath("*[@ctx-id=$ctxid]",ctxid = close_matches[0])
                            if newelement: 
                                newelement = newelement[0]
                            else: 
                                newelement = None
                    
                    
            if newelement is None: return element, "/".join([p0] + path)
            elif newelement.get("ctx-id") != p0:
                self.iface.info2("Seleccionamos %s cuando buscabamos %s" % (newelement.get("ctx-id"), p0))
            element = newelement
        self.xfinal.apply_one_id(element)
        return element, "."
    
    def resolve_select2(self, element, select):
        tstart = time.time()
        element, select = self.resolve_select(element, select)
        if select.startswith("text()"): select = "text()"
        elif select.startswith("#text"): select = "text()"
        elif select == ".": select = "."
        tend = time.time()
        tdelta = tend - tstart
        self.time_resolve_select += tdelta
        return element, select
    

    def patch_xupdate(self):
        for action in self.patch: self.do_patch_action(action)
    
    def do_patch_action(self, action):
        #tstart = time.time()
        self._do_patch_action(action)
        #tend = time.time()
        #tdeltams = (tend - tstart) * 1000
        #if tdeltams > 30:
        #    ns = "{http://www.xmldb.org/xupdate}"
        #    self.iface.msg("-- Accion %s %s , %.2f ms (%.2f ms resolving selects)" % (action.tag.replace(ns,""), action.attrib["select"][-30:], tdeltams, self.time_resolve_select*1000 ))
    
    def _do_patch_action(self, action):
        ns = "{http://www.xmldb.org/xupdate}"
        actionname = None
        if not action.tag.startswith("{"):
            actionname = action.tag
        if action.tag.startswith(ns):
            actionname = action.tag.replace(ns,"")

        if actionname is None:
            self.iface.warn("Tipo de tag no esperado: " + action.tag)
            return
        select = _select = action.get("select")
        element, select = self.resolve_select2(self.xfinal.root, select)
        #if '/' in select:
        #    self.xfinal.load_entities()
        #    element, select = self.resolve_select2(self.xfinal.root, select)
            
        if '/' in select:
            searching = select.split("/")[0]
            alternatives = element.xpath("*/@ctx-id")
            close_matches = difflib.get_close_matches(searching, alternatives, 4, 0.4)
            self.iface.warn("Error buscando el elemento %s entre %s" % (repr(searching),close_matches))
            return
        
        if actionname == "update" and select == "text()":
            element.text = action.text
        elif actionname == "delete" and select == "text()":
            element.text = None
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
        elif actionname == "delete" and select != ".":
            searching = select.split("/")[0]
            alternatives = element.xpath("*/@ctx-id")
            close_matches = difflib.get_close_matches(searching, alternatives, 4, 0.4)
            self.iface.warn("No se encontró el elemento %s entre %s y no se eliminó nada" % (searching,close_matches))
        elif actionname == "insert-after" and select == ".":
            added = deepcopy(action[0])
            tail = element.tail
            if tail is None: tail = ""
            element.addnext(added)
            element.tail = tail + "    "
            parent = element.getparent()
            parent.text = None
            for subn in parent:
                subn.tail = None
            self.xfinal.load_entities(parent,added.tag)
            
        elif actionname == "insert-after" and select != ".":
            searching = select.split("/")[0]
            alternatives = element.xpath("*/@ctx-id")
            close_matches = difflib.get_close_matches(searching, alternatives, 4, 0.4)
        
            self.iface.warn("No se encontró el elemento %s entre %s y se agregó el nodo al final" % (searching,close_matches))
            added = deepcopy(action[0])
            tail = element.text
            try: previous = element.getchildren()[-1]; prev_tail = previous.tail
            except IndexError: previous = None; prev_tail = ""
            element.append(added)
            if previous is not None:
                added.tail = prev_tail
                previous.tail = tail
            parent = element.getparent()
            self.xfinal.load_entities(parent,added.tag)
        elif actionname == "append-first" and select == ".":
            added = deepcopy(action[0])
            tail = element.text
            element.insert(0,added)
            parent = element.getparent()
            self.xfinal.load_entities(parent,added.tag)
        else:
            self.iface.warn("Accion no aplicada -> %s\t%s\t%s" % (actionname, element.get("ctx-id"), select))
                
                
            
            
        
        
    
    
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
    try:
        xmldiff = XMLDiffer(iface, format, style, file_base = file_base, file_final = file_final)
    except etree.XMLSyntaxError, e: 
        iface.warn(u"Error parseando fichero XML: %s" % (str(e)))
        iface.warn(u".. durante Diff LXML $base:%s $final:%s" % (base,final))
        try:
            file_base = open(base, "r")
            file_final = open(final, "r")
            xmldiff = XMLDiffer(iface, format, style, file_base = file_base, file_final = file_final, recover = True)
        except etree.XMLSyntaxError, e: 
            iface.error(u"Error parseando fichero XML: %s" % (str(e)))
            iface.error(u".. durante Diff LXML $base:%s $final:%s" % (base,final))
            return False
    except ValueError:
        return False

    patch = xmldiff.compare()
    if len(patch) == 0: return -1
    #xbase.clean()
    iface.output.write(xmldiff.patch_output())
    return True







            
    
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
    
    tstart = time.time()
    
    xmldiff = XMLDiffer(iface, format, style, file_base = file_base, file_final = file_final, file_patch = file_patch)
    
    t1 = time.time()
    
    xmldiff.apply_patch()

    t2 = time.time()
    
    iface.output.write(xmldiff.final_output())

    tend = time.time()
    tdeltams = (tend - tstart) * 1000
    
    if tdeltams > 300:
        tdeltams1 = (t1 - tstart) * 1000
        tdeltams2 = (t2 - t1) * 1000
        tdeltams3 = (tend - t2) * 1000
        #iface.info2("-- Time %.2f ms = %.2f ms +%.2f ms + %.2f ms  (%.2f ms resolving, %.2f ms sname)" % (tdeltams,tdeltams1,tdeltams2,tdeltams3,xmldiff.time_resolve_select*1000,xmldiff.xbase.time_sname*1000+xmldiff.xfinal.time_sname*1000))
        iface.info2("-- Time %.2f ms , %.2f ms sname , %.2f ms evaluating" % (tdeltams,xmldiff.xbase.time_sname*1000+xmldiff.xfinal.time_sname*1000, xmldiff.xbase.time_evaluate*1000+xmldiff.xfinal.time_evaluate*1000))

    return True




    
    

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


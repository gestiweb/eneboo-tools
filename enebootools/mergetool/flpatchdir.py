# encoding: UTF-8
from lxml import etree
from copy import deepcopy
import os, os.path, shutil
import difflib, time
import hashlib, fnmatch

from enebootools.mergetool import flpatchqs, flpatchlxml

def filepath(): return os.path.abspath(os.path.dirname(__file__))
def filedir(x): return os.path.abspath(os.path.join(filepath(),x))

def hash_file(dirname, filename):
    f1 = open(os.path.join(dirname, filename))
    sha = hashlib.sha224()
    while True:
        chunk = f1.read(4096)
        if not chunk: break
        sha.update(chunk)
    return sha.hexdigest()

def hash_none():
    sha = hashlib.sha224()
    return sha.hexdigest()
    
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

class FolderApplyPatch(object):
    def __init__(self, iface, patchdir):
        self.iface = iface
        if patchdir[-1] == "/": patchdir = patchdir[:-1]
        try:
            patchname = open(os.path.join(patchdir,"conf","patch_series")).read().strip()
            newpatchdir = os.path.join(patchdir,"patches",patchname)
            iface.warn("Cambiando carpeta de parche a %s" % newpatchdir)
            patchdir = newpatchdir
        except Exception:
            pass
        if getattr(self.iface,"patch_name",None):
            self.patch_name = self.iface.patch_name
        else:
            self.patch_name = os.path.basename(patchdir)
        expected_file = self.patch_name + ".xml"
        self.patch_dir = None
        for root, dirs, files in os.walk(patchdir):
            if expected_file in files:
                self.patch_dir = root
                break
        if self.patch_dir is None:
            self.iface.error("No pude encontrar %s en ninguna subcarpeta del parche." % expected_file)
            self.patch_dir = patchdir

        patch_file = os.path.join(self.patch_dir, expected_file)
        try:
            self.encoding = "iso-8859-15"
            self.parser = etree.XMLParser(
                            ns_clean=False,
                            encoding=self.encoding,
                            recover=True, # .. recover funciona y parsea cuasi cualquier cosa.
                            remove_blank_text=True,
                            )
            self.tree = etree.parse(patch_file, self.parser)
            self.root = self.tree.getroot()
        except IOError, e:
            self.root = None
            iface.error("No se pudo leer el parche: " + str(e))
    
    def patch_folder(self, folder):
        if self.root is None: return
        for action in self.root:
            
            actionname = action.tag
            if not isinstance(actionname,basestring): continue
            if actionname.startswith("{"):
                actionname = action.tag.split("}")[1]
            actionname = actionname.lower()
            if actionname.startswith("flpatch:"):
              actionname = actionname.split(":")[1]
              
            tbegin = time.time()
            try:
                if actionname == "addfile": self.add_file(action, folder)
                elif actionname == "deletefile": self.delete_file(action, folder)
                elif actionname == "replacefile": self.replace_file(action, folder)
                elif actionname == "patchscript": self.patch_script(action, folder)
                elif actionname == "patchxml": self.patch_xml(action, folder)
                # TODO: actionname == "patchphp" 
                else: self.iface.warn("** Se ha ignorado acción desconocida %s **" % repr(actionname))
            except Exception, e:
                self.iface.exception("ComputePatch", "No se pudo aplicar el parche para %s" % action.get("name"))
            
            tend = time.time()
            tdelta = tend - tbegin
            if tdelta > 1:
                self.iface.debug("La operación tomó %.2f segundos" % tdelta)
    
    def get_patch_info(self):
        if self.root is None: return
        info = {"provides" : [], "requires" : []}
        
        for action in self.root:
            actionname = action.tag
            if actionname.startswith("{"):
                actionname = action.tag.split("}")[1]
            actionname = actionname.lower()
            
            pathname = os.path.join(action.get("path"),action.get("name"))
            
            atype = None
            if actionname == "addfile": atype = "provides"
            elif actionname == "replacefile": atype = "requires"
            elif actionname == "patchscript": atype = "requires"
            elif actionname == "patchxml": atype = "requires"
            info[atype].append(pathname)
        return info
            
            
    
    def add_file(self, addfile, folder):            
        path = addfile.get("path")
        filename = addfile.get("name")
        module_path = path
        while module_path.count("/") > 1:
            module_path = os.path.dirname(module_path)
        if not os.path.exists(os.path.join(folder,module_path)):
            if os.path.relpath(path, module_path).count("/") > 0:
                self.iface.warn("Ignorando la creación de fichero %s (el módulo no existe)" % filename)
                return
        
        pathname = os.path.join(path, filename)
        src = os.path.join(self.patch_dir,filename)
        dst = os.path.join(folder,pathname)
        dst_parent = os.path.dirname(dst)
        
        self.iface.debug("Copiando %s . . ." % filename)
        if not os.path.exists(dst_parent):
            os.makedirs(dst_parent)
        
        shutil.copy(src, dst)
        
    def delete_file(self, addfile, folder):            
        path = addfile.get("path")
        filename = addfile.get("name")
        module_path = path
        while module_path.count("/") > 1:
            module_path = os.path.dirname(module_path)
        if not os.path.exists(os.path.join(folder,module_path)):
            self.iface.info("Ignorando el borrado de fichero %s (el módulo no existe)" % filename)
            return
        
        pathname = os.path.join(path, filename)
        src = os.path.join(self.patch_dir,filename)
        dst = os.path.join(folder,pathname)
        dst_parent = os.path.dirname(dst)
        
        if os.path.exists(dst_parent):
            if os.path.exists(dst):
                self.iface.info("Borrando %s . . ." % filename)
                os.unlink(dst)
            else:
                self.iface.warn("Se iba a borrar %s, pero no existe." % filename)
            
    
    def replace_file(self, replacefile, folder):            
        path = replacefile.get("path")
        filename = replacefile.get("name")
        
        pathname = os.path.join(path, filename)
        dst = os.path.join(folder,pathname)
        if not os.path.exists(dst):
            self.iface.warn("Ignorando reemplazo de fichero para %s (el fichero no existe)" % filename)
            return
        
        self.iface.debug("Reemplazando fichero %s . . ." % filename)
        src = os.path.join(self.patch_dir,filename)
        os.unlink(dst)
        shutil.copy(src, dst)
                
    def patch_script(self, patchscript, folder):
        style = patchscript.get("style", "legacy")
        path = patchscript.get("path")
        filename = patchscript.get("name")
        
        pathname = os.path.join(path, filename)
        src = os.path.join(self.patch_dir,filename)
        dst = os.path.join(folder,pathname)
        
        if not os.path.exists(dst):
            self.iface.warn("Ignorando parche QS para %s (el fichero no existe)" % filename)
            return
        self.iface.info("Aplicando parche QS %s . . ." % filename)
        old_output = self.iface.output
        old_verbosity = self.iface.verbosity
        self.iface.verbosity -= 2
        if self.iface.verbosity < 0: self.iface.verbosity = 0
        old_style, self.iface.patch_qs_style_name = self.iface.patch_qs_style_name, style
        self.iface.set_output_file(dst+".patched")
        if style in ['legacy']:
            ret = flpatchqs.patch_qs(self.iface,dst,src)
        elif style in ['qsdir']:
            ret = flpatchqs.patch_qs_dir(self.iface,dst,src)
        else:
            raise ValueError, "Estilo de parche QS desconocido: %s" % style
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        self.iface.patch_qs_style_name = old_style
        if not ret:
            self.iface.warn("Hubo algún problema aplicando el parche QS para %s" % filename)
            try: os.unlink(dst+".patched")
            except IOError: pass
        else:
            os.unlink(dst)
            os.rename(dst+".patched",dst)
                
    def patch_xml(self, patchxml, folder):
        style = patchxml.get("style", "legacy1")
        path = patchxml.get("path")
        filename = patchxml.get("name")
        
        pathname = os.path.join(path, filename)
        src = os.path.join(self.patch_dir,filename)
        dst = os.path.join(folder,pathname)
        
        if not os.path.exists(dst):
            self.iface.warn("Ignorando parche XML para %s (el fichero no existe)" % filename)
            return
        self.iface.info("Aplicando parche XML %s . . ." % filename)
        old_output = self.iface.output
        old_verbosity = self.iface.verbosity
        self.iface.verbosity -= 2
        if self.iface.verbosity < 0: self.iface.verbosity = min([0,self.iface.verbosity])
        self.iface.set_output_file(dst+".patched")
        ret = flpatchlxml.patch_lxml(self.iface,src,dst)
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        if not ret:
            self.iface.warn("Hubo algún problema aplicando el parche XML para %s" % filename)
            try: os.unlink(dst+".patched")
            except IOError: pass
        else:
            os.unlink(dst)
            os.rename(dst+".patched",dst)
        
        
class FolderCreatePatch(object):
    nsmap = {
        'flpatch' : "http://www.abanqg2.com/es/directori/abanq-ensambla/?flpatch",
    }
    def __init__(self, iface, basedir, finaldir, patchdir):
        self.iface = iface
        if patchdir[-1] == "/": patchdir = patchdir[:-1]
        if self.iface.patch_name:
            self.patch_name = self.iface.patch_name
        else:
            self.patch_name = os.path.basename(patchdir)
        expected_file = self.patch_name + ".xml"
        self.patchdir = patchdir
        self.basedir = basedir
        self.finaldir = finaldir

        self.patch_filename = os.path.join(self.patchdir, expected_file)
        
        self.encoding = "iso-8859-15"
        # <flpatch:modifications name="patchname" >
        self.root = etree.Element("{%s}modifications" % self.nsmap['flpatch'], name=self.patch_name, nsmap=self.nsmap)
        self.tree = self.root.getroottree()
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
        basedir_files = set([])
        
        for root, dirs, files in os.walk(basedir):
            baseroot = os.path.relpath(root,basedir)
            for pattern in ignored_files:
                delfiles = fnmatch.filter(files, pattern)
                for f in delfiles: files.remove(f)
                deldirs = fnmatch.filter(dirs, pattern)
                for f in deldirs: dirs.remove(f)
                
            for filename in files:
                basedir_files.add( os.path.join( baseroot, filename ) ) 

        finaldir_files = set([])
    
        for root, dirs, files in os.walk(finaldir):
            baseroot = os.path.relpath(root,finaldir)
            for pattern in ignored_files:
                delfiles = fnmatch.filter(files, pattern)
                for f in delfiles: files.remove(f)
                deldirs = fnmatch.filter(dirs, pattern)
                for f in deldirs: dirs.remove(f)

            for filename in files:
                finaldir_files.add( os.path.join( baseroot, filename ) ) 
    
        self.added_files = finaldir_files - basedir_files
        self.deleted_files = basedir_files - finaldir_files
        self.common_files = finaldir_files & basedir_files
        #print "+" , self.added_files
        #print "-" , self.deleted_files
        #print "=" , self.common_files
        
        iface.info("Calculando diferencias . . . ")
        
        file_actions = []
        file_actions += [ (os.path.dirname(f),f, "add") for f in self.added_files ]
        file_actions += [ (os.path.dirname(f),f, "common") for f in self.common_files ]
        file_actions += [ (os.path.dirname(f),f, "delete") for f in self.deleted_files ]
        # Intentar guardarlos de forma ordenada, para minimizar las diferencias entre parches.
        for path, filename, action in sorted(file_actions):
            if action == "add":
                self.add_file(filename)
            elif action == "common":
                self.compare_file(filename)
            elif action == "delete":
                self.remove_file(filename)
            else: raise ValueError

        
    def create_action(self, actionname, filename):
        path, name = os.path.split(filename)
        if len(path) and not path.endswith("/"): path += "/"
        newnode = etree.SubElement(self.root, "{%s}%s" % (self.nsmap['flpatch'], actionname), path = path, name = name)
        return newnode

    def add_file(self, filename):  
        # flpatch:addFile
        self.create_action("addFile",filename)
        
    def compare_file(self, filename):
        # Hay que comparar si son iguales o no
        base_hexdigest = hash_file(self.basedir, filename)
        final_hexdigest = hash_file(self.finaldir, filename)
        none_hexdigest = hash_none()
        if final_hexdigest == base_hexdigest: return
        if base_hexdigest == none_hexdigest: 
            self.create_action("replaceFile",filename)
            return
        if final_hexdigest == none_hexdigest: 
            return
        
        script_exts = ".qs".split(" ")
        xml_exts = ".xml .ui .mtd".split(" ")
        php_exts = ".php".split(" ")
        
        path, name = os.path.split(filename)
        froot, ext = os.path.splitext(name)
        
        if ext in script_exts:
            # flpatch:patchScript
            self.create_action("patchScript",filename)
        elif ext in xml_exts:
            # flpatch:patchXml
            self.create_action("patchXml",filename)
        #elif ext in php_exts:
        # TODO: flpatch:patchPhp 
        else:        
            # flpatch:replaceFile
            self.create_action("replaceFile",filename)
        
    def remove_file(self, filename):
        self.create_action("deleteFile",filename)
        # self.iface.warn("Se detectó borrado del fichero %s, pero flpatch no soporta esto. No se guardará este cambio." % filename)
        
    def create_patch(self):
        for action in self.root:
            actionname = action.tag
            if actionname.startswith("{"):
                actionname = action.tag.split("}")[1]
            actionname = actionname.lower()
            
            tbegin = time.time()
            path = action.get("path")
            if path:
                if path.endswith("/"):
                    path = path[:-1]
                action.set("path",path + "/")
            ret = 1
            try:
                if actionname == "addfile": ret = self.compute_add_file(action)
                elif actionname == "deletefile": ret = self.compute_delete_file(action)
                elif actionname == "replacefile": ret = self.compute_replace_file(action)
                elif actionname == "patchscript": ret = self.compute_patch_script(action)
                elif actionname == "patchxml": ret = self.compute_patch_xml(action)
                # TODO: actionname == "patchphp" 
                else: self.iface.warn("** Se ha ignorado acción desconocida %s **" % repr(actionname))
            except Exception, e:
                self.iface.exception("ComputePatch", "No se pudo computar el parche para %s" % action.get("name"))
                
            if ret == -1:
                self.root.remove(action)
            tend = time.time()
            tdelta = tend - tbegin
            if tdelta > 1:
                self.iface.debug("La operación tomó %.2f segundos" % tdelta)
                
        f1 = open(self.patch_filename,"w")
        f1.write(_xf(self.root,xml_declaration=False,cstring=True,encoding=self.encoding))
        f1.close()

    def compute_delete_file(self, addfile):            
        path = addfile.get("path")
        filename = addfile.get("name")
        
        pathname = os.path.join(path, filename)
        # NO SE HACE NADA.
        

    def compute_add_file(self, addfile):            
        path = addfile.get("path")
        filename = addfile.get("name")
        
        pathname = os.path.join(path, filename)
        self.iface.debug("Copiando fichero %s (nuevo) . . ." % filename)
        dst = os.path.join(self.patchdir,filename)
        src = os.path.join(self.finaldir,pathname)
        
        shutil.copy(src, dst)
            
    
    def compute_replace_file(self, replacefile):            
        path = replacefile.get("path")
        filename = replacefile.get("name")
        
        pathname = os.path.join(path, filename)
        src = os.path.join(self.finaldir,pathname)
        
        self.iface.debug("Copiando fichero %s (reemplazado) . . ." % filename)
        dst = os.path.join(self.patchdir,filename)
        shutil.copy(src, dst)
                
    def compute_patch_script(self, patchscript):
        patchscript.set("style", self.iface.patch_qs_style_name)
        path = patchscript.get("path")
        filename = patchscript.get("name")

        pathname = os.path.join(path, filename)
        dst = os.path.join(self.patchdir,filename)
        base = os.path.join(self.basedir,pathname)
        final = os.path.join(self.finaldir,pathname)
    
        self.iface.info("Generando parche QS %s . . ." % filename)
        old_output = self.iface.output
        old_verbosity = self.iface.verbosity
        self.iface.verbosity -= 2
        if self.iface.verbosity < 0: self.iface.verbosity = min([0,self.iface.verbosity])
        self.iface.set_output_file(dst)
        if self.iface.patch_qs_style_name in ['legacy']:
            ret = flpatchqs.diff_qs(self.iface,base,final)
        elif self.iface.patch_qs_style_name in ['qsdir']:
            ret = flpatchqs.diff_qs_dir(self.iface,base,final)
        else:
            raise ValueError, "patch_qs_style_name no reconocido: %s" % self.iface.patch_qs_style_name
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        if ret == -1:
            os.unlink(dst)
            return -1
        if not ret:
            self.iface.warn("Pudo haber algún problema generando el parche QS para %s" % filename)
                
    def compute_patch_xml(self, patchxml):
        patchxml.set("style", self.iface.patch_xml_style_name)
        path = patchxml.get("path")
        filename = patchxml.get("name")
        pathname = os.path.join(path, filename)
        dst = os.path.join(self.patchdir,filename)
        base = os.path.join(self.basedir,pathname)
        final = os.path.join(self.finaldir,pathname)
        self.iface.info("Generando parche XML %s . . ." % filename)
        old_output = self.iface.output
        old_verbosity = self.iface.verbosity
        self.iface.verbosity -= 2
        if self.iface.verbosity < 0: self.iface.verbosity = min([0,self.iface.verbosity])
        self.iface.set_output_file(dst)
        ret = flpatchlxml.diff_lxml(self.iface,base,final)
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        if ret == -1:
            os.unlink(dst)
            return -1
        if not ret:
            self.iface.warn("Pudo haber algún problema generando el parche XML para %s" % filename)
        


def diff_folder(iface, basedir, finaldir, patchdir, inplace = False):
    iface.debug(u"Folder Diff $basedir:%s $finaldir:%s $patchdir:%s" % (basedir,finaldir,patchdir))
    # patchdir no debe existir
    parent_patchdir = os.path.abspath(os.path.join(patchdir,".."))
    if not os.path.exists(parent_patchdir):
        iface.error("La ruta %s no existe" % parent_patchdir)
        return
    if not os.path.exists(basedir):
        iface.error("La ruta %s no existe" % basedir)
        return
    if not os.path.exists(finaldir):
        iface.error("La ruta %s no existe" % finaldir)
        return
    if not inplace:
        if os.path.lexists(patchdir):
            iface.error("La ruta a $finaldir %s ya existía. No se continua. " % patchdir)
            return
    if not os.path.lexists(patchdir):
        os.mkdir(patchdir)

    fpatch = FolderCreatePatch(iface, basedir, finaldir, patchdir)
    fpatch.create_patch()
    

    
    
    
    
def patch_folder(iface, basedir, finaldir, patchdir):
    iface.debug(u"Folder Patch $basedir:%s $finaldir:%s $patchdir:%s" % (basedir,finaldir,patchdir))
    if not os.path.exists(basedir):
        iface.error("La ruta %s no existe" % basedir)
        return
    if not os.path.exists(patchdir):
        iface.error("La ruta %s no existe" % patchdir)
        return
    if finaldir == ":inplace":
        basedir, finaldir = finaldir , basedir
        
        # finaldir no debe existir
        parent_finaldir = os.path.abspath(os.path.join(finaldir,".."))
        if not os.path.exists(parent_finaldir):
            iface.error("La ruta %s no existe" % parent_finaldir)
            return
    else:
        # finaldir no debe existir
        parent_finaldir = os.path.abspath(os.path.join(finaldir,".."))
        if not os.path.exists(parent_finaldir):
            iface.error("La ruta %s no existe" % parent_finaldir)
            return
        if os.path.lexists(finaldir):
            iface.error("La ruta a $finaldir %s ya existía. No se continua. " % finaldir)
            return
    
        os.mkdir(finaldir)

        for node in os.listdir(basedir):
            if node.startswith("."): continue
            src = os.path.join(basedir, node)
            if not os.path.isdir(src): continue
            dst = os.path.join(finaldir, node)
            iface.debug("Copiando %s . . . " % node)
            shutil.copytree(src,dst)
        
    
    fpatch = FolderApplyPatch(iface, patchdir)
    fpatch.patch_folder(finaldir)
        

def patch_folder_inplace(iface, patchdir, finaldir):
    fpatch = FolderApplyPatch(iface, patchdir)
    fpatch.patch_folder(finaldir)


def get_patch_info(iface, patchdir):
    fpatch = FolderApplyPatch(iface, patchdir)
    return fpatch.get_patch_info()


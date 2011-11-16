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
        if self.iface.patch_name:
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
        
        self.encoding = "iso-8859-15"
        self.parser = etree.XMLParser(
                        ns_clean=False,
                        encoding=self.encoding,
                        recover=True, # .. recover funciona y parsea cuasi cualquier cosa.
                        remove_blank_text=True,
                        )
        self.tree = etree.parse(patch_file, self.parser)
        self.root = self.tree.getroot()
    
    def patch_folder(self, folder):
        for action in self.root:
            actionname = action.tag
            if actionname.startswith("{"):
                actionname = action.tag.split("}")[1]
            actionname = actionname.lower()
            
            tbegin = time.time()
            
            if actionname == "addfile": self.add_file(action, folder)
            elif actionname == "replacefile": self.replace_file(action, folder)
            elif actionname == "patchscript": self.patch_script(action, folder)
            elif actionname == "patchxml": self.patch_xml(action, folder)
            # TODO: actionname == "patchphp" 
            else: self.iface.warn("** Se ha ignorado acción desconocida %s **" % repr(actionname))
            tend = time.time()
            tdelta = tend - tbegin
            if tdelta > 1:
                self.iface.debug("La operación tomó %.2f segundos" % tdelta)
            
    
    def add_file(self, addfile, folder):            
        path = addfile.get("path")
        filename = addfile.get("name")
        
        pathname = os.path.join(path, filename)
        self.iface.debug("Copiando %s . . ." % filename)
        src = os.path.join(self.patch_dir,filename)
        dst = os.path.join(folder,pathname)
        dst_parent = os.path.dirname(dst)
        if not os.path.exists(dst_parent):
            os.makedirs(dst_parent)
        
        shutil.copy(src, dst)
            
    
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
        if self.iface.verbosity < 0: self.iface.verbosity = min([0,self.iface.verbosity])
        self.iface.set_output_file(dst+".patched")
        ret = flpatchqs.patch_qs(self.iface,dst,src)
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        if not ret:
            self.iface.warn("Pudo haber algún problema aplicando el parche QS para %s" % filename)
        os.unlink(dst)
        os.rename(dst+".patched",dst)
                
    def patch_xml(self, patchxml, folder):
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
            self.iface.warn("Pudo haber algún problema aplicando el parche XML para %s" % filename)

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
            baseroot = root[len(basedir)+1:]
            for pattern in ignored_files:
                delfiles = fnmatch.filter(files, pattern)
                for f in delfiles: files.remove(f)
                deldirs = fnmatch.filter(dirs, pattern)
                for f in deldirs: dirs.remove(f)
                
            for filename in files:
                basedir_files.add( os.path.join( baseroot, filename ) ) 

        finaldir_files = set([])
    
        for root, dirs, files in os.walk(finaldir):
            baseroot = root[len(finaldir)+1:]
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
        for filename in self.added_files:
            self.add_file(filename)

        for filename in self.common_files:
            self.compare_file(filename)
        
        for filename in self.deleted_files:
            self.remove_file(filename)
        
    def create_action(self, actionname, filename):
        path, name = os.path.split(filename)
        if not path.endswith("/"): path += "/"
        newnode = etree.SubElement(self.root, "{%s}%s" % (self.nsmap['flpatch'], actionname), path = path, name = name)
        return newnode

    def add_file(self, filename):  
        # flpatch:addFile
        self.create_action("addFile",filename)
        
    def compare_file(self, filename):
        # Hay que comparar si son iguales o no
        base_hexdigest = hash_file(self.basedir, filename)
        final_hexdigest = hash_file(self.finaldir, filename)
        if final_hexdigest == base_hexdigest: return
        
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
        self.iface.warn("Se detectó borrado del fichero %s, pero flpatch no soporta esto. No se guardará este cambio." % filename)
        
    def create_patch(self):
        for action in self.root:
            actionname = action.tag
            if actionname.startswith("{"):
                actionname = action.tag.split("}")[1]
            actionname = actionname.lower()
            
            tbegin = time.time()
            ret = 1
            if actionname == "addfile": ret = self.compute_add_file(action)
            elif actionname == "replacefile": ret = self.compute_replace_file(action)
            elif actionname == "patchscript": ret = self.compute_patch_script(action)
            elif actionname == "patchxml": ret = self.compute_patch_xml(action)
            # TODO: actionname == "patchphp" 
            else: self.iface.warn("** Se ha ignorado acción desconocida %s **" % repr(actionname))
            if ret == -1:
                self.root.remove(action)
            tend = time.time()
            tdelta = tend - tbegin
            if tdelta > 1:
                self.iface.debug("La operación tomó %.2f segundos" % tdelta)
                
        f1 = open(self.patch_filename,"w")
        f1.write(_xf(self.root,xml_declaration=False,cstring=True,encoding=self.encoding))
        f1.close()

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
        ret = flpatchqs.diff_qs(self.iface,base,final)
        self.iface.output = old_output 
        self.iface.verbosity = old_verbosity
        if ret == -1:
            os.unlink(dst)
            return -1
        if not ret:
            self.iface.warn("Pudo haber algún problema generando el parche QS para %s" % filename)
                
    def compute_patch_xml(self, patchxml):
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
        


def diff_folder(iface, basedir, finaldir, patchdir):
    iface.debug(u"Folder Diff $basedir:%s $finaldir:%s $patchdir:%s" % (basedir,finaldir,patchdir))
    # patchdir no debe existir
    parent_patchdir = os.path.abspath(os.path.join(patchdir,".."))
    if not os.path.exists(parent_patchdir):
        iface.error("La ruta %s no existe" % parent_patchdir)
        return
    if os.path.lexists(patchdir):
        iface.error("La ruta a $finaldir %s ya existía. No se continua. " % patchdir)
        return
    if not os.path.exists(basedir):
        iface.error("La ruta %s no existe" % basedir)
        return
    if not os.path.exists(finaldir):
        iface.error("La ruta %s no existe" % finaldir)
        return
        
    os.mkdir(patchdir)

    fpatch = FolderCreatePatch(iface, basedir, finaldir, patchdir)
    fpatch.create_patch()
    

    
    
    
    
def patch_folder(iface, basedir, finaldir, patchdir):
    iface.debug(u"Folder Patch $basedir:%s $finaldir:%s $patchdir:%s" % (basedir,finaldir,patchdir))
    # finaldir no debe existir
    parent_finaldir = os.path.abspath(os.path.join(finaldir,".."))
    if not os.path.exists(parent_finaldir):
        iface.error("La ruta %s no existe" % parent_finaldir)
        return
    if os.path.lexists(finaldir):
        iface.error("La ruta a $finaldir %s ya existía. No se continua. " % finaldir)
        return
    if not os.path.exists(basedir):
        iface.error("La ruta %s no existe" % basedir)
        return
    if not os.path.exists(patchdir):
        iface.error("La ruta %s no existe" % patchdir)
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
        


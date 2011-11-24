# encoding: UTF-8
import os
from lxml import etree
from enebootools.lib.utils import one, find_files, get_max_mtime, read_file_list
from enebootools.mergetool import flpatchdir
import shutil

class BuildInstructions(object):
    def __init__(self, iface, instructions):
        self.instructions = instructions
        self.iface = iface
        assert( self.instructions.tag in ["BuildInstructions"] )
        self.path = self.instructions.get("path")
        self.dstfolder = self.instructions.get("dstfolder")
        self.feature = self.instructions.get("feature")
        self.target = self.instructions.get("target")
        self.dstpath = os.path.join(self.path, self.dstfolder)
        
    def execute(self):
        if os.path.exists(self.dstpath):
            self.iface.debug("Borrando carpeta %s ..." % self.dstpath)
            shutil.rmtree(self.dstpath)
        os.mkdir(self.dstpath)
        for instruction in self.instructions:
            if instruction.tag == "CopyFolderAction":
                self.copyFolder(**instruction.attrib)
            elif instruction.tag == "ApplyPatchAction":
                self.applyPatch(**instruction.attrib)
            else:
                self.iface.warn("Accion %s desconocida" % instruction.tag)
        
    def copyFolder(self,src,dst,create_dst=False):
        if create_dst == "yes": create_dst = True
        if create_dst == "no": create_dst = False
        self.iface.debug("copyFolder src=%s dst=%s" % (src, dst))
        dst = os.path.join(self.dstpath, dst)
        if not os.path.exists(src):
            self.iface.error("La carpeta %s no existe" % src)
            return False
        pdst = os.path.dirname(dst)
        if not os.path.exists(pdst):
            if create_dst:
                os.makedirs(pdst)
            else:
                self.iface.error("La carpeta %s no existe" % pdst)
                return False
        if os.path.exists(dst):
            self.iface.error("La carpeta %s ya existe!" % dst)
            return False
        shutil.copytree(src,dst)
        

    def applyPatch(self,src):
        self.iface.debug("applyPatch src=%s" % (src))
        flpatchdir.patch_folder_inplace(self.iface, src, self.dstpath)

def build_xml_file(iface, xmlfile):
    parser = etree.XMLParser(
                    ns_clean=False,
                    encoding="UTF-8",
                    remove_blank_text=True,
                    )
    bitree = etree.parse(xmlfile, parser)
    build_instructions = bitree.getroot()
    bi = BuildInstructions(iface, build_instructions)
    bi.execute()
    

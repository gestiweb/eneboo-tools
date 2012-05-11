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
        
    def execute(self, rebuild = True):
        if os.path.exists(self.dstpath):
            if rebuild == False: return True
            self.iface.info("Borrando carpeta %s . . . "  % self.dstpath)
            shutil.rmtree(self.dstpath)
        os.mkdir(self.dstpath)
        for instruction in self.instructions:
            if instruction.tag == "CopyFolderAction":
                self.copyFolder(**instruction.attrib)
            elif instruction.tag == "ApplyPatchAction":
                self.applyPatch(**instruction.attrib)
            elif instruction.tag == "CreatePatchAction":
                self.createPatch(**instruction.attrib)
            elif instruction.tag == "Message":
                self.message(**instruction.attrib)
            else:
                self.iface.warn("Accion %s desconocida" % instruction.tag)
    
    def message(self, text):
        self.iface.msg(text)
    
        
    def copyFolder(self,src,dst,create_dst=False):
        if create_dst == "yes": create_dst = True
        if create_dst == "no": create_dst = False
        self.iface.info("Copiando %s . . . " % (dst))
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
        self.iface.info("Aplicando parche (...)%s . . ." % (src[-64:]))
        flpatchdir.patch_folder_inplace(self.iface, src, self.dstpath)

    def createPatch(self,src,dst):
        self.iface.info("Creando parche (...)%s - (...)%s . . ." % (src[-48:],dst[-48:]))
        flpatchdir.diff_folder(self.iface, src, dst, self.dstpath, inplace = True)

def build_xml_file(iface, xmlfile, rebuild = True):
    parser = etree.XMLParser(
                    ns_clean=False,
                    encoding="UTF-8",
                    remove_blank_text=True,
                    )
    bitree = etree.parse(xmlfile, parser)
    build_instructions = bitree.getroot()
    bi = BuildInstructions(iface, build_instructions)
    bi.execute(rebuild)
    
def build_xml(iface, xml, rebuild = True):
    bi = BuildInstructions(iface, xml)
    bi.execute(rebuild)

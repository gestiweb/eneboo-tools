# encoding: UTF-8
import os
from lxml import etree
from enebootools.lib.utils import one, find_files, get_max_mtime, read_file_list

class BuildInstructions(object):
    def __init__(self, iface, instructions):
        self.instructions = instructions
        self.iface = iface
        print self.instructions.tag
        print self.instructions.attrib
        assert( self.instructions.tag in ["BuildInstructions"] )
        
    def execute(self):
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
        print "copyFolder", src, dst

    def applyPatch(self,src):
        print "ApplyPatch", src

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
    

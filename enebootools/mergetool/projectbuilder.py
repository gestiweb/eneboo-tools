# encoding: UTF-8
import os
from lxml import etree
from enebootools.lib.utils import one, find_files, get_max_mtime, read_file_list

class BuildInstructions(object):
    def __init__(self, iface, instructions):
        self.instructions = instructions
        self.iface = iface
        
    def execute(self):
        pass
        

def build_xml_file(iface, xmlfile):
    parser = etree.XMLParser(
                    ns_clean=False,
                    encoding="UTF-8",
                    remove_blank_text=True,
                    )
    bitree = etree.parse(xmlfile, parser)
    build_instructions = bitree.getroot()
    assert( build_instructions.tag in ["BuildInstructions"] )
    print build_instructions.tag
    print build_instructions.attrib
    

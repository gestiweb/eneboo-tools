# encoding: UTF-8
__version__ = "1.0.0"
__PROGRAM__NAME__ = "Eneboo Tools Packager"

import enebootools
from enebootools import EnebooToolsInterface
import sys, traceback

reload(sys)  
sys.setdefaultencoding('utf8')

from enebootools.packager import pkgjoiner, pkgsplitter


"""
    Packager es una utilidad para Eneboo que realiza paquetes al estilo 
    .eneboopkg o .abanq que luego el motor Eneboo puede leer y cargar
    
    Un paquete .eneboopkg es una serialización de ficheros que contiene los 
    módulos y ficheros a cargar en una base de datos. 

"""


class PackagerInterface(EnebooToolsInterface):
    module_description = u"Herramientas para empaquetar y desempaquetar ficheros .eneboopkg"
    def __init__(self, setup_parser = True):
        EnebooToolsInterface.__init__(self, False)
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        EnebooToolsInterface.setup_parser(self)

        self.create_action = self.parser.declare_action(
            name = "create",
            args = ["modulefolder"],
            options = [],
            description = u"Lee la carpeta $modulefolder, examina los módulos y los empaqueta",
            call_function = self.do_create,
            )
        self.create_action.set_help_arg(
            modulefolder = "Carpeta que leer para empaquetar su contenido",
            )                

        self.create_action = self.parser.declare_action(
            name = "unpack",
            args = ["packagefile"],
            options = [],
            description = u"Lee el fichero $packagefile y desempaqueta los módulos en una carpeta",
            call_function = self.do_unpack,
            )
        self.create_action.set_help_arg(
            packagefile = "Fichero que leer para extraer su contenido",
            )                
            

        self.split_action = self.parser.declare_action(
            name = "split",
            args = ["packagefile"],
            options = [],
            description = u"Lee el fichero $packagefile y genera una carpeta con su contenido",
            call_function = self.do_split,
            )
        self.split_action.set_help_arg(
            packagefile = "Fichero que leer para extraer su contenido",
            )                
            
        self.join_action = self.parser.declare_action(
            name = "join",
            args = ["packagefolder"],
            options = [],
            description = u"Lee la carpeta $packagefolder y genera un fichero empaquetando su contenido",
            call_function = self.do_join,
            )
        self.join_action.set_help_arg(
            packagefolder = "Carpeta que leer para empaquetar su contenido",
            )                
            
              
    # :::: ACTIONS ::::
    
    def do_create(self, modulefolder):
        try:
            return pkgjoiner.createpkg(self, modulefolder)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
    
    
    def do_unpack(self, packagefile):
        try:
            return pkgsplitter.unpackpkg(self, packagefile)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
    
    def do_split(self, packagefile):
        try:
            return pkgsplitter.splitpkg(self, packagefile)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
    
              
    def do_join(self, packagefolder):
        try:
            return pkgjoiner.joinpkg(self, packagefolder)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
    

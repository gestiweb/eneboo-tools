# encoding: UTF-8
from enebootools import EnebooToolsInterface

from enebootools.assembler import database as asmdb

class AssemblerInterface(EnebooToolsInterface):
    module_description = u"Herramientas de gestión de proyectos de mezcla"
    def __init__(self, setup_parser = True):
        EnebooToolsInterface.__init__(self, False)
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        EnebooToolsInterface.setup_parser(self)

        self.new_action = self.parser.declare_action(
            name = "new",
            args = ["subfoldername","description"],
            options = [],
            min_argcount = 0,
            description = u"Crea una nueva plantilla de funcionalidad",
            call_function = self.do_new,
            )

        self.new_action.set_help_arg(
            subfoldername = "Nombre de la subcarpeta que será creada. Debe seguir la plantilla extA999-codename.",
            description = "Nombre descriptivo para la funcionalidad",
            )
            
        self.build_action = self.parser.declare_action(
            name = "build",
            args = ["feat","target"],
            options = [],
            description = u"Construye el objetivo $target de la funcionalidad $feat",
            call_function = self.do_build,
            )
        self.build_action.set_help_arg(
            target = "Objetivo a construir",
            feat = "Funcionalidad a construir",
            )                
            
        
        self.save_fullpatch_action = self.parser.declare_action(
            name = "save-fullpatch",
            args = ["feat"],
            options = [],
            description = u"Para la funcionalidad $feat guarda los cambios como parche completo",
            call_function = self.do_save_fullpatch,
            )
        self.build_action.set_help_arg(
            feat = "Funcionalidad a construir",
            )                
            
        
        self.dbupdate_action = self.parser.declare_action(
            name = "dbupdate",
            args = [],
            options = [],
            description = u"Actualiza la base de datos de módulos y extensiones existentes",
            call_function = self.do_dbupdate,
            )
            
        self.list_objects_action = self.parser.declare_action(
            name = "list-objects",
            args = [],
            options = [],
            description = u"Lista los objetos (módulos y funcionalidades) en la base de datos",
            call_function = self.do_list_objects,
            )
            
        self.howto_build_action = self.parser.declare_action(
            name = "howto-build",
            args = ["feat","target"],
            options = [],
            description = u"Explica los pasos a seguir para construir el objetivo $target de la funcionalidad $feat",
            call_function = self.do_howto_build,
            )
        self.howto_build_action.set_help_arg(
            target = "Objetivo a construir",
            feat = "Funcionalidad a construir",
            )                
            
            
    # :::: ACTIONS ::::

    def do_dbupdate(self):
        try:
            return asmdb.update_database(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_list_objects(self):
        try:
            return asmdb.list_objects(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_howto_build(self, target, feat):
        try:
            return asmdb.do_howto_build(self,target, feat)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_build(self, target, feat):
        try:
            return asmdb.do_build(self,target, feat)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_save_fullpatch(self, feat):
        try:
            return asmdb.do_save_fullpatch(self, feat)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_new(self, subfoldername = None, description = None):
        try:
            return asmdb.do_new(self, subfoldername, description )
        except Exception,e:
            self.exception(type(e).__name__,str(e))




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




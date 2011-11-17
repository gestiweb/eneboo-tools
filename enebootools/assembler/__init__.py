# encoding: UTF-8
from enebootools import EnebooToolsInterface

from enebootools.assembler.database import update_database

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
            
    # :::: ACTIONS ::::

    def do_dbupdate(self):
        try:
            return update_database(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))




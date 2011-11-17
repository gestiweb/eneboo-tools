# encoding: UTF-8
from enebootools import EnebooToolsInterface


class AssemblerInterface(EnebooToolsInterface):
    module_description = u"Herramientas de gestión de proyectos de mezcla"
    def __init__(self, setup_parser = True):
        EnebooToolsInterface.__init__(self, False)
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        EnebooToolsInterface.setup_parser(self)
        
        self.update_action = self.parser.declare_action(
            name = "update",
            args = [],
            options = [],
            description = u"Actualiza la base de datos de módulos y extensiones existentes",
            call_function = self.do_update,
            )
            
    # :::: ACTIONS ::::

    def do_update(self):
        try:
            ret = False
            # TODO: Llamar aqui la funcion de reescaneo de directorios.
            return ret
        except Exception,e:
            self.exception(type(e).__name__,str(e))




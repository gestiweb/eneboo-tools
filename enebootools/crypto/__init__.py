# encoding: UTF-8
from enebootools import EnebooToolsInterface

from enebootools.crypto import main

class CryptoInterface(EnebooToolsInterface):
    module_description = u"Herramientas de criptografía"
    def __init__(self, setup_parser = True):
        EnebooToolsInterface.__init__(self, False)
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        EnebooToolsInterface.setup_parser(self)

        
        self.checksum_action = self.parser.declare_action(
            name = "checksum",
            args = ["module"],
            options = [],
            min_argcount = 1,
            description = u"Computa un fichero .checksum para un módulo",
            call_function = self.do_checksum,
            )

        self.checksum_action.set_help_arg(
            module = u"Fichero .mod a firmar"
            )

            
            
    # :::: ACTIONS ::::

    def do_checksum(self, module):
        try:
            return main.module_checksum(self, module)
        except Exception,e:
            self.exception(type(e).__name__,str(e))


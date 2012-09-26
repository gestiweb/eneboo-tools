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
            args = [],
            options = [],
            min_argcount = 0,
            description = u"Computa un fichero .checksum para un módulo",
            call_function = self.do_checksum,
            )

        self.addcert_action = self.parser.declare_action(
            name = "addcert",
            args = ["pemfile"],
            options = [],
            min_argcount = 1,
            description = u"Agrega un certificado en formato PEM a la lista de certificados",
            call_function = self.do_addcert,
            )
            
        self.addsignature_action = self.parser.declare_action(
            name = "addsignature",
            args = ["pkcs12"],
            options = [],
            min_argcount = 1,
            description = u"Agrega una firma a la lista de firmas usando un fichero pkcs12 para leer certificado y clave privada",
            call_function = self.do_addsignature,
            )
            
            
    # :::: ACTIONS ::::

    def do_checksum(self):
        try:
            return main.module_checksum(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_addcert(self, pemfile):
        try:
            return main.add_certificate(self,pemfile)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_addsignature(self, pkcs12):
        try:
            return main.add_signature(self,pkcs12)
        except Exception,e:
            self.exception(type(e).__name__,str(e))


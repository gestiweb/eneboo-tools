# encoding: UTF-8
from enebootools import EnebooToolsInterface

from enebootools.crypto import main
import sys  

reload(sys)  
sys.setdefaultencoding('utf8')


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
        self.addcert_action.set_help_arg(
            pemfile = "Certificado que agregar a la lista de certificados",
            )                
            
        self.addsignature_action = self.parser.declare_action(
            name = "sign",
            args = ["certpem", "pkeypem"],
            options = [],
            min_argcount = 2,
            description = u"Agrega una firma a la lista de firmas usando un fichero PEM para leer certificado y otro para la clave privada",
            call_function = self.do_addsignature,
            )
            
        self.addsignature_action.set_help_arg(
            certpem = "Certificado para usar en la firma",
            pkeypem = "Clave privada para usar en la firma",
            )          
                  
        self.check_action = self.parser.declare_action(
            name = "check",
            args = [],
            options = [],
            min_argcount = 0,
            description = u"Realiza comprobaciones varias sobre las firmas existentes",
            call_function = self.do_check,
            )
            
                  
            
    # :::: ACTIONS ::::

    def do_checksum(self):
        try:
            return main.module_checksum(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_check(self):
        try:
            return main.check(self)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_addcert(self, pemfile):
        try:
            return main.add_certificate(self,pemfile)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_addsignature(self,certpem,pkeypem):
        try:
            return main.add_signature(self,certpem,pkeypem)
        except Exception,e:
            self.exception(type(e).__name__,str(e))


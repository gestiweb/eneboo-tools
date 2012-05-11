# encoding: UTF-8
import sys, traceback
import enebootools.parseargs as pa

output_encoding = sys.stdout.encoding
if output_encoding is None: 
    import codecs
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)
    output_encoding = "UTF-8"

def ustr(x):
    if type(x) is str: return x
    if type(x) is unicode: return x.encode("UTF-8","replace")
    return str(x)
    

def myprint(*args):
    txt = " ".join(args)+"\n"
    sys.stdout.write(unicode(txt,"UTF-8"))
    

class EnebooToolsInterface(object):
    module_description = u"Descripción genérica"
    def __init__(self, setup_parser = True):
        self.action_chain = None
        self.parser = None
        self.verbosity = 0
        self.output_file_name = "STDOUT"
        self.output = sys.stdout
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        self.parser = pa.ArgParser(
                description = self.module_description,
                )    
        self.parser.declare_option(
            name = "output-file",
            aliases = [ "output" ], # sinonimos con los que llamar la opcion
            description = u"guarda la salida del programa en PATH",
            level = "action", # ( action | parser )
            variable = "PATH", # determina el nombre de la variable en la ayuda.
                        # si es None, no hay variable. Esto fuerza también la sintaxis.
            call_function = self.set_output_file
            )
        self.parser.declare_option(
            name = "verbose",
            short = "vV", # opción corta relacionada (si se usa, no puede haber variable)
            description = u"Aumenta la cantidad de mensajes",
            level = "parser", # ( action | parser )
            # variable = None  # es omisible, porque None es por defecto.
            call_function = self.set_verbose
            )
        self.parser.declare_option(
            name = "quiet",
            short = "q", 
            description = u"Disminuye la cantidad de mensajes",
            level = "parser",
            call_function = self.set_quiet
            )
            
                
    def parse_args(self, argv = None):
        self.action_chain = self.parser.parse_args(argv)
        self.filename_list = self.parser.parse.files
        if self.action_chain is None: return False
        else: return True
    
    def execute_actions(self):
        # Action chain es la cadena de llamadas. Es una lista que contiene:
        # [
        #  .. (function1_ptr ,  *args, **kwargs),
        #  .. (function2_ptr ,  *args, **kwargs),
        # ]
        # Se lanzan en orden.
        if self.action_chain is None:
            print "Hubo un error al leer los argumentos y no se puede realizar la acción."
            return 
        for function, args, kwargs in self.action_chain:
            if self.verbosity > 4: print "DEBUG:", function, args, kwargs
            ret = function(*args, **kwargs)
            if ret: return ret
        
        self.action_chain = []
              
    def set_output_file(self, filename):
        self.output_file_name = filename
        self.output = open(filename, "w")

    def set_verbose(self):
        self.verbosity += 1
    
    def set_quiet(self):
        self.verbosity -= 1
    
    def debug2r(self, variable = None, **kwargs):
        if self.verbosity < 4: return
        from pprint import pformat
        if variable is not None: kwargs['var'] = variable
        print "DEBUG+",
        for arg, var in sorted(kwargs.items()):
            prefix = ": %s =" % arg
            print prefix, 
            try: lines = pformat(var).splitlines()
            except UnicodeEncodeError: 
                lines = ["UNICODE ENCODE ERROR"]
            for n,line in enumerate(lines):
                if n > 0: print " "*(len(prefix)+0), 
                print line,
                if n < len(lines)-1: print
        print
                

    def debug2(self, text):
        if self.verbosity < 4: return
        text = ustr(text)
        myprint("DEBUG+:", text)    

    def debug(self, text):
        if self.verbosity < 3: return
        text = ustr(text)
        myprint("DEBUG:", text)    
    
    def info2(self, text):
        if self.verbosity < 2: return
        text = ustr(text)
        myprint("INFO:", text)    
    
    def info(self, text):
        if self.verbosity < 1: return
        text = ustr(text)
        myprint(":", text)    
    
    def msg(self, text):
        if self.verbosity < 0: return
        text = ustr(text)
        myprint(text)    
    
    def warn(self, text):
        if self.verbosity < -1: return
        text = ustr(text)
        myprint("WARN:", text)    
    
    def error(self, text):
        if self.verbosity < -2: return
        text = ustr(text)
        myprint("ERROR:", text)    
        
    def critical(self, text):
        if self.verbosity < -3: return
        text = ustr(text)
        myprint("CRITICAL:", text)    
        
    def exception(self, errtype, text=""):
        if self.verbosity < -3: return
        text = ustr(text)
        txt_exc = traceback.format_exc()
        
        myprint("UNEXPECTED ERROR %s:" % errtype, text)
        myprint(txt_exc)
            
            

# **** CONFIGURACION *****
import os.path, os

USER_HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(USER_HOME,".eneboo-tools")

if not os.path.exists(CONF_DIR):
    os.mkdir(CONF_DIR)
    



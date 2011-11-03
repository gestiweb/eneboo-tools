# encoding: UTF-8
import enebootools
from enebootools import EnebooToolsInterface
import enebootools.parseargs as pa
import sys, traceback

from enebootools.mergetool import flpatchqs

"""
    El receptor de las llamadas del parser es una clase. Cada opción
    activada, genera una llamada en una función de la clase y así va 
    configurando la clase con cada llamada consecutiva.
    
    Esta clase está a nivel de módulo (mergetool) y es la interfaz
    de conexión de un módulo a otro.
    
    Una opción --output-file generara una llamada a una función miembro 
    "self.set_output_file(value)", donde "value" sería el valor recibido por
    la opción. 
    
    En el caso de que la opción no lleve valor, se ejecuta la función sin 
    argumentos.
    
    Las opciones cortas se configuran unicamente como alias de opciones 
    largas, de ese modo aprovechamos la configuración de unas cosas para otras.
    Y además, forzamos a que toda opción corta tenga su correspondiente opción 
    larga.
    
    Las acciones serán ejecutadas al final, y se les pasará los parámetros
    indicados con kwargs, de modo que el orden de los parámetros en la función
    es irrelevante, pero deben contar con el mismo nombre. 

    Las listas de ficheros se inicializan en el primer paso recibiendo el 
    array de ficheros, probablemente con una llamada a set_file_list.

    La ejecución de las acciones es prearada en el parse() pero no se ejecutan
    hasta la llamada de una segunda funcion execute_actions() para evitar 
    sobrecargar la pila de llamadas (y que cuando se lance un traceback sea 
    lo más sencillo posible).
    
    NOTAS: 
     * Los parámetros pueden llegar a ser omisibles?
        en tal caso o se omiten los últimos o tiene que poder darles nombre 
        o tiene que haber un argumento de exclusión como "-".
        
     * Múltiples acciones realizadas por ejecución?
        Si los parámetros de la acción se consumen se podría entender que se 
        inicia otra acción o concatenar mediante un separador. Esto generaría 
        problemas y es posible que no sea práctico para ningún caso. Es 
        posible reciclar opciones y parámetros de llamada entre acciones?
        ... de momento se provee de una interfaz interna para esto, pero no se
        va a usar.
    
     * Habrá que agregar un control de excepciones en las llamadas de cada 
        función, para intentar buscar errores en la propia llamada (funcion no 
        existe, argumentos no válidos... etc)
    
"""


class MergeToolInterface(EnebooToolsInterface):
    module_description = u"Herramientas para la ayuda de resolución de conflictos de mezcla"
    def __init__(self, setup_parser = True):
        self.action_chain = None
        self.parser = None
        self.verbosity = 0
        self.output_file_name = "STDOUT"
        self.output = sys.stdout
        self.patch_qs_rewrite = "abort"
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
            name = "patch-qs-rewrite",
            description = u"indica si al aplicar un parche de QS se debe sobreescribir o no las clases existentes ( yes / warn / no / abort ) ",
            level = "action",
            variable = "VALUE", 
            call_function = self.set_patch_qs_rewrite
            )
        self.parser.declare_option(
            name = "verbose",
            short = "vV", # opción corta relacionada (si se usa, no puede haber variable)
            description = u"Activa el modo charlatán",
            level = "parser", # ( action | parser )
            # variable = None  # es omisible, porque None es por defecto.
            call_function = self.set_verbose
            )
        self.parser.declare_option(
            name = "quiet",
            short = "q", 
            description = u"Disminuye la cantidad de avisos",
            level = "parser",
            call_function = self.set_quiet
            )

        self.file_diff_action = self.parser.declare_action(
            name = "file-diff",
            args = ["ext","base","final"],
            description = u"Genera un parche de fichero $ext de la diferencia entre el fichero $base y $final",
            options = ['output-file'],
            call_function = self.do_file_diff,
            min_file_list = 0, # por defecto es 0
            max_file_list = 0, # por defecto es 0, -1 indica sin límite.
            min_argcount = -1  # cantidad de argumentos obligatorios. por defecto -1
            )
        self.file_diff_action.set_help_arg(
            ext = "Tipo de fichero a procesar: QS / XML",
            base = "Fichero original",
            final = "Fichero final",
            )                
        self.file_patch_action = self.parser.declare_action( 
            name = "file-patch",
            args = ["ext","patch","base"],
            description = u"Aplica un parche de fichero $ext especificado por $patch al fichero $base",
            options = ['output-file','patch-qs-rewrite'],
            call_function = self.do_file_patch,
            )
        self.file_patch_action.set_help_arg(
            ext = "Tipo de fichero a procesar: QS / XML",
            base = "Fichero original",
            patch = "Parche a aplicar sobre $base",
            )
        self.file_check_action = self.parser.declare_action( 
            name = "file-check",
            args = ["check","filename"],
            description = u"Analiza un fichero $filename en busca de errores usando el algoritmo de comprobación $check",
            options = [],
            call_function = self.do_file_check,
            )
        self.file_check_action.set_help_arg(
            ext = "Tipo de análisis a realizar: qs-classes / ...",
            filename = "Fichero a analizar",
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
        
    def set_patch_qs_rewrite(self, value):
        if value not in ['yes','no','warn','abort']: raise ValueError
        self.patch_qs_rewrite = value
    
    def set_verbose(self):
        self.verbosity += 1
    
    def set_quiet(self):
        self.verbosity -= 1
    
    def debug2r(self, variable = None, **kwargs):
        if self.verbosity < 4: return
        from pprint import pformat
        if variable is not None: kwargs['var'] = variable
        
        for arg, var in sorted(kwargs.items()):
            prefix = "DEBUG+: %s =" % arg
            print prefix, 
            for n,line in enumerate(pformat(var).splitlines()):
                if n > 0: print " "*(len(prefix)+0), 
                print line
                

    def debug2(self, text):
        if self.verbosity < 4: return
        print "DEBUG+:", text    

    def debug(self, text):
        if self.verbosity < 3: return
        print "DEBUG:", text    
    
    def info2(self, text):
        if self.verbosity < 2: return
        print "INFO:", text    
    
    def info(self, text):
        if self.verbosity < 1: return
        print ":", text    
    
    def msg(self, text):
        if self.verbosity < 0: return
        print text    
    
    def warn(self, text):
        if self.verbosity < -1: return
        print "WARN:", text    
    
    def error(self, text):
        if self.verbosity < -2: return
        print "ERROR:", text    
        
    def critical(self, text):
        if self.verbosity < -3: return
        print "CRITICAL:", text    
        
    def exception(self, errtype, text=""):
        if self.verbosity < -3: return
        print
        print "UNEXPECTED ERROR %s:" % errtype, text    
        print traceback.format_exc()
    
    # :::: ACTIONS ::::
    
    def do_file_diff(self, ext, base, final):
        try:
            ext = str(ext).upper()
            if ext == 'QS': return flpatchqs.diff_qs(self,base,final)
            print "Unknown $ext %s" % (repr(ext))
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_file_patch(self, ext, base, patch):
        try:
            ext = str(ext).upper()
            if ext == 'QS': return flpatchqs.patch_qs(self,base,patch)
            print "Unknown $ext %s" % (repr(ext))
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_file_check(self, check, filename):
        try:
            check = str(check).lower() 
            if check == 'qs-classes': return flpatchqs.check_qs_classes(self,filename)
            print "Unknown $check %s" % (repr(check))
        except Exception,e:
            self.exception(type(e).__name__,str(e))

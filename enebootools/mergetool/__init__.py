# encoding: UTF-8
import enebootools
from enebootools import EnebooToolsInterface
import sys, traceback

from enebootools.mergetool import flpatchqs, flpatchxml, flpatchlxml, flpatchdir, projectbuilder

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
        EnebooToolsInterface.__init__(self, False)
        self.patch_qs_rewrite = "warn"
        self.patch_xml_style_name = "legacy1"
        self.diff_xml_search_move = False
        self.patch_name = None
        if setup_parser: self.setup_parser()
        
    def setup_parser(self):
        EnebooToolsInterface.setup_parser(self)
        self.parser.declare_option(
            name = "patch-qs-rewrite",
            description = u"indica si al aplicar un parche de QS se debe sobreescribir o no las clases existentes ( reverse / predelete / yes / warn / no / abort ) ",
            level = "action",
            variable = "VALUE", 
            call_function = self.set_patch_qs_rewrite
            )
        self.parser.declare_option(
            name = "patch-name",
            description = u"Indica el nombre del parche que se usará en lugar de autodetectarlo.",
            level = "action",
            variable = "NAME", 
            call_function = self.set_patch_name
            )
        self.parser.declare_option(
            name = "enable-diff-xml-search-move",
            description = u"Activa la búsqueda de movimientos de bloques XML. Puede ser un poco más lento y puede generar parches incompatibles con otras herramientas.",
            level = "action",
            call_function = self.enable_diff_xml_search_move
            )
        self.parser.declare_option(
            name = "patch-xml-style",
            description = u"Usar otro estilo para generar parches (ver mergetools/etc/patch-styles/)",
            variable = "NAME", 
            level = "action",
            call_function = self.set_patch_xml_style
            )
            
        self.build_project_action = self.parser.declare_action(
            name = "build-project",
            args = ["buildxml"],
            options = [],
            description = u"Lee el fichero $buildxml y realiza las operaciones que se determinan",
            call_function = self.do_build_project,
            )
        self.build_project_action.set_help_arg(
            buildxml = "Fichero del que leer las instrucciones",
            )                
            
        self.folder_diff_action = self.parser.declare_action(
            name = "folder-diff",
            args = ["patchdir","basedir","finaldir"],
            options = ["patch-name"],
            description = u"Genera en $patchdir una colección de parches de la diferencia entre las carpetas $basedir y $finaldir",
            call_function = self.do_folder_diff,
            )
        self.folder_diff_action.set_help_arg(
            patchdir = "Carpeta donde guardar las diferencias",
            basedir = "Carpeta a leer como referencia",
            finaldir = "Carpeta a comparar",
            )                
            
        self.folder_patch_action = self.parser.declare_action(
            name = "folder-patch",
            args = ["patchdir","basedir","finaldir"],
            options = ["patch-name"],
            description = u"Aplica los parches en $patchdir a la carpeta $basedir y genera $finaldir",
            call_function = self.do_folder_patch,
            )
        self.folder_patch_action.set_help_arg(
            patchdir = "Carpeta donde leer las diferencias",
            basedir = "Carpeta a leer como referencia",
            finaldir = "Carpeta a aplicar los cambios",
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
            options = ['output-file','patch-qs-rewrite',"enable-diff-xml-search-move","patch-xml-style"],
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
        self.qs_extract_action = self.parser.declare_action(
            name = "qs-extract",
            args = ["final","classlist"],
            description = u"Extrae del fichero $final las clases indicadas en $classlist",
            options = ['output-file'],
            call_function = self.do_qs_extract,
            )
        self.qs_extract_action.set_help_arg(
            final = "Fichero QS que contiene las clases a extraer",
            classlist = "Lista de clases a extraer, separadas por coma y sin espacios: class1,class2,...",
            )                
              
        self.qs_split_action = self.parser.declare_action(
            name = "qs-split",
            args = ["final"],
            description = u"Separa el fichero $final en subficheros en una carpeta",
            options = [],
            call_function = self.do_qs_split,
            )
        self.qs_split_action.set_help_arg(
            final = "Fichero QS",
            )                
              
        self.qs_join_action = self.parser.declare_action(
            name = "qs-join",
            args = ["folder"],
            description = u"Une la carpeta $folder en un fichero",
            options = [],
            call_function = self.do_qs_join,
            )
        self.qs_join_action.set_help_arg(
            folder = "Carpeta con los subficheros QS",
            )                
              
    def set_patch_name(self, name):
        if name == "": name = None
        self.patch_name = name
        
    def set_patch_xml_style(self, name):
        self.patch_xml_style_name = name
        
    def set_patch_qs_rewrite(self, value):
        if value not in ['reverse','predelete','yes','no','warn','abort']: raise ValueError
        self.patch_qs_rewrite = value

    def enable_diff_xml_search_move(self):
        self.diff_xml_search_move = True
    
    # :::: ACTIONS ::::
    def do_build_project(self, buildxml):
        try:
            return projectbuilder.build_xml_file(self, buildxml)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
    
    def do_folder_diff(self, basedir, finaldir, patchdir):
        try:
            return flpatchdir.diff_folder(self, basedir, finaldir, patchdir)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_folder_patch(self, basedir, finaldir, patchdir):
        try:
            return flpatchdir.patch_folder(self, basedir, finaldir, patchdir)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    
    def do_file_diff(self, ext, base, final):
        try:
            ext = str(ext).upper()
            if ext == 'QS': return flpatchqs.diff_qs(self,base,final)
            if ext == 'QSDIR': return flpatchqs.diff_qs_dir(self,base,final)
            #if ext == 'XML': return flpatchxml.diff_xml(self,base,final)
            if ext == 'XML': return flpatchlxml.diff_lxml(self,base,final)
            print "Unknown $ext %s" % (repr(ext))
        except Exception,e:
            self.exception(type(e).__name__,str(e))

    def do_file_patch(self, ext, base, patch):
        try:
            ext = str(ext).upper()
            if ext == 'QS': return flpatchqs.patch_qs(self,base,patch)
            if ext == 'QSDIR': return flpatchqs.patch_qs_dir(self,base,patch)
            if ext == 'XML': return flpatchlxml.patch_lxml(self,patch,base)
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
            
    def do_qs_extract(self, final, classlist):
        try:
            return flpatchqs.extract_classes_qs(self,final, classlist)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
            
    def do_qs_split(self, final):
        try:
            return flpatchqs.split_qs(self,final)
        except Exception,e:
            self.exception(type(e).__name__,str(e))
            
    def do_qs_join(self, folder):
        try:
            return flpatchqs.join_qs(self,folder)
        except Exception,e:
            self.exception(type(e).__name__,str(e))

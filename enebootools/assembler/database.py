# encoding: UTF-8
import os
import os.path
import sqlite3
import re

from lxml import etree

from enebootools import CONF_DIR
from enebootools.assembler.config import cfg
from enebootools.lib.utils import one, find_files, get_max_mtime
import enebootools.lib.peewee as peewee
from enebootools.mergetool import projectbuilder
from enebootools.mergetool import MergeToolInterface    


from databasemodels import KnownObjects

from mypeewee import transactional
from kobjects import ObjectIndex

class Database(object):
    def __init__(self, filename):
        self.db = None
        self.dbtree = None
        self.dbfile = filename
    
    def ready(self):
        return bool(self.db)
        
    def setup(self):
        self.db = peewee.SqliteDatabase(self.dbfile)
        self.db.execute("PRAGMA synchronous = 1;")
        KnownObjects.setup(database.db)

    def init(self):
        if not database.ready():
            self.setup()
        
    def get_database(self):
        return self.db

database = Database(os.path.join(CONF_DIR, "assembler-database.sqlite"))


def init_database():
    global database
    database.init()
    return database



@transactional(database)
def update_database(iface):
    from datetime import datetime
    iface.info(u"Actualizando base de datos de módulos y funcionalidades . . . ")
    KnownObjects.delete().execute() # -- Borrar todos los objetos
    module_root = {}
    for path in cfg.module.modulefolders:
        if not os.path.exists(path):
            iface.debug(u"Se ignora directorio inexistente %s" % repr(path))
            continue
        modules = find_files(path,"*.mod", True)
        if not modules:
            iface.warn(u"Directorio no contiene módulos %s" % repr(path))
            continue
        iface.info(u"Se encontraron %d modulos en la carpeta %s" % (len(modules), repr(path)))
        for module in modules:
            iface.debug(u"Módulo %s" % module)
            mtime = get_max_mtime(path,module)
            dmtime = datetime.fromtimestamp(mtime)
            obj = KnownObjects()
            obj.objtype = "module"
            obj.abspath = path
            obj.relpath = os.path.dirname(module)
            obj.filename = os.path.basename(module)
            obj.timestamp = int(mtime)
            obj.extradata = ""
            obj.save()
            
            # print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
        module_root[path] = modules

    feature_root = {}
    for path in cfg.module.featurefolders:
        if not os.path.exists(path):
            iface.debug(u"Se ignora directorio inexistente %s" % repr(path))
            continue
        features = find_files(path,"*.feature.ini", True)
        if not features:
            iface.warn("Directorio no contiene funcionalidades %s" % repr(path))
            continue
        iface.info(u"Se encontraron %d funcionalidades en la carpeta %s" % (len(features), repr(path)))
        for feature in features:
            iface.debug(u"Funcionalidad %s" % feature)
            mtime = get_max_mtime(path,feature)
            dmtime = datetime.fromtimestamp(mtime)
            # print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
            obj = KnownObjects()
            obj.objtype = "feature"
            obj.abspath = path
            obj.relpath = os.path.dirname(feature)
            obj.filename = os.path.basename(feature)
            obj.timestamp = int(mtime)
            obj.extradata = ""
            obj.save()
        
        feature_root[path] = features


def list_objects(iface):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    iface.msg(u"\nMódulos cargados:")
    for obj in oi.modules():
        iface.msg(u" - %s" % obj.formal_name())

    iface.msg(u"\nFuncionalidades cargadas:")
    for obj in oi.features():
        iface.msg(u" - %s" % obj.formal_name())

def do_howto_build(iface,target, feat):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    build_instructions = oi.get_build_actions(target,feat)
    if build_instructions is None:
        iface.error("Error al buscar %s -> %s" % (feat,target))
        return False
    iface.info("Acciones para compilar funcionalidad %s %s:" % (feat, target))
    iface.msg(etree.tostring(build_instructions, pretty_print=True))
    buildpath = os.path.join(build_instructions.get("path"), "build")
    if not os.path.exists(buildpath):
        os.mkdir(buildpath)
    dstfile = os.path.join(buildpath, "%s.build.xml" % target)
    build_instructions.getroottree().write(dstfile, pretty_print=True)
    
    

def is_target_built(iface, target, feat):
    # TODO: Revisar si $target.build.xml existe
    # TODO: Si existe, preguntar a mergetool si cree que está construido.
    return False # Asumir que nunca una dependencia está cumplida

def do_build(iface,target, feat, rebuild=True, dstfolder = None):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    build_instructions = oi.get_build_actions(target,feat,dstfolder)
    if build_instructions is None: 
        iface.error("Error al generar las instrucciones de compilado.")
        return False
    buildpath = os.path.join(build_instructions.get("path"), "build")
    if not os.path.exists(buildpath):
        os.mkdir(buildpath)
    dstfile = os.path.join(buildpath, "%s.build.xml" % target)
    build_instructions.getroottree().write(dstfile, pretty_print=True)
    depends = build_instructions.get("depends", "").split(" ")
    if depends:
        for dep in depends: 
            dep = dep.strip()
            if dep == "": continue
            if not is_target_built(iface, dep, feat):
                # Si tiene una dependencia, y no está cumplida, recompilarla:
                do_build(iface, dep, feat, rebuild = False)
                
    mtool_iface = MergeToolInterface()
    mtool_iface.verbosity = iface.verbosity
    projectbuilder.build_xml(mtool_iface,build_instructions,rebuild)
    
def uinput(question):
    import sys
    text= raw_input(unicode(question).encode(sys.stdout.encoding)).decode(sys.stdin.encoding)
    return text

def uinput_mask(question, mask, errortext = None):
    if errortext is None:
        errortext = u"El valor '%s' no es válido"
    while True:
        text = uinput(question)
        m1 = re.search(mask,text)
        if m1:
            return text,m1
        else:
            print errortext % text
    
    
def do_save_fullpatch(iface, feat):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    patchname = oi.get_patch_name(feat, default = True)
    patch_folder = os.path.join("patches", patchname)
    do_build(iface, target = "fullpatch", feat = feat, rebuild = True, dstfolder = patch_folder)
    oi.set_patch_name(feat, patchname)
    
def select_option(title, options, answers, question = None, errortext = None, default = None, accept_invalid = False):
    if question is None:
        question = u"Seleccione una opción: "
    if errortext is None:
        errortext = u"El valor '%s' no es una opción válida"
    print title
    answers = answers[:len(options)]
    for answer, option in zip(answers,options):
        print u"    %s) %s" % (answer, option)
    def ask():
        answer = uinput(question).lower()
        if answer == "": answer = default
        if answer not in answers: 
            print errortext % answer
            return None
        return answer
    answer = None
    while answer is None: 
        answer = ask()
        if answer is None:
            if accept_invalid:
                return None, None
    
    return answer, options[answers.index(answer)]

def do_new(iface):
    letters = list("abcdefghijklmnopqrstuvwxyz123456789")
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    
    # SELECCIONAR CARPETA DONDE SE GUARDARA:
    folders = []
    for path in cfg.module.featurefolders:
        if not os.path.exists(path):
            iface.debug(u"Se ignora directorio inexistente %s" % repr(path))
            continue
        folders.append(path)
    if len(folders) == 0:
        iface.error("No hay carpetas válidas donde guardar extensiones. Imposible continuar.")
        return False
    fpath = None
    def change_fpath():
        print
        if len(folders) == 1:
            fpath = folders[0]
            print u"La funcionalidad se guardará en la única carpeta válida: '%s'" % fpath
        else:
            a,fpath = select_option( 
                    title = u"Existen varias carpetas de funcionalidades:", 
                    question = u"Seleccione en qué carpeta desea crear la nueva funcionalidad: ", 
                    options = folders,
                    answers = letters,
                    )
        return fpath
    fpath = change_fpath()
    
    ftype_options = [u"extensión",u"proyecto", u"conjunto de extensiones"]
    ftype_answers = ["ext","prj","set"]
    ftype_idx = dict(zip(ftype_answers,ftype_options))
    def change_ftype():
        print
        ftype,o = select_option( 
                title = u"Qué tipo de funcionalidad va a crear?", 
                question = u"Seleccione una opción: ", 
                options = ftype_options,
                answers = ftype_answers,
                )
        return ftype
    ftype = change_ftype()
    
    def change_fcode():
        print
        t,m = uinput_mask(
                    question = u"Código para la nueva funcionalidad: ",
                    mask = r"^([A-Z0-9]\d{3})$", 
                    errortext = u"ERROR: El valor '%s' debe seguir el formato A999 (A puede ser número).",
                    )
        fcode = m.group(0)
        return fcode
    fcode = change_fcode()
    
    def change_fname():    
        print
        t,m = uinput_mask(
                    question = u"Nombre corto de funcionalidad: ",
                    mask = r"^([a-z][a-z0-9_]{3,15})$", 
                    errortext = u"ERROR: El valor '%s' debe tener entre 4 y 16 carácteres, ser minúsculas y tener solo letras y números (empezando siempre por letra)",
                    )
        fname = m.group(0)
        return fname
    fname = change_fname()
    
    def change_fdesc():
        print
        fdesc = uinput(u"Descripción de la funcionalidad: ")
        return fdesc
    fdesc = change_fdesc()
    
    fdep_modules = []
    fdep_features = []
    fload_patch = None
    while True:
        fdstpath = os.path.join(fpath,"%s%s-%s" % (ftype, fcode, fname))
        print
        print u"**** Asistente de creación de nueva funcionalidad ****"
        print 
        print u" : Carpeta destino : %s" % fdstpath
        print u" : Nombre          : %s - %s - %s " % (ftype_idx[ftype], fcode, fname)
        print u" : Descripción     : %s " % (fdesc)
        print
        print u" : Dependencias    : %d módulos, %d funcionalidades" % (len(fdep_modules),fdep_features)
        print u" : Importar Parche : %s" % (fload_patch)
        print
        menu1_options = []
        menu1_answers = []
        menu1_options += [ u"Cambiar datos básicos"]
        menu1_answers += [ "c" ]
        menu1_options += [ u"Dependencias", u"Importar parche", u"Eliminar parche" ]
        menu1_answers += [ "d"           , "i"                , "e"]
        menu1_options += [ u"Aceptar y crear", u"Cancelar y Salir" ]
        menu1_answers += [ "a"              , "q" ]
        a1,o1 = select_option( 
                title = u"--  Menú de opciones generales --", 
                question = u"Seleccione una opción: ", 
                options = menu1_options,
                answers = menu1_answers,
                )
        if a1 == "i":
            t,m = uinput_mask(
                        question = u"Ruta hasta el parche: ",
                        mask = r"^([\w-./]+)$", 
                        errortext = u"ERROR: El valor debe ser una ruta válida",
                        )
            fload_patch = t
            
        if a1 == "e":
            fload_patch = e
                
        if a1 == "d":
            print
            print "Dependencias..."
                
        if a1 == "c":
            menu2_options = []
            menu2_answers = []
            kvs = menu2_answers, menu2_options
            def agregar_opcion2(kvs, k,v):
                ks, vs = kvs
                ks += [ k ]
                vs += [ v ]
            agregar_opcion2(kvs, "0", u"Seleccionar una carpeta diferente")
            agregar_opcion2(kvs, "1", u"Cambiar tipo de funcionalidad")
            agregar_opcion2(kvs, "2", u"Cambiar código")
            agregar_opcion2(kvs, "3", u"Cambiar nombre")
            agregar_opcion2(kvs, "4", u"Cambiar descripción")
            agregar_opcion2(kvs, "q", u"Finalizar edición")
            while True:
                print
                print u"**** Cambiar datos básicos ****"
                print 
                print u" : Carpeta : %s" % fpath
                print u" : Tipo    : %s (%s) " % (ftype_idx[ftype],ftype)
                print u" : Código  : %s" % (fcode)
                print u" : Nombre  : %s" % (fname)
                print u" : Descr.  : %s " % (fdesc)
                print
                a2,o2 = select_option( 
                        title = u"--  Menú de datos básicos --", 
                        question = u"Seleccione una opción: ", 
                        options = menu2_options,
                        answers = menu2_answers,
                        )
                if a2 == "0":
                    fpath = change_fpath()
                if a2 == "1":
                    ftype = change_ftype()
                if a2 == "2":
                    fcode = change_fcode()
                if a2 == "3":
                    fname = change_fname()
                if a2 == "4":
                    fdesc = change_fdesc()
                if a2 == "q":
                    break
            continue
            
        if a1 == "a": 
            print
            print u"Guardando ... "
            break
        if a1 == "q": 
            print u"Se ha cancelado la operación."
            break
        

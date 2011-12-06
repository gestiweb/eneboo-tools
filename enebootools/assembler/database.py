# encoding: UTF-8
import os
import os.path
import sqlite3
import re
import readline, fnmatch
import shutil

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
    
def uinput(question, possible_values = None):
    import sys
    if isinstance(possible_values, list):
        completer1.enable_value_completer(possible_values)
    elif isinstance(possible_values, basestring):       
        if possible_values == "os.path":
            completer1.enable_path_completer()
    text= raw_input(unicode(question).encode(sys.stdout.encoding)).decode(sys.stdin.encoding)
    completer1.disable_completer()
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
    
def select_option(title, options, answers, question = None, errortext = None, default = "", accept_invalid = False, callback = None):
    if question is None:
        question = u"Seleccione una opción: "
    if errortext is None:
        errortext = u"El valor '%s' no es una opción válida"
    print title
    answers = answers[:len(options)]
    for answer, option in zip(answers,options):
        print u"    %s) %s" % (answer, option)
    def ask():
        answer = uinput(question, possible_values = answers).lower()
        if answer == "": answer = default
        answerlist = [ x.strip() for x in answer.split(" ") if x.strip() ]
        for answer in answerlist:
            if answer not in answers: 
                print errortext % answer
                return []
        return answerlist
    answerlist = []
    while len(answerlist) == 0: 
        answerlist = ask()
        if len(answerlist) == 0:
            if accept_invalid:
                return None, None
        elif len(answerlist) > 1 and callback is None:
            print u"No se acepta más de una respuesta."
            answerlist[:] = []
        
    if callback:
        for answer in answerlist:
            try:
                callback(answer, options[answers.index(answer)])
            except Exception, e:
                print e
    else:
        answer = answerlist[0]
        return answer, options[answers.index(answer)]


class MyCompleter(object):
    def __init__(self):
        self.possible_complete_values = []
        self.last_search_text = None
        self.last_matchlist = None

    def set_complete_values(self,valuelist):
        self.last_search_text = None
        self.last_matchlist = None
        self.possible_complete_values[:] = valuelist
        
    def enable_value_completer(self, valuelist):
        readline.set_completer(None)
        readline.set_completer(completer1.value_completer)
        readline.set_completer_delims(", ")
        readline.parse_and_bind('tab: menu-complete')
        self.set_complete_values(valuelist)
        
    def enable_path_completer(self):
        readline.set_completer(None)
        readline.set_completer(completer1.path_completer)
        readline.set_completer_delims("")
        readline.parse_and_bind('tab: menu-complete')
        self.set_complete_values([])
        
    def disable_completer(self):
        readline.set_completer(None)
        self.set_complete_values([])
    
    def value_completer(self,text, state):
        try:
            manual = False
            if '*' not in text:
                text = "*" + text + "*"
            else:
                manual = True
            if text == self.last_search_text:
                matches = self.last_matchlist
            else:
                matches = fnmatch.filter(self.possible_complete_values, text) 
                self.last_matchlist = matches
                self.last_search_text = text
            if manual:
                if state == 0:
                    return " ".join(matches)
                else:
                    return
                
            try:
                return matches[state]
            except IndexError:
                return None
        except Exception,e:
            print e
            
    def path_completer(self,text, state):
        return None # <- por defecto hace ya lo que queremos 
            
completer1 = MyCompleter()


def do_new(iface, subfoldername = None, description = None, patchurl = None):
    letters = list("abcdefghijklmnopqrstuvwxyz123456789")
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    fpath = ftype = fcode = fname = fdesc = None
    if description: fdesc = description
    if subfoldername:
        match = re.match("^([a-z]+)([A-Z0-9][0-9]{3})-([a-z][a-z0-9]{3,12})$", subfoldername)
        if not match:
            print "El nombre de subcarpeta '%s' no es válido" % subfoldername
            return False
        ftype, fcode, fname = match.groups()
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
    fpath = folders[-1]
    
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
        
    if ftype is None: ftype = change_ftype()
    
    def change_fcode():
        print
        t,m = uinput_mask(
                    question = u"Código para la nueva funcionalidad: ",
                    mask = r"^([A-Z0-9]\d{3})$", 
                    errortext = u"ERROR: El valor '%s' debe seguir el formato A999 (A puede ser número).",
                    )
        fcode = m.group(0)
        return fcode
    if fcode is None: fcode = change_fcode()
    
    def change_fname():    
        print
        t,m = uinput_mask(
                    question = u"Nombre corto de funcionalidad: ",
                    mask = r"^([a-z][a-z0-9_]{3,15})$", 
                    errortext = u"ERROR: El valor '%s' debe tener entre 4 y 16 carácteres, ser minúsculas y tener solo letras y números (empezando siempre por letra)",
                    )
        fname = m.group(0)
        return fname
    if fname is None: fname = change_fname()
    
    def change_fdesc():
        print
        fdesc = uinput(u"Descripción de la funcionalidad: ")
        return fdesc
    if fdesc is None: fdesc = change_fdesc()
    
    def change_fload_patch():
        t,m = uinput_mask(
                question = u"Ruta hasta el parche: ",
                mask = r"^([\w./-]*)$", 
                errortext = u"ERROR: El valor '%s' debe ser una ruta válida",
                )
        if os.path.exists(t):
            return t
        else:
            print "ERROR: La ruta '%s' no existe." % t
            return None
        

    
    fdep_modules = []
    fdep_features = []
    fload_patch = patchurl
    def checkpatch_deps(fload_patch):
        file_index = oi.index_by_file()
        from enebootools.mergetool.flpatchdir import FolderApplyPatch
        fpatch = FolderApplyPatch(iface, fload_patch)
        info = fpatch.get_patch_info()
        for filename in info["requires"]:
            if filename not in file_index:
                print "??? Dependencia no encontrada para:", filename
                continue
            modules = file_index[filename]["provided-by-module"]
            features = file_index[filename]["provided-by-feature"]
            for m in modules:
                if m not in fdep_modules:
                    fdep_modules.append(m)
                    print u"Se agregó automáticamente la dependencia con el módulo '%s'" % m
            for f in features:
                if f not in fdep_features:
                    fdep_features.append(f)
                    print u"Se agregó automáticamente la dependencia con la funcionalidad '%s'" % f
    
    if fload_patch:
        checkpatch_deps(fload_patch)
    
    while True:
        fdstpath = os.path.join(fpath,"%s%s-%s" % (ftype, fcode, fname))
        print
        print u"**** Asistente de creación de nueva funcionalidad ****"
        print 
        print u" : Carpeta destino : %s" % fdstpath
        print u" : Nombre          : %s - %s - %s " % (ftype_idx[ftype], fcode, fname)
        print u" : Descripción     : %s " % (fdesc)
        print
        print u" : Dependencias    : %d módulos, %d funcionalidades" % (len(fdep_modules),len(fdep_features))
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
            fload_patch = change_fload_patch()
            if fload_patch:
                checkpatch_deps(fload_patch)
        if a1 == "e":
            fload_patch = None
                
        if a1 == "d":
            menu2_options = []
            menu2_answers = []
            kvs = menu2_answers, menu2_options
            def agregar_opcion2(kvs, k,v):
                ks, vs = kvs
                ks += [ k ]
                vs += [ v ]
            agregar_opcion2(kvs, "+m", u"Agregar módulo")
            agregar_opcion2(kvs, "-m", u"Eliminar módulo")
            agregar_opcion2(kvs, "+f", u"Agregar funcionalidad")
            agregar_opcion2(kvs, "-f", u"Eliminar funcionalidad")
            agregar_opcion2(kvs, "q", u"Finalizar edición")
            while True:
                print
                print u"**** Dependencias ****"
                print 
                print u" : Módulos :"
                for d in fdep_modules:
                    print u"    - %s" % d
                print
                print u" : Funcionalidades :"
                for d in fdep_features:
                    print u"    - %s" % d
                print
                a2,o2 = select_option( 
                        title = u"--  Menú de dependencias --", 
                        question = u"Seleccione una opción: ", 
                        options = menu2_options,
                        answers = menu2_answers,
                        )
                if a2 == "+m":
                    # Agregar dependencia modulo
                    k1 = []
                    v1 = []
                    for module in oi.modules():
                        k, v = module.code or module.name, module.formal_name()
                        if v in fdep_modules: continue
                        k1.append(k)
                        v1.append(v)
                        
                    select_option( 
                            title = u"--  Agregar dependencia de módulo --", 
                            question = u"Seleccione un módulo: ", 
                            answers = k1,
                            options = v1,
                            accept_invalid = True,
                            callback = lambda a,o: fdep_modules.append(o),
                            )
                    
                if a2 == "-m":
                    # Eliminar dependencia modulo
                    k1 = []
                    v1 = []
                    for module in oi.modules():
                        k, v = module.code or module.name, module.formal_name()
                        if v not in fdep_modules: continue
                        k1.append(k)
                        v1.append(v)
                    select_option( 
                            title = u"--  Eliminar dependencia de módulo --", 
                            question = u"Seleccione un módulo: ", 
                            answers = k1,
                            options = v1,
                            accept_invalid = True,
                            callback = lambda a,o: fdep_modules.remove(o),
                            )
                if a2 == "+f":
                    # Agregar dependencia funcionalidad
                    k1 = []
                    v1 = []
                    for feature in oi.features():
                        k, v = feature.code or feature.name, feature.formal_name()
                        if v in fdep_features: continue
                        k1.append(k)
                        v1.append(v)
                        
                    select_option( 
                            title = u"--  Agregar dependencia de funcionalidad --", 
                            question = u"Seleccione una funcionalidad: ", 
                            answers = k1,
                            options = v1,
                            accept_invalid = True,
                            callback = lambda a,o: fdep_features.append(o),
                            )
                if a2 == "-f":
                    # Eliminar dependencia funcionalidad
                    k1 = []
                    v1 = []
                    for feature in oi.features():
                        k, v = feature.code or feature.name, feature.formal_name()
                        if v not in fdep_features: continue
                        k1.append(k)
                        v1.append(v)
                        
                    select_option( 
                            title = u"--  Eliminar dependencia de funcionalidad --", 
                            question = u"Seleccione una funcionalidad: ", 
                            answers = k1,
                            options = v1,
                            accept_invalid = True,
                            callback = lambda a,o: fdep_features.remove(o),
                            )
                if a2 == "q":
                    break
                
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
            
            # GUARDAR AQUI
            create_new_feature(
                path = fdstpath,
                fcode = fcode,
                fname = fname,
                ftype = ftype,
                fdesc = fdesc,
                fdep_modules = fdep_modules,
                fdep_features = fdep_features,
                fload_patch = fload_patch,
                )
            print
            break
        if a1 == "q": 
            print
            print u"Se ha cancelado la operación."
            print
            break
        
def create_new_feature(path, fcode, fname, ftype, fdesc, fdep_modules, fdep_features, fload_patch):
    
    os.mkdir(path)
    f_ini = open(os.path.join(path, "%s.feature.ini" % fname),"w")
    f_ini.write("[feature]\n")
    f_ini.write("type=%s\n" % ftype)
    f_ini.write("code=%s\n" % fcode)
    f_ini.write("name=%s\n" % fname)
    f_ini.write("description=%s\n" % fdesc)
    f_ini.write("\n")
    f_ini.close()
    patchespath = os.path.join(path, "patches")
    os.mkdir(patchespath)

    confpath = os.path.join(path, "conf")
    os.mkdir(confpath)
    
    f_patch = open(os.path.join(confpath, "patch_series"),"w")
    patch_dstpath = None
    if fload_patch:
        if fload_patch.endswith("/"):
            fload_patch = fload_patch[:-1]
        basename = os.path.basename(fload_patch)
        f_patch.write("%s\n" % basename)
        patch_dstpath = os.path.join(patchespath, basename)
        shutil.copytree(fload_patch,patch_dstpath,
            ignore=shutil.ignore_patterns('*.pyc', 'tmp*', '.*'))
    else:
        f_patch_readme = open(os.path.join(patchespath, "README"), "w")
        f_patch_readme.write("""
        Esta carpeta es donde se deben ubicar los parches. Este fichero sirve
        únicamente para que los VCS como GIT guarden la carpeta al existir al
        menos un fichero en ella.
        \n""")
        f_patch_readme.close()
        
    f_patch.write("\n")
    f_patch.close()
    
    f_req_mod = open(os.path.join(confpath, "required_modules"),"w")
    for mod in fdep_modules:
        f_req_mod.write("%s\n" % mod)
    
    f_req_mod.write("\n")
    f_req_mod.close()
    
    f_req_feat = open(os.path.join(confpath, "required_features"),"w")
    for feat in fdep_features:
        f_req_feat.write("%s\n" % feat)
    
    f_req_feat.write("\n")
    f_req_feat.close()
    

    return

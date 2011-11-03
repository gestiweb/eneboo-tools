# encoding: UTF-8
u"""
    Módulo de cálculo y aplicación de parches emulando flpatch.
"""
"""
    -----
    Hay que anotar de algún modo cuando parcheamos una clase, qué clase 
    estábamos buscando. Esto servirá para que la próxima clase que busque esa
    misma, en su lugar herede de la nuestra y así preservar el correcto orden
    de aplicación.
    
    Ejemplo:
    
    class jasper extends num_serie /** %from: oficial */ {
    
    
    Aunque pueda parecer información excesiva, es normal, porque genera un 
    arbol 1->N y da la información exacta de la extensión/mezcla al usuario
    final.
    
"""

import re, os.path

def qsclass_reader(iface, file_name, file_lines):
    linelist = []
    classes = []
    declidx = {}
    defidx = {}
    iface = None
    for n,line in enumerate(file_lines):
        m = re.search("/\*\*\s*@(\w+)\s+(\w+)?\s*\*/", line)
        if m:
            dtype = m.group(1)
            cname = m.group(2)
            npos = len(linelist)
            if dtype == "class_declaration":
                if cname in classes:
                    iface.error(u"Redefinición de la clase %s (file: %s)" % (cname,file_name))
                else:
                    classes.append(cname)
                    declidx[cname] = npos
            elif dtype == "class_definition":
                defidx[cname] = npos
            elif dtype == "file":
                # el tipo @file no lo gestionamos
                pass 
            else:
                iface.warn(u"Tipo de identificador doxygen no reconocido %s (file: %s)" % (repr(dtype),file_name))
                continue
                
            found = [ dtype , cname, n ]
            if len(linelist): 
                linelist[-1].append(n) 
            linelist.append(found)
        # const iface = new ifaceCtx( this );
        m = re.search("(const|var)\s+iface\s*=\s*new\s*(?P<classname>\w+)\(\s*this\s*\);?", line) 
        if m:
            iface = {
                'block' : len(linelist) - 1,
                'classname' : m.group('classname'),
                'line' : n,
                'text' : m.group(0),
            }

    linelist[-1].append(len(file_lines)) 
    classlist = {
        "decl" : declidx,
        "def" : defidx,
        "classes" : classes,
        "list" : linelist,
        "iface" : iface
        }
    return classlist
    
        
def extract_class_decl_info(iface,text_lines):
    linelist = []
    for n,line in enumerate(text_lines):
        m = re.search("class\s+(?P<cname>\w+)(\s+extends\s+(?P<cbase>\w+))?(\s+/\*\*\s+%from:\s+(?P<cfrom>\w+)\s+\*/)?",line)
        if m:
            match = m.group(0)
            class_name = m.group("cname")
            class_basename = m.group("cbase")
            class_fromname = m.group("cfrom")
            linelist.append( [match, class_name, class_basename, class_fromname, n] )
            
    return linelist

    

def file_reader(filename):
    try:
        f1 = open(filename, "r")
    except IOError,e: 
        iface.error("File Not Found: %s" % repr(filename))
        return
    name = os.path.basename(filename)
    return name, [line.rstrip() for line in f1.readlines()]
    

def diff_qs(iface, base, final):
    iface.debug(u"Procesando Diff QS $base:%s -> $final:%s" % (base, final))
    nbase, flbase = file_reader(base)
    nfinal, flfinal = file_reader(final)
    if flbase is None or flfinal is None:
        iface.info(u"Abortando Diff QS por error al abrir los ficheros")
        return
    clbase = qsclass_reader(iface, base, flbase)
    clfinal = qsclass_reader(iface, final, flfinal)
    created_classes_s = list(set(clfinal['classes']) - set(clbase['classes']))
    deleted_classes = list(set(clbase['classes']) - set(clfinal['classes']))
    # Mantener el orden en que se encontraron:
    created_classes = [ clname for clname in clfinal['classes'] if clname in created_classes_s ]
    
    if len(created_classes) == 0:
        iface.warn(u"No se han detectado clases nuevas. El parche quedará vacío. ($final:%s)" % (final))
        
    if len(deleted_classes) > 0:
        iface.warn(u"Se han borrado clases. Este cambio no se registrará en el parche. ($final:%s)" % (final))
        
    iface.debug2r(created = created_classes, deleted = deleted_classes)
    iface.output.write("\n")
    
    for clname in created_classes:
        block_decl = clfinal['decl'].get(clname,None)
        if block_decl is None:
            iface.error(u"Se esperaba una declaración de clase para %s." % clname)
            continue
        dtype, clname, idx1, idx2 = clfinal['list'][block_decl]
        iface.debug2r(exported_block=clfinal['list'][block_decl])
        lines = flfinal[idx1:idx2]
        text = "\n".join(lines) 
        iface.output.write(text)
        
    iface.output.write("\n")
    
    for clname in created_classes:
        block_def = clfinal['def'].get(clname,None)
        if block_def is None:
            iface.warn(u"Se esperaba una definición de clase para %s." % clname)
            continue
        dtype, clname, idx1, idx2 = clfinal['list'][block_def]
        iface.debug2r(exported_block=clfinal['list'][block_def])
        lines = flfinal[idx1:idx2]
        text = "\n".join(lines) 
        iface.output.write(text)
        

def check_qs_classes(iface, base):
    iface.debug(u"Comprobando clases del fichero QS $filename:%s" % (base))
    nbase, flbase = file_reader(base)
    if flbase is None:
        iface.info(u"Abortando comprobación por error al abrir los ficheros")
        return
    clbase = qsclass_reader(iface, base, flbase)
    clbase['classinfo'] = extract_class_decl_info(iface, flbase)
    
    iface.debug2r(clbase=clbase)
    
    
    
    
    
def patch_qs(iface, base, patch):
    iface.debug(u"Procesando Patch QS $base:%s + $patch:%s" % (base, patch))
    nbase, flbase = file_reader(base)
    npatch, flpatch = file_reader(patch)
    if flbase is None or flpatch is None:
        iface.info(u"Abortando Patch QS por error al abrir los ficheros")
        return
    
    
    
    


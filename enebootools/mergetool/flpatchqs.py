# encoding: UTF-8
u"""
    Módulo de cálculo y aplicación de parches QS emulando flpatch.
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

import re, os.path, difflib

def latin1_to_ascii (unicrap):
    """This replaces UNICODE Latin-1 characters with
    something equivalent in 7-bit ASCII. All characters in the standard
    7-bit ASCII range are preserved. In the 8th bit range all the Latin-1
    accented letters are stripped of their accents. Most symbol characters
    are converted to something meaningful. Anything not converted is deleted.
    """
    xlate = {
        0xc0:'A', 0xc1:'A', 0xc2:'A', 0xc3:'A', 0xc4:'A', 0xc5:'A',
        0xc6:'Ae', 0xc7:'C',
        0xc8:'E', 0xc9:'E', 0xca:'E', 0xcb:'E',
        0xcc:'I', 0xcd:'I', 0xce:'I', 0xcf:'I',
        0xd0:'Th', 0xd1:'N',
        0xd2:'O', 0xd3:'O', 0xd4:'O', 0xd5:'O', 0xd6:'O', 0xd8:'O',
        0xd9:'U', 0xda:'U', 0xdb:'U', 0xdc:'U',
        0xdd:'Y', 0xde:'th', 0xdf:'ss',
        0xe0:'a', 0xe1:'a', 0xe2:'a', 0xe3:'a', 0xe4:'a', 0xe5:'a',
        0xe6:'ae', 0xe7:'c',
        0xe8:'e', 0xe9:'e', 0xea:'e', 0xeb:'e',
        0xec:'i', 0xed:'i', 0xee:'i', 0xef:'i',
        0xf0:'th', 0xf1:'n',
        0xf2:'o', 0xf3:'o', 0xf4:'o', 0xf5:'o', 0xf6:'o', 0xf8:'o',
        0xf9:'u', 0xfa:'u', 0xfb:'u', 0xfc:'u',
        0xfd:'y', 0xfe:'th', 0xff:'y',
        0xa1:'!', 0xa2:'{cent}', 0xa3:'{pound}', 0xa4:'{currency}',
        0xa5:'{yen}', 0xa6:'|', 0xa7:'{section}', 0xa8:'{umlaut}',
        0xa9:'{C}', 0xaa:'{^a}', 0xab:'<<', 0xac:'{not}',
        0xad:'-', 0xae:'{R}', 0xaf:'_', 0xb0:'{degrees}',
        0xb1:'{+/-}', 0xb2:'{^2}', 0xb3:'{^3}', 0xb4:"'",
        0xb5:'{micro}', 0xb6:'{paragraph}', 0xb7:'*', 0xb8:'{cedilla}',
        0xb9:'{^1}', 0xba:'{^o}', 0xbb:'>>',
        0xbc:'{1/4}', 0xbd:'{1/2}', 0xbe:'{3/4}', 0xbf:'?',
        0xd7:'*', 0xf7:'/'
    }

    r = ''
    for i in unicrap:
        if xlate.has_key(ord(i)):
            r += xlate[ord(i)]
        elif ord(i) >= 0x80:
            pass
        else:
            r += i
    return r


def qsclass_reader(iface, file_name, file_lines):
    linelist = []
    classes = []
    delclasses = []
    declidx = {}
    defidx = {}
    iface_n = None
    for n,line in enumerate(file_lines):
        line2 = latin1_to_ascii(line)
        m = re.search("/\*\*?\s*@(\w+)\s+([^ */]+)?\s*\*/", line2)
        if m:
        
            m2 = re.search("^\s*/\*\* @(\w+)( \w+)?\s*\*/\s*$", line)
            if not m2:
                iface.warn("Formato incorrecto de la linea %s" % repr(line))
            dtype = m.group(1)
            cname = m.group(2)
                
            npos = len(linelist)
            if dtype == "class_declaration":
                classdecl = extract_class_decl_info(iface, file_lines[n:n+12])
                if cname not in classdecl:
                    iface.error(u"Bloque 'class_declaration' con nombre erroneo clase %s no existe en el bloque (file: %s)" % (cname,file_name))
                    
                if cname in classes:
                    iface.error(u"Hay dos bloques 'class_declaration' para la clase %s (file: %s)" % (cname,file_name))
                else:
                    classes.append(cname)
                    declidx[cname] = npos
            elif dtype == "class_definition":
                if cname in defidx:
                    iface.error(u"Hay dos bloques 'class_definition' para la clase %s (file: %s)" % (cname,file_name))
                else:
                    defidx[cname] = npos
                    if cname not in classes:
                        iface.error(u"Bloque 'class_definition' huérfano para la clase %s (file: %s)" % (cname,file_name))
            elif dtype == "delete_class":
                # Clase a borrar cuando se aplique el parche.
                if cname in delclasses:
                    iface.error(u"Hay dos bloques 'delete_class' para la clase %s (file: %s)" % (cname,file_name))
                else:
                    delclasses.append(cname)
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
            iface_n = {
                'block' : len(linelist) - 1,
                'classname' : m.group('classname'),
                'line' : n,
                'text' : m.group(0),
            }
    if linelist:
        linelist[-1].append(len(file_lines)) 
        
    classlist = {
        "decl" : declidx,
        "def" : defidx,
        "classes" : classes,
        "delclasses" : delclasses,
        "list" : linelist,
        "iface" : iface_n
        }
    return classlist
    
        
def extract_class_decl_info(iface,text_lines):
    classdict = {}
    for n,line in enumerate(text_lines):
        m = re.search("class\s+(?P<cname>\w+)(\s+extends\s+(?P<cbase>\w+))?(\s+/\*\*\s+%from:\s+(?P<cfrom>\w+)\s+\*/)?",line)
        if m:
            cname = m.group("cname")
            classdict[cname] = {
                'name' : cname,
                'extends' : m.group("cbase"),
                'from' : m.group("cfrom"),
                'text': m.group(0),
                'line' : n,
                }
    return classdict

    

def file_reader(filename):
    try:
        f1 = open(filename, "r")
    except IOError,e: 
        raise ValueError("File Not Found: %s" % repr(filename))
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
    
    if len(created_classes) == 0 and len(deleted_classes) == 0:
        iface.warn(u"No se han detectado clases nuevas ni viejas. El parche quedará vacío. ($final:%s)" % (final))
        return -1
        
    iface.debug2r(created = created_classes, deleted = deleted_classes)
    return extract_classes(iface,clfinal,flfinal,created_classes, deleted_classes)

def extract_classes_qs(iface, final, classlist):
    if isinstance(classlist, basestring):
        classlist = classlist.split(",")
    iface.debug(u"Extrayendo clases QS $final:%s $classlist:%s" % (final,",".join(classlist)))
    nfinal, flfinal = file_reader(final)
    if flfinal is None:
        iface.info(u"Abortando por error al abrir los ficheros")
        return
    clfinal = qsclass_reader(iface, final, flfinal)

    if len(classlist) == 0:
        iface.warn(u"No se han pasado clases. El parche quedará vacío. ($final:%s)" % (final))
        
    return extract_classes(iface,clfinal,flfinal,classlist)
    
def split_qs_old(iface, final):
    iface.debug(u"Separando fichero QS %s . . . " % (final))
    nfinal, flfinal = file_reader(final)
    if flfinal is None:
        iface.info(u"Abortando por error al abrir los ficheros")
        return
    flfinal = [ line.replace("\t","        ") for line in flfinal ]
    clfinal = qsclass_reader(iface, final, flfinal)
    nameroot, ext = os.path.splitext(final)
    dstfolder = nameroot+"-splitted"
    
    try: os.mkdir(dstfolder)
    except OSError: pass
    f1 = open(os.path.join(dstfolder,"index"),"w")
    f1.write("header\n")
    
    f2 = open(os.path.join(dstfolder,"header"),"w")
    stype, clname, line1, linen = clfinal['list'][0]
    f2.write("\n".join(flfinal[:line1]) + "\n")
    f2.close()
    parent_class = None
    for item in clfinal['list']:
        stype, clname, line1, linen = item
        name = "%s-%s" % (str(stype).lower(), str(clname).lower())
        
        f1.write("%s\n" % name)
        f2 = open(os.path.join(dstfolder,name),"w")
        text = "\n".join(flfinal[line1:linen]) + "\n"
        if stype == "class_declaration" and parent_class:
            text = text.replace(parent_class, "{$parent_class}")
            
        f2.write(text)
        f2.close()
        parent_class = clname
        
        
    f1.write("tail\n")
    f2 = open(os.path.join(dstfolder,"tail"),"w")
    stype, clname, line1, linen = clfinal['list'][-1]
    f2.write("\n".join(flfinal[linen:]) + "\n")
    f2.close()
        
    
def split_qs(iface, final):
    iface.debug(u"Separando fichero QS %s . . . " % (final))
    nfinal, flfinal = file_reader(final)
    if flfinal is None:
        iface.info(u"Abortando por error al abrir los ficheros")
        return
    flfinal = [ line.replace("\t","        ") for line in flfinal ]
    clfinal = qsclass_reader(iface, final, flfinal)
    cdfinal = extract_class_decl_info(iface, flfinal) 
    nameroot, ext = os.path.splitext(final)
    dstfolder = nameroot+"-splitted"
    
    try: os.mkdir(dstfolder)
    except OSError: pass
    
    if clfinal['iface']: 
        line = clfinal['iface']['line']
        flfinal[line] = ""
    
    f1 = open(os.path.join(dstfolder,"patch_series"),"w")
    for n,classname in enumerate(clfinal['classes']):
        if n > 0:
            fix_class(iface, flfinal, clfinal, cdfinal, classname, set_extends = "PARENT_CLASS", set_from = None)
    
        f1.write(classname + "\n")
        f2 = open(os.path.join(dstfolder,classname + ".qs"),"w")
        if n == 0:
            stype, clname, line1, linen = clfinal['list'][0]
            f2.write("\n".join(flfinal[:line1]) + "\n")
            if stype == "file":
                f2.write("\n".join(flfinal[line1:linen]) + "\n")
        nblock1 = clfinal['decl'].get(classname)
        if nblock1:
            stype, clname, line1, linen = clfinal['list'][nblock1]
            f2.write("\n".join(flfinal[line1:linen]) + "\n")
    
        nblock2 = clfinal['def'].get(classname)
        if nblock2:
            stype, clname, line1, linen = clfinal['list'][nblock2]
            f2.write("\n".join(flfinal[line1:linen]) + "\n")
    
        if n == 0:
            stype, clname, line1, linen = clfinal['list'][-1]
            f2.write("\n".join(flfinal[linen:]) + "\n")
     
        f2.close()
        
    f1.close()
    
        

class PatchReader(object):
    def __init__(self, iface, folder, cname, parent_class, last_class):
        self.iface = iface
        self.last_class = last_class
        self.folder = folder
        self.cname = cname
        self.parent_class = parent_class
        self.filename = os.path.join(folder,cname + ".qs")
        self.name, self.file = file_reader(self.filename)
        if self.file is None:
            iface.info(u"Abortando por error al abrir los ficheros")
            return
        self.classes = qsclass_reader(iface, self.filename, self.file)
        self.classdict = extract_class_decl_info(iface, self.file) 
        if parent_class:
            fix_class(iface, self.file, self.classes, self.classdict, cname, set_extends = parent_class)
        if self.classes['iface']: 
            line = self.classes['iface']['line']
            self.file[line] = ""
            #fix_iface(self.iface, self.file, self.classes, self.last_class)
    
    def write_head(self, f2):
        stype, clname, line1, linen = self.classes['list'][0]
        f2.write("\n".join(self.file[:line1]) + "\n")
        if stype == "file":
            f2.write("\n".join(self.file[line1:linen]) + "\n")
    
    def write_tail(self, f2):
        stype, clname, line1, linen = self.classes['list'][-1]
        f2.write("\n".join(self.file[linen:]) + "\n")
        
    def write_decl(self, f2):
        for classname, nblock1 in self.classes['decl'].items():
            stype, clname, line1, linen = self.classes['list'][nblock1]
            f2.write("\n".join(self.file[line1:linen]) + "\n")
            
    def write_def(self, f2):
        for classname, nblock1 in self.classes['def'].items():
            stype, clname, line1, linen = self.classes['list'][nblock1]
            f2.write("\n".join(self.file[line1:linen]) + "\n")
            
    

def join_qs(iface, dstfolder):
    head, foldername = os.path.split(dstfolder)
    filename = foldername.replace("-splitted",".joined") + ".qs"
    filepath = os.path.join(head,filename)
    iface.debug(u"Uniendo carpeta %s . . . " % (dstfolder))
    f1 = open(os.path.join(dstfolder,"patch_series"))
    classlist = [ cname.strip() for cname in f1 if len(cname.strip()) ]
    f1.close()
    
    patch = {}
    parent_class = None
    p_iface = None
    for cname in classlist:
        patch[cname] = PatchReader(iface,dstfolder,cname,parent_class,classlist[-1])
        parent_class = cname
        

    f1 = open(filepath, "w")
    p0 = patch[classlist[0]]
    p0.write_head(f1)
    
    for cname in classlist:
        p = patch[cname]
        p.write_decl(f1)
    f1.write("const iface = new %s( this );\n\n" % classlist[-1])
    
    for cname in classlist:
        p = patch[cname]
        p.write_def(f1)
        
    p0.write_tail(f1)
    f1.close()
    iface.info(u"El fichero %s ha sido escrito correctamente." % (filepath))
        
    
    
def patch_qs_dir(iface, base, patch):
    iface.debug(u"Procesando Patch sobre carpeta QS $base:%s + $patch:%s" % (base, patch))
    f1 = open(patch)
    section = None
    subsection = None
    sections = {}
    seclist = []
    for line in f1:
        if line[-1] == "\n": line = line[:-1]
        code = line[:2]
        text = line[2:]
        if code == "@@":
            name = text.strip()
            nameidx = name.find(" ")
            if nameidx > 0:
                section, subsection = name[:nameidx], name[nameidx+1:]
            else:
                section = name
                subsection = None
            if section not in sections:
                sections[section] = {}
            if subsection not in sections[section]:
                sections[section][subsection] = []
            else:
                iface.error("Sección '@@%s' redeclarada" % name) 
            seclist.append((section, subsection))
            continue
        if code == "..":
            section = None
            continue
        if section:
            sections[section][subsection].append( (code, text) )
    patch_series = [ cl.strip() for cl in open(os.path.join(base,"patch_series")) if cl.strip() != "" ]
    patch_series_orig = patch_series[:]

    sec_rmcls = sections.get("remove-classes")
    if sec_rmcls:
        iface.error("TODO: Remove Classes")
        for code, line in sec_rmcls[None]:
            if code == "- ": 
                try: patch_series.remove(line)
                except ValueError: iface.warn(u"La clase %s iba a ser eliminada del fichero, pero no la encontramos")

    sec_mvcls = sections.get("move-classes")
    if sec_mvcls:
        for code, line in sec_mvcls[None]:
            line = line.strip()
            if len(line) == 0: continue
            match = re.match("^([\w,]+) \((\w+)\) ([\w,]+)", line)
            if not match:
                iface.error(u"Línea de movimiento de clases malformada: %s" % (repr(line)))
                continue
            group1, relation, group2 = match.groups()
            if relation not in ['before']:
                iface.error(u"Línea de movimiento con relación desconocida: %s" % (repr(relation)))
                continue
            group1 = group1.split(",")
            group2 = group2.split(",")
            for cl in group1:
                try: idx = patch_series.index(cl)
                except ValueError: 
                    iface.warn("La clase %s iba a ser movida antes de %s pero la primera no existe" % (cl,cl_from))
                    continue

                for cl_from in group2:
                    try: idx_from = patch_series.index(cl_from)
                    except ValueError: 
                        iface.warn("La clase %s iba a ser movida antes de %s pero la segunda no existe" % (cl,cl_from))
                        continue

                    if relation == "before":
                        if idx > idx_from:
                            patch_series[:] = patch_series[:idx_from] + [patch_series[idx]] + patch_series[idx_from:idx] + patch_series[idx+1:]
                            idx = patch_series.index(cl)
                    
            #print code, ":", line
            
            
    sec_addcls = sections.get("add-classes")
    if sec_addcls:
        iface.error("TODO: Add Classes")
        known_cls = []
        to_add = []
        for code, line in sec_addcls[None]:
            line = line.strip()
            if line == "": continue
            if code == "  ":
                if line in patch_series:
                    known_cls.append(line)
            if code == "+ ":
                if line in patch_series:
                    iface.error(u"TODO: Add Classes -  Clase %s ya existía" % line)
                    continue
                
                known_cls.append(line)
                to_add.append(line)
                
        print known_cls
        print to_add

    print patch_series_orig
    print patch_series
            
    sec_patchcls = sections.get("patch-class")
    if sec_patchcls:
        for cls, list1 in sec_patchcls.items():
            iface.error("TODO: Patch Class %s" % cls)
            for code, line in list1[:1]:
                print code, ":", line
            
            
    sec_addedcls = sections.get("added-class")
    if sec_addedcls:
        for cls, list1 in sec_patchcls.items():
            iface.error("TODO: Added Class %s" % cls)
            for code, line in list1[:1]:
                print code, ":", line
            
                    
            
        
        
        
    
def diff_qs_dir(iface, base, final):
    iface.debug(u"Procesando Diff de carpetas QS $base:%s -> $final:%s" % (base, final))
    
    iface.debug(u"Comparando clases en patch_series . . .")
    f1 = open(os.path.join(base,"patch_series"))
    classlist1 = [ cname.strip() for cname in f1 if len(cname.strip()) ]
    f1.close()
    f1 = open(os.path.join(final,"patch_series"))
    classlist2 = [ cname.strip() for cname in f1 if len(cname.strip()) ]
    f1.close()
    classlist1a = classlist1[:]
    classlist2a = classlist2[:]
    
    clases_eliminadas = [ c for c in classlist1 if c not in classlist2 ]
    clases_agregadas = [ c for c in classlist2 if c not in classlist1 ]
    # El sentido de la operación debe ser:
    # 1.- Eliminar clases 
    # 2.- Mover clases
    # 3.- Parchear clases
    # 4.- Agregar clases
    if clases_eliminadas: 
        iface.debug("Clases eliminadas: " + ", ".join(clases_eliminadas))
        iface.output.write("@@remove-classes\n")
        for cls in classlist1:
            if cls in clases_eliminadas: code = "- "
            else: code = "  "
            iface.output.write("%s%s\n" % (code,cls))
        iface.output.write("..\n")
        
    for c in clases_eliminadas: classlist1a.remove(c)
    for c in clases_agregadas: classlist2a.remove(c)
    
    assert(len(classlist1a) == len(classlist2a))
    for n1,(a,b) in enumerate(zip(classlist1a,classlist2a)):
        if a != b: break
    for n2,(a,b) in reversed(list(enumerate(zip(classlist1a,classlist2a)))):
        if a != b: break
    # classlist1b y classlist2b mantienen el listado de clases discrepantes.
    classlist1b,classlist2b = classlist1a[n1:n2+1],classlist2a[n1:n2+1]
    classlist1b_n = [ classlist2b.index(c) for c in classlist1b ]
    
    move_actions = get_move_actions(classlist1b_n,classlist2b)
    if move_actions:
        iface.output.write("@@move-classes\n")
        for move_action in move_actions:
            iface.debug("Clases movidas: " + repr(move_action))
            cl2move, relation, clctx = move_action
            iface.output.write("  %s (%s) %s\n" % (",".join(cl2move),relation,",".join(clctx)))
        iface.output.write("..\n")
        
    if clases_agregadas: 
        iface.debug("Clases agregadas: " + ", ".join(clases_agregadas))
        iface.output.write("@@add-classes\n")
        for cls in classlist2:
            if cls in clases_agregadas: code = "+ "
            else: code = "  "
            iface.output.write("%s%s\n" % (code,cls))
        iface.output.write("..\n")


    
    clases_comunes = [ c for c in classlist2 if c in classlist1 ]
    
    for cls in clases_comunes:
        file1 = list(open(os.path.join(base,cls + ".qs")))
        file2 = list(open(os.path.join(final,cls + ".qs")))
        diff = list(difflib.ndiff(file1, file2))
        changed_lines = [ (n,line) for n,line in enumerate(diff) if line[0:2] not in ['  '] and len(line[1:].rstrip())>1 ]
        if changed_lines:
            iface.debug(" ##### FICHERO %s.qs #####" % cls)
            iface.output.write("@@patch-class %s\n" % cls)
            unprinted_lines = list(range(len(diff)))
            for n,ld in changed_lines:
                if n not in unprinted_lines: continue
                idx = unprinted_lines.index(n)
                prev_lines, post_lines = unprinted_lines[:idx] , unprinted_lines[idx+1:]
                if len(prev_lines) > 3:
                    for j in reversed(prev_lines):
                        if re.search("^\s*(function|class) ",diff[j]): break
                    omitted = len(prev_lines[:prev_lines.index(j)])
                    if omitted > 5: iface.output.write("== %d lines ==\n" % omitted)
                    else:
                        for k in prev_lines[:prev_lines.index(j)]:
                            iface.output.write(diff[k])
                    for k in prev_lines[prev_lines.index(j):]:
                        iface.output.write(diff[k])
                else:
                    for k in prev_lines:
                        iface.output.write(diff[k])
                unprinted_lines[:idx+1] = []
                iface.output.write(diff[n])

                post_lines = [ x for x in unprinted_lines if x > n ]
                end = False
                count = 0
                for b in post_lines:
                    if re.search("function",diff[b]): 
                        end = True
                    if end and count > 1: break
                    
                    iface.output.write(diff[b])
                    unprinted_lines.remove(b)
                    if diff[b][0:2] == "  ": count += 1
                    else: 
                        count = 0
                        end = False
                
                        
                
            iface.output.write("..\n")
            iface.debug("-")
            
    for cls in clases_eliminadas:
        file1 = open(os.path.join(base,cls + ".qs"))
        iface.output.write("@@removed-class %s\n" % cls)        
        for line in file1:
            iface.output.write("  %s" % line)        
        iface.output.write("..\n")
            
    for cls in clases_agregadas:
        file1 = open(os.path.join(final,cls + ".qs"))
        iface.output.write("@@added-class %s\n" % cls)        
        for line in file1:
            iface.output.write("  %s" % line)        
        iface.output.write("..\n")
            
    iface.output.write("\n")
            
    
    
def get_move_actions(cln1, names):
    actions = []
    cln = cln1[:]
    for i in reversed(range(len(cln))):
        if i == 0: break
        if cln[i-1] < cln[i]: continue
        for j in reversed(range(-1,i)):
            if j < 0 or cln[j] < cln[i]: break

        beforen2 = cln[j+1:i]
        mbf2 = min(beforen2)
        for k in range(i,len(cln)):
            if k > mbf2: break
        beforen1 = cln[i:k+1]
        
        actions.append(([names[i] for i in beforen1], "before", [names[i] for i in beforen2]))
        cln[i:k+1] = []
        cln[j+1:i] = beforen1 + cln[j+1:i]
        
    return actions
        
    
    



def extract_classes(iface,clfinal,flfinal,classes2extract, classes2delete = []):    
    iface_line = -1
    if clfinal['iface']:
        iface_line = clfinal['iface']['line']

    for clname in classes2delete:
        iface.output.write("\n")
        iface.output.write("/** @delete_class %s */" % clname)
        iface.output.write("\n")
    
        
    for clname in classes2extract:
        block_decl = clfinal['decl'].get(clname,None)
        if block_decl is None:
            iface.error(u"Se esperaba una declaración de clase para %s." % clname)
            continue
        dtype, clname, idx1, idx2 = clfinal['list'][block_decl]
        iface.debug2r(exported_block=clfinal['list'][block_decl])
        
        lines = flfinal[idx1:idx2]
        if iface_line >= idx1 and iface_line < idx2:
            # Excluir la definición "iface" del parche, en caso de que estuviese dentro
            rel_line = iface_line - idx1
            from_text = clfinal['iface']['text']
            assert( lines[rel_line].find(from_text) != -1 )
            lines[rel_line] = lines[rel_line].replace(from_text,"")
        while lines[0].strip() == "": del lines[0]
        while lines[-1].strip() == "": del lines[-1]

        text = "\n".join(lines) 
        iface.output.write("\n")
        iface.output.write(text)
        iface.output.write("\n")
        
    
    for clname in classes2extract:
        block_def = clfinal['def'].get(clname,None)
        if block_def is None:
            iface.debug(u"Se esperaba una definición de clase para %s." % clname)
            continue
        dtype, clname, idx1, idx2 = clfinal['list'][block_def]
        iface.debug2r(exported_block=clfinal['list'][block_def])
        lines = flfinal[idx1:idx2]
        while lines[0].strip() == "": del lines[0]
        while lines[-1].strip() == "": del lines[-1]

        text = "\n".join(lines) 
        iface.output.write("\n")
        iface.output.write(text)
        iface.output.write("\n")
        
    iface.output.write("\n")
    return True
        

def check_qs_classes(iface, base):
    iface.debug(u"Comprobando clases del fichero QS $filename:%s" % (base))
    nbase, flbase = file_reader(base)
    if flbase is None:
        iface.info(u"Abortando comprobación por error al abrir los ficheros")
        return
    clbase = qsclass_reader(iface, base, flbase)
    classdict = extract_class_decl_info(iface, flbase)
    
    if not clbase['iface']:
        iface.error(u"No encontramos declaración de iface.")
        return
    iface_clname = clbase['iface']['classname']
    iface.debug(u"Se encontró declaración iface de la clase %s" % (repr(iface_clname)))
    # Buscar clases duplicadas primero. 
    # Los tests no se ejecutaran bien si tienen clases duplicadas.
    for clname in set(clbase['classes']):
        count = clbase['classes'].count(clname)
        if count > 1:
            iface.error("La clase %s se encontró %d veces" % (clname,count))            
            return
    
    if iface_clname not in classdict:
        iface.error(u"La declaración de iface requiere una clase %s"
                    u" que no existe." % (iface_clname))
        return
    not_used_classes = clbase['classes'][:]
    iface_class_hierarchy = []
    current_class = iface_clname
    prev_class = "<no-class>"
    if clbase['iface']['line'] < classdict[current_class]['line']:
        iface.warn(u"La declaración de iface requiere una clase %s"
                   u" que está definida más abajo en el código" % (current_class))
    while True:
        if current_class not in not_used_classes:
            if current_class in clbase['classes']:
                iface.error(u"La clase %s es parte de una "
                            u"referencia circular (desde: %s)" % 
                            (current_class, prev_class))
            else:
                iface.error(u"La clase %s no está "
                            u"definida (desde: %s)" % 
                            (current_class, prev_class))
            return
        not_used_classes.remove(current_class)
        iface_class_hierarchy.insert(0, current_class)
        parent = classdict[current_class]['extends']        
        if parent is None: break
        
        if parent not in classdict or parent not in clbase['classes']:
            iface.error(u"La clase %s no está "
                        u"definida (extends de la clase %s, desde: %s)" % 
                        (parent, current_class, prev_class))
            return
            
        if not check_class(iface, flbase, clbase, classdict, current_class):
            iface.error(u"Se detectó algún problema en la clase %s"
                        u" (clase padre: %s, desde: %s)" % 
                        (current_class, parent, prev_class))
        
        if classdict[current_class]['line'] < classdict[parent]['line']:
            iface.error(u"La clase %s hereda de una clase %s que está"
                        u" definida más abajo en el código" % (current_class, parent))
            return
        current_class = parent

    # De las clases sobrantes, ninguna puede heredar de alguna que hayamos usado
    for clname in not_used_classes:
        parent = classdict[clname]['extends']        
        if parent in iface_class_hierarchy:
            iface.error(u"La clase %s no la heredó iface, y sin embargo,"
                        u" hereda de la clase %s que sí la heredó." % (clname, parent))
            return
    iface.debug2r(classes=iface_class_hierarchy)
    iface.info2(u"La comprobación se completó sin errores.")
    return True
    
    
    
    
def patch_qs(iface, base, patch):
    iface.debug(u"Procesando Patch QS $base:%s + $patch:%s" % (base, patch))
    nbase, flbase = file_reader(base)
    npatch, flpatch = file_reader(patch)
    if flbase is None or flpatch is None:
        iface.info(u"Abortando Patch QS por error al abrir los ficheros")
        return
    # classlist
    clpatch = qsclass_reader(iface, patch, flpatch) 
    # classdict
    cdpatch = extract_class_decl_info(iface, flpatch) 
    
    if clpatch['iface']:
        iface.error(u"El parche contiene una definición de iface. No se puede aplicar.")
        return
    
    #iface.debug2r(clpatch=clpatch)
    #iface.debug2r(cdpatch=cdpatch)
    
    # Hallar el trabajo a realizar:
    #  - Hay que insertar en "base" las clases especificadas por clpatch['classes']
    #       en el mismo orden en el que aparecen.
    #  - Al insertar la clase agregamos en el extends un /** %from: clname */
    #       que indicará qué clase estábamos buscando.
    #  - Cuando insertemos una nueva clase, hay que ajustar las llamadas a la
    #       clase padre de la clase insertada y de la nueva clase hija
    #  - En caso de no haber nueva clase hija, entonces "iface" cambia de tipo.
    #       Además, probablemente haya que bajar la definición de iface.
    new_iface_class = None
    for newclass in clpatch['classes'] + clpatch['delclasses']:
        auth_overwrite_class = False
        todo = [] # Diferentes "arreglos" que ejecutar luego.
        clbase = qsclass_reader(iface, base, flbase) 
        cdbase = extract_class_decl_info(iface, flbase) 
        if iface.patch_qs_rewrite == "reverse":
            mode = "insert" if newclass in clpatch['delclasses'] else "delete"
        else:
            mode = "insert" if newclass in clpatch['classes'] else "delete"
            
        if mode == "delete":
            iface.debug(u"Procediendo a la *eliminación* de la clase %s" % newclass)
        else:
            iface.debug(u"Procediendo a la inserción de la clase %s" % newclass)
            
        if mode == "delete" and newclass not in clbase['classes']:
            iface.info2(u"La clase %s NO estaba insertada en el fichero, "
                        u"se OMITE el borrado de la clase." % newclass)
            continue

        # debería heredar de su extends, o su from (si existe). 
        # si carece de extends es un error y se omite.
        if mode == "insert": 
            extends = cdpatch[newclass]['extends']
        else:
            extends = cdbase[newclass]['extends']

            
        if mode == "delete":
            iface.info2(u"La clase %s ya estaba insertada en el fichero, "
                        u"se procede a borrar la clase como se ha solicitado." % newclass)
            old_extends = cdbase[newclass]['extends']
            for clname, cdict in cdbase.items():
                # Si alguna clase extendía esta, ahora extenderá $old_extends
                if cdict['extends'] == newclass:
                    fix_class(iface, flbase, clbase, cdbase, clname, set_extends = old_extends)
            
            # TODO: Si iface era de tipo $newclass, ahora será de tipo $old_extends.
                    
            remove_lines = []
            if newclass in clbase['decl']:
                remove_lines.append(clbase['decl'][newclass])
                del clbase['decl'][newclass]
            
            if newclass in clbase['def']:
                remove_lines.append(clbase['def'][newclass])
                del clbase['def'][newclass]
            
            for n in reversed(sorted(remove_lines)):
                del clbase['list'][n]
            
            clbase['classes'].remove(newclass)
            del cdbase[newclass]
        lower_classes = [ str(x).lower() for x in clbase['classes'] ]
        if str(newclass).lower() in lower_classes:
            if iface.patch_qs_rewrite == "abort":
                iface.error(u"La clase %s ya estaba insertada en el fichero, "
                            u"abortamos la operación." % newclass)
                return False
            if iface.patch_qs_rewrite == "no":
                iface.warn(u"La clase %s ya estaba insertada en el fichero, "
                            u"omitimos el parcheo de esta clase." % newclass)
                continue
            if iface.patch_qs_rewrite == "yes":
                iface.info2(u"La clase %s ya estaba insertada en el fichero, "
                            u"se sobreescribirá la clase." % newclass)
            
            if iface.patch_qs_rewrite == "warn":
                iface.warn(u"La clase %s ya estaba insertada en el fichero, "
                            u"se sobreescribirá la clase." % newclass)
            auth_overwrite_class = True
            idx = lower_classes.index(str(newclass).lower())
            oldclass = clbase['classes'][idx]
        if extends is None:
            iface.error(u"La clase %s carece de extends y no es insertable como"
                        u" un parche." % newclass)
            continue
        cfrom = cdpatch[newclass]['from']
        if cfrom and cfrom != extends: 
            iface.debug(u"class %s: Se ha especificado un %%from %s y "
                        u"tomará precedencia por encima del extends %s" % (
                        newclass, cfrom, extends) )
            extends = cfrom
            #iface.debug(u"class %s: Se ha especificado un %%from %s, "
            #            u"pero se ignora y dejamos el extends %s" % (
            #            newclass, cfrom, extends) )
        if extends not in clbase['classes']:
            clsheur = 1 # <- cambiar modo de heuristica
            if clsheur == 1 : 
                try:
                    # Modo heuristico basico:
                    if newclass.startswith("pub"): testclass = "iface"
                    elif newclass.startswith("base"): testclass = "interna"
                    else: testclass = "oficial"
                    if testclass not in clbase['classes']:
                        testclass = clbase['classes'][-1]
                    
                    iface.warn(u"La clase %s debía heredar de %s, pero no "
                                u"la encontramos en el fichero base. "
                                u"En su lugar, heredará de %s." % (newclass,extends, testclass))
                    extends = testclass
                except IndexError:
                    iface.error(u"La clase %s debía heredar de %s, pero no "
                                u"la encontramos en el fichero base." % (newclass,extends))
                    continue
                
            else:
                # Modo antiguo:
                iface.error(u"La clase %s debía heredar de %s, pero no "
                            u"la encontramos en el fichero base." % (newclass,extends))
                continue
        iface.debug(u"La clase %s deberá heredar de %s" % (newclass,extends))
        
        # Buscar la clase más inferior que heredó originalmente de "extends"
        if auth_overwrite_class:
            extends = cdbase[oldclass]['from']
            extending = cdbase[oldclass]['extends']
        else:
            extending = extends
            for classname in reversed(clbase['classes']):
                # Buscamos del revés para encontrar el último.
                cdict = cdbase[classname]
                if cdict['from'] == extends:
                    extending = cdict['name']
                    iface.debug(u"La clase %s es la última que heredó de %s, pasamos a heredar de ésta." % (extending,extends))
                    break
        
        if mode == "insert":
            # Habrá que insertar el bloque entre dos bloques: parent_class y child_class.
            # Vamos a asumir que estos bloques están juntos y que child_class heredaba de parent_class.
            parent_class = clbase['decl'][extending]
            # Dónde guardar el código de definición: (después de la clase que extendimos)
            ext_class_idx = clbase["classes"].index(extending)
            if newclass in clpatch['def']:
                while True: 
                    ext_cname = clbase["classes"][ext_class_idx]
                    try:
                        child_def_block = clbase['def'][ext_cname] + 1 
                        break
                    except KeyError:
                        ext_class_idx += 1
                        if ext_class_idx >= len(clbase["classes"]):
                            iface.info2(u"Se va a colocar el código de las "
                                       u"definiciones de la clase %s al"
                                       u" final del fichero." % (newclass))
                            child_def_block = max(clbase['def'].values()) + 1 
                            break
            else:
                child_def_block = max(clbase['def'].values()) + 1 
            
           
            assert(clbase['list'][parent_class][1] == extending) # <- este calculo deberia ser correcto. 
        
            child_class = -1 # Supuestamente es el siguiente bloque de tipo "class_declaration".
            for n, litem in enumerate(clbase['list'][parent_class:]):
                if n == 0: continue
                if litem[0] != "class_declaration": continue
                child_class = parent_class + n
                break
                
            if child_class >= 0 and not auth_overwrite_class:
                prev_child_cname = clbase['list'][child_class][1]
                # $prev_child_name debería estar heredando de $extending.
                if cdbase[prev_child_cname]['extends'] != extending:
                    iface.error(u"Se esperaba que la clase %s heredara de "
                                u"%s, pero en cambio hereda de %s" % (prev_child_cname,extending,cdbase[prev_child_cname]['extends']))
                    continue                    
                else:
                    iface.debug(u"La clase %s hereda de %s, pasará a heredar %s" % (prev_child_cname,extending,newclass))
                    todo.append('fix-class prev_child_cname')
            else:
                # Si no había clase posterior, entonces marcamos como posición
                # de inserción el próximo bloque.
                child_class = parent_class + 1
            
            # Si la clase que vamos a heredar es la que está en el iface, entonces 
            #   en el iface habrá que cambiarlo por la nuestra.
            if clbase['iface']: # -> primero comprobar que tenemos iface.
                iface.debug2r(iface=clbase['iface'])
                if clbase['iface']['classname'] == extending:
                    iface.debug(u"La clase que estamos extendiendo (%s) es el "
                            u"tipo de dato usado por iface, por lo tanto actualizamos"
                            u" el tipo de dato usado por iface a %s" % (extending, newclass))
                    todo.append('fix-iface newclass')
                    new_iface_class = newclass
            else:
                iface.warn("No existe declaración de iface en el código (aplicando patch para clase %s)" % newclass)
                todo.append('create-iface')
                
            # Si la clase del parche que estamos aplicando pasa a extender otra 
            # clase con nombre distinto, actualizaremos también los constructores.
            if cdpatch[newclass]['extends'] != extending:
                iface.debug(u"La clase %s extendía %s en el parche, pasará a"
                        u" heredar a la clase %s" % (newclass, 
                            cdpatch[newclass]['extends'], extending))
                todo.append('fix-class newclass')
            
            
        # Bloques a insertar:
        newblocklist = clbase['list'][:]
        if mode == "insert":
            if newclass in clpatch['def']:
                try:
                    from_def_block = clpatch['list'][clpatch['def'][newclass]]
                    # incrustamos en posicion $child_def_block
                    if newclass in clbase['classes']:
                        # Sobreescribimos el bloque si ya existe la clase.
                        assert(auth_overwrite_class)
                        newblocklist[clbase['def'][newclass]] = from_def_block 
                    else: newblocklist.insert(child_def_block, from_def_block)
            
                    # Se hace en orden inverso (primero abajo, luego arriba) para evitar
                    # descuadres, por tanto asumimos:
                    assert(child_def_block > child_class)
            
                except KeyError:
                    iface.info2(u"La clase %s carece de bloque de definición." % newclass)
            
            from_decl_block = clpatch['list'][clpatch['decl'][newclass]]
            # incrustamos en posicion $child_class
            if newclass in clbase['classes']:
                assert(auth_overwrite_class)
                newblocklist[clbase['decl'][newclass]] = from_decl_block
            else: newblocklist.insert(child_class, from_decl_block)
        
        newbase = [] # empezamos la creación del nuevo fichero
        
        # insertamos las líneas de cabecera (hasta el primer bloque)
        idx1 = clbase['list'][0][2]
        newbase += flbase[:idx1]
        
        # iteramos por la lista de bloques y vamos procesando.
        for btype, bname, idx1, idx2 in newblocklist:
            # ATENCION: Sabemos que un bloque viene del parche o de base porque
            # .. tiene la clase $newclass que no está en base. Si esta condición
            # .. no se cumple, entonces el algoritmo falla.
            if bname == newclass: source = "patch"
            else: source = "base"
            
            if source == "base":
                block = flbase[idx1:idx2]
            elif source == "patch":
                block = flpatch[idx1:idx2]
            else: raise AssertionError
            while block[0] == "": del block[0]
            while block[-1] == "": del block[-1]
            block.append("")
            newbase += block
        
        # Ya tenemos el fichero montado:
        flbase = newbase
        # Recalculamos:
        clbase = qsclass_reader(iface, base, flbase) 
        cdbase = extract_class_decl_info(iface, flbase) 
        
        # Procesar tareas (to-do)
        if mode == "insert":
            fix_class(iface, flbase, clbase, cdbase, newclass, set_extends = extending, set_from = extends)
            if 'fix-class newclass' in todo:
                # Esta tarea se realiza en la linea anterior incondicionalmente. 
                todo.remove('fix-class newclass')
            
            if 'fix-class prev_child_cname' in todo:
                iface.debug2r(prev_child_cname)
                fix_class(iface, flbase, clbase, cdbase, prev_child_cname, set_extends = newclass)
                # Al terminar, borramos la tarea.
                todo.remove('fix-class prev_child_cname')

            if 'fix-iface newclass' in todo:
                fix_iface(iface, flbase, clbase, new_iface_class)
                todo.remove('fix-iface newclass')
                
            
        for task in todo:
            iface.warn("La tarea %s no se ejecutó o se desconoce cómo hacerlo." % repr(task))
    line = ""
    for line in flbase:
        iface.output.write(line)
        iface.output.write("\n")
        
    if line:
        iface.output.write("\n")
    
    return True
    
def fix_iface(iface, flbase, clbase, newclass):
    oldclass = clbase['iface']['classname']
    oldtext = clbase['iface']['text']
    newtext = oldtext.replace(" %s(" % oldclass, " %s(" % newclass, 1)
    line = clbase['iface']['line']
    oldline = flbase[line]
    newline = oldline.replace(oldtext,newtext, 1)
    iface.debug("%d: %s -> %s" % (line, oldline, newline))
    flbase[line] = newline
    clbase['iface']['text'] = newtext
    clbase['iface']['classname'] = newclass

def fix_class(iface, flbase, clbase, cdbase, classname, **updates):
    """
        Busca en $base la clase $class_name y modifica el código según los
        cambios en $**updates.
        Updates puede contener los siguientes tipos de argumentos:
        
        set_extends = actualiza la herencia de la clase
        set_from = actualiza la sentencia from
    """
    #iface.debug2r(clbase=clbase)
    #iface.debug2r(cdbase=cdbase)
    set_extends = updates.get("set_extends",-1)
    set_from = updates.get("set_from",-1)
    if set_extends == -1 and set_from == -1: raise ValueError
    
    if set_extends != -1: extends = set_extends
    else: extends = cdbase[classname]['extends']
    
    if set_from != -1: cfrom = set_from
    else: cfrom = cdbase[classname]['from']

    # Reescribir sentencia class:
    line_no = cdbase[classname]['line']
    old_expr = cdbase[classname]['text']
    new_expr = "class %s" % classname
    if extends: new_expr += " extends %s" % extends
    if cfrom: new_expr += " /** %%from: %s */" % cfrom

    flbase[line_no] = flbase[line_no].replace(old_expr, new_expr)

    if cdbase[classname]['extends'] != extends:
        # Si se ha cambiado la herencia
        decl_block_no = clbase['decl'][classname]
        end_line = clbase['list'][decl_block_no][3]
        for n,line in enumerate(flbase[line_no:end_line],line_no):
            m_it = re.finditer("(?P<fname>\w+)\s*\(\s*context\s*\);?", line)
            for m in m_it:
                if m.group("fname") != cdbase[classname]['extends']: continue
                old = m.group(0)
                new = str(m.group(0)).replace(cdbase[classname]['extends'],extends,1)
                flbase[n] = line.replace(old,new,1)
                # iface.debug2r(line = line)
                # iface.debug2r(new_line = flbase[n])
                
            
        
        
    cdbase[classname]['extends'] = extends
    cdbase[classname]['from'] = cfrom



def check_class(iface, flbase, clbase, cdbase, classname):
    """
        Busca en $base la clase $class_name y comprueba que sea correcta.
    """
    
    extends = cdbase[classname]['extends']
    
    line_no = cdbase[classname]['line']
    old_expr = cdbase[classname]['text']
    new_expr = "class %s" % classname
    
    decl_block_no = clbase['decl'][classname]
    end_line = clbase['list'][decl_block_no][3]
    found = []
    line_found = []
    for n,line in enumerate(flbase[line_no:end_line],line_no):
        match = list(re.finditer("(?P<fname>\w+)\s*\(\s*context\s*\);", line))
        if match: 
            line_found.append(line)
            found += match 
        
    if len(line_found) < 1:
        iface.error(u"No encontramos lineas candidatas a constructor")
        return False
    if len(line_found) > 1:
        iface.error(u"Encontramos más de una linea candidata a constructor: %s" % repr(line_found))
        return False
    for m in found:
        old = m.group(0)
        new = str(m.group(0)).replace(m.group(1),extends,1)
        if extends != m.group(1):
            iface.error("Leimos %s pero deberia ser %s (%s)" % (old,new,line_found[0]))
            return False
            
    return True
                
            
        
        




"""
    Análisis de reordenación de clases:

    Primero eliminamos toda clase en A y B que haya sido agregada o eliminada. 
    Dejamos solo las clases comunes a las dos versiones.

    Luego, se examina hacia abajo cuantas clases consecutivamente coinciden en 
    orden hasta que encontramos la primera que no coincide. Eliminamos todo el bloque
    superior de clases que coinciden. Hacemos lo mismo de abajo a arriba.

    Se realiza un análisis de movimientos mínimos para llegar del set A al set B.
    
    Para realizar este análisis, seguimos el algoritmo de ordenación por inserción:
    
    http://es.wikipedia.org/wiki/Ordenamiento_por_inserci%C3%B3n
    
    Según este sistema, asignamos un número a cada clase del 1 a la 99 según su 
    orden en B (destino).
    
    Luego, usando el algoritmo de ordenacion calculamos los movimientos mínimos
    para llegar de A a B.
    
    Se analiza siempre de del final hacia adelante, buscando cuando un número es
    menor que su anterior. Ese número se desplaza hacia la izquierda tantas veces
    hasta que su anterior sea menor o no haya más antes. 
    
    Por ejemplo, con la siguente secuencia, tendríamos:
    
    ::::   3412576
    ext 6 : 1 posicion a la izquierda

    ::::   3412567
    ext 1 : 2 posiciones a la izquierda

    ::::   1342567
    ext 2 : 2 posiciones a la izquierda

    ::::   1234567
    Ok.
    
    Esto guardará unas instrucciones a modo de parche:
    
    clase 6 antes de 7
    clase 1 antes de 3 y de 4
    clase 2 después de 1 (este "después" se agrega porque se está moviendo en medio de la anterior)
    

    
"""


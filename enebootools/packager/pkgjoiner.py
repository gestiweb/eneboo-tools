# encoding: UTF-8
import zlib, os, sys, re, hashlib
from enebootools.packager.pkgsplitter import to_uint32
from enebootools.packager import __version__, __PROGRAM__NAME__
from enebootools.lib.utils import find_files

__package_header__ = "%s %s" % (__PROGRAM__NAME__, __version__)



def from_uint32(number):
    text = ""
    for i in range(4):
        byte = (number >> ((3 - i)*8) ) & 0xff 
        ch = chr(byte)
        text += ch
    number2 = to_uint32(text)
    try: assert(number == number2)
    except AssertionError:
        print "ASSERT: number %d == number2 %d ... FAILED" % (number, number2)
        raise
    
    return text

def write_compressed(f1, txt):
    zipped_text = from_uint32( len(txt) ) + zlib.compress(txt)
    write_string(f1,zipped_text, binary = True)

def write_string(f1, txt, binary = False):
    if binary:
        text = txt
    else:
        text = txt.rstrip() + "\0"
        if text == "\0": 
            f1.write( from_uint32( 0 ) )
            return
        
    lentxt = from_uint32( len(text) )
    f1.write(lentxt)
    f1.write(text)

    

def joinpkg(iface, packagefolder):
    if packagefolder.endswith("/"): packagefolder=packagefolder[:-1]
    if packagefolder.endswith("\\"): packagefolder=packagefolder[:-1]
    iface.info2("Empaquetando carpeta %s . . ." % packagefolder)
    packagename = packagefolder + ".eneboopkg"
    f1 = open(packagename,"w")
    n = 0
    for filename in sorted(os.listdir(packagefolder)):
        n+=1
        format = "string"
        if filename.endswith(".file"): format = "compressed"
        contents = open(os.path.join(packagefolder,filename)).read()
        if format == "string": 
            sys.stdout.write(".")
            write_string(f1, contents)
        if format == "compressed": 
            sys.stdout.write("*")
            write_compressed(f1, contents)
        sys.stdout.flush()
    f1.close()
    print 
    print  "Hecho. %d objetos empaquetados en %s" % (n,packagename)
    
        

def createpkg(iface, modulefolder):
    if modulefolder.endswith("/"): modulefolder=modulefolder[:-1]
    if modulefolder.endswith("\\"): modulefolder=modulefolder[:-1]
    iface.info2("Creando paquete de módulos de %s . . ." % modulefolder)
    outputfile = modulefolder + ".eneboopkg"
    
    f1 = open(outputfile, "w")
    # VERSION
    write_string(f1,__package_header__)
    
    # RESERVADO 1
    write_string(f1,"")

    # RESERVADO 2
    write_string(f1,"")
    
    # RESERVADO 3
    write_string(f1,"")

    # MODULES
    modules = find_files(modulefolder, "*.mod", True)
    file_folders = []
    modnames = []
    modlines = []
    for module in sorted(modules):
        file_folders.append(os.path.dirname(module))
        modnames.append(os.path.basename(module))
        modlines.append("<!-- Module %s -->\n" % module)
        inittag = False
        for line in open(os.path.join(modulefolder, module)):
            if line.find("<MODULE>") != -1: inittag = True
            if inittag: modlines.append(line)
            if line.find("</MODULE>") != -1: inittag = False
    
    write_compressed(f1, """<!DOCTYPE modules_def>
<modules>
%s
</modules>""" % (''.join(modlines)))
    # FILES XML
    file_list = []
    filelines = []
    shasum = ""
    ignored_ext = set([])
    load_ext = set(['.qs', '.mtd', '.ts', '.ar', '.kut', '.qry', '.ui', '.xml', '.xpm'])
    for folder, module in zip(file_folders,modnames):
        fpath = os.path.join(modulefolder,folder)
        files = find_files(fpath)
        modulename = re.search("^\w+",module).group(0)
        print fpath, modulename
        for filename in files:
            bname, ext = os.path.splitext( filename )
            if ext not in load_ext: 
                ignored_ext.add(ext)
                continue
            
            file_basename = os.path.basename(filename)
            filepath = os.path.join(fpath,filename)
            sha1text = hashlib.sha1(open(filepath).read()).hexdigest()
            sha1text = sha1text.upper()
            shasum+= sha1text
            file_list.append(filepath)
            filelines.append("""  <file>
    <module>%s</module>
    <name>%s</name>
    <text>%s</text>
    <shatext>%s</shatext>
  </file>
""" % (modulename, file_basename, file_basename, sha1text))

    write_compressed(f1, """<!DOCTYPE files_def>
<files>
%s  <shasum>%s</shasum>
</files>
""" % (''.join(filelines), hashlib.sha1(shasum).hexdigest().upper()))
    
    # FILE CONTENTS
    for filepath in file_list:
        sys.stdout.write(".")
        sys.stdout.flush()
        write_compressed(f1, open(filepath).read())
    print
    # CLOSE
    f1.close()
    print "Paquete creado. Extensiones ignoradas:", ignored_ext    

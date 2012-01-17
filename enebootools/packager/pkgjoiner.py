import zlib, os, sys
from enebootools.packager.pkgsplitter import to_uint32

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
    
        

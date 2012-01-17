import zlib, os, sys

def to_uint32(text):
    number = 0
    for i, ch in enumerate(list(text)):
        n = ord(ch)
        byte = 3-i
        n *= 2**(8*byte)
        number += n
    return number

def read_string(f1):
    txtsize = f1.read(4)
    if len(txtsize)==0: return None
    if len(txtsize)<4: raise AssertionError, "File Error"
    slen = to_uint32(txtsize)
    
    string = f1.read(slen)
    
    try: assert(len(string) == slen)
    except AssertionError:
        print "ASSERT: len(string) %d == slen %d  ... FAILED" % (len(string), slen)
        raise
    #print slen, repr(string[:32])
    return string
    
    
def uncompress(txt):
    
    slen = to_uint32(txt[0:4])
    try:
        txt_data = zlib.decompress(txt[4:])
    except zlib.error, e:
        return None
    if slen != len(txt_data):
        print "Uncompressed data size does not match the expected size"
    #print slen, len(txt_data), repr(txt_data[:256])
    return txt_data
    

def splitpkg(iface, packagefile):
    iface.info2("Separando paquete %s . . ." % packagefile)
    f1 = open(packagefile)
    version = read_string(f1)
    foldername = packagefile+".contents"
    try:
        os.mkdir(foldername)
    except OSError, e:
        pass
    
    sys.stdout.write("|")
    sys.stdout.flush()
    open(os.path.join(foldername, "0001.header"),"w").write(version[:-1]+"\n")
    n = 1
    while n<20000:
        n+=1
        text = read_string(f1)
        if text is None: break
        unzipped = uncompress(text)
        if unzipped:
            sys.stdout.write("*")
            sys.stdout.flush()
            open(os.path.join(foldername, "%04d.file" % n),"w").write(unzipped)
        else:            
            sys.stdout.write(".")
            sys.stdout.flush()
            open(os.path.join(foldername, "%04d.text" % n),"w").write(text[:-1]+"\n")
        #if n%50 == 0:
        #    sys.stdout.write("\n")
        #    sys.stdout.flush()
    f1.close()
        
    print
    print "Hecho. %d objetos extraidos en %s" % (n,foldername)
    
    


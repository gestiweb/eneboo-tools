# encoding: UTF-8


def configure(parse):
    # leer parse.short_options y parse.options, y de las que se procesen aquí,
    # eliminarlas del array. (o modificar su valor)
    
    # Esta función está pensada para ser llamada únicamente desde la consola y
    # realiza transformaciones por ejemplo en --output-file cambiando el valor
    # a un fichero real.
    print "Configurando mergetool . . ."
    
    
def cleanup_configure(parse):
    # Realiza la operación inversa de configure, básicamente liberando recursos
    # que posiblemente haya reservado.
    print "Desconfigurando mergetool . . ."
    
    
Proyecto Eneboo-tools (Guía superrapida)
=================================================

Actualmente solo se provee del comando eneboo-mergetool.

Dependencias
---------------------

Como mínimo, se necesita:
    * python 2.5 
    * lxml (python-lxml)
        * libxml2
        * libxslt
    
Para tener el programa funcionando, se recomienda:
    * python 2.6 o superior. (no es compatible con Python 3.X)
    * lxml (python-lxml) (Parser de XML)
    * psycopg (python-psycopg) (Driver de base de datos PostgreSQL)
    * pyqt4 (python-pyqt4) (Enlace de Qt4 para GUI)
    

Instalación
---------------------

No hay aún instalación, pero se recomienda enlazarlo a /usr/local/bin para 
poder llamarlo desde cualuquier sitio::

    $ sudo ln -s $HOME/git/eneboo-tools/eneboo-mergetool /usr/local/bin/eneboo-mergetool


Uso
-------------------

Para sacar una ayuda y listado de acciones::

    $ eneboo-mergetool --help


Para sacar más ayuda de una acción::

    $ eneboo-mergetool --help nombre-accion


Acciones disponibles
----------------------------

**Utilidades para carpetas:**

*folder-diff* lee dos carpetas recursivamente y obtiene una diferencia. A partir
de esta diferencia, genera una colección de parches en una tercera carpeta.

*folder-patch* lee una carpeta de parches (flpatch) y una carpeta de ficheros
originales. Aplica los parches en a estos ficheros y el resultado se guarda en 
una tercera carpeta.
            
**Utilidades para ficheros individuales:**

*file-diff* muestra la diferencia entre dos ficheros por la salida estándar o a 
un fichero especificado por --output-file. Tiene un argumento de modo que 
condiciona el tipo de algoritmo que será lanzado para comparar los ficheros.
Están soportados *qs* y *xml*.
            
*file-patch* muestra el resultado de aplicar un parche a un fichero por la salida
estándar o guarda el resultado en el fichero indicado por --output-file. Tiene
un argumento de modo que condiciona el algoritmo que se lanza para aplicar el 
parche. Están soportados *qs* y *xml*.

*file-check* realiza comprobaciones rutinarias sobre el fichero dado. Actualmente
sólo está soportado el modo *qs-classes*, que comprobará la correcta herencia de
éstas.
            
*qs-extract* es una utilidad para extraer clases que se especifiquen de un 
fichero qs directamente, sin necesidad de comparar con otro fichero.


FOLDER DIFF
-----------------------------------

Extrae las modificaciones realizadas en un proyecto y guarda una carpeta 
de parche.

Para trabajar con esta herramienta, debemos contar con dos carpetas. Una 
contendrá un backup del proyecto antes de realizar los cambios y la otra será
donde hayamos realizado nuestras modificaciones. Llamamos *basedir* a la carpeta
de backup y *finaldir* a la carpeta donde están los cambios realizados.

Esta herramienta creará una carpeta (que no debe existir antes) y dejará dentro
todas las diferencias encontradas, así como las instrucciones de aplicación.

Veamos un ejemplo::

    $ eneboo-mergetool folder-diff parches/mi_parche \
        proyecto1_original/ proyecto1_modificado/
        
Esto crearía la carpeta *parches/mi_parche* y contendría las instrucciones para
generar *proyecto1_modificado* a partir del *proyecto1_original*.


FOLDER PATCH
-----------------------------------

Lee una carpeta de parche y aplica las modificaciones en el proyecto generando
una carpeta nueva.

Para trabajar con esta herramienta, debemos contar con dos carpetas. Una 
contendrá proyecto a aplicar los cambios y la otra será donde hayamos guardado
el parche. Llamamos *basedir* a la carpeta del proyecto original y *patchdir* 
 a la carpeta donde están guardados los parches.

Esta herramienta creará una carpeta (que no debe existir antes) y dejará dentro
el nuevo proyecto que será el resultado de la aplicación de los parches.

Veamos un ejemplo::

    $ eneboo-mergetool folder-patch parches/mi_parche \
        proyecto1_original/ proyecto1_parcheado/
        
Esto crearía la carpeta *proyecto1_parcheado/* y contendría *proyecto1_original/*
pero con los parches aplicados.



DIFF QS
---------------

Obtener diff de un fichero QS::

    $ eneboo-mergetool file-diff qs \
        antiguo/facturacion/facturacion/scripts/flfactalma.qs \
        nuevo/facturacion/facturacion/scripts/flfactalma.qs \
        --output-file patches/flfactalma.qs


Aplicar un diff de fichero QS::

    $ eneboo-mergetool file-patch qs \
        antiguo/facturacion/facturacion/scripts/flfactalma.qs \
        patches/flfactalma.qs \
        --output-file antiguo/facturacion/facturacion/scripts/flfactalma.patched.qs



DIFF XML
---------------------

Obtener diff de un fichero XML::

    $ eneboo-mergetool file-diff xml \
        antiguo/facturacion/facturacion/forms/flfactalma.ui \
        nuevo/facturacion/facturacion/forms/flfactalma.ui \
        --output-file patches/flfactalma.ui

Aplicar un diff de fichero XML::

    $ eneboo-mergetool file-patch qs \
        antiguo/facturacion/facturacion/forms/flfactalma.ui \
        patches/flfactalma.ui \
        --output-file antiguo/facturacion/facturacion/scripts/flfactalma.patched.ui







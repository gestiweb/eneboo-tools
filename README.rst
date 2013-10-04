Proyecto Eneboo-tools (Guía superrapida)
=================================================

Actualmente solo se proveen los comandos eneboo-mergetool y eneboo-assembler.

Otros comandos que no están listados aquí pueden ser pruebas de concepto o estar
en desarrollo.

Dependencias
---------------------

Como mínimo, se necesita:
    * python 2.5 
        * sqlite3
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

La instalación recomendada es enlazar los comandos en /usr/local/bin 

Hemos creado un Makefile que lo hace automáticamente al lanzar el comando::
    
    $ sudo make install
    
Si se quiere realizar manualmente, se puede hacer del siguiente modo::

    $ sudo ln -s $HOME/git/eneboo-tools/eneboo-mergetool /usr/local/bin/eneboo-mergetool


Assembler: Introducción
------------------------
eneboo-assembler es una herramienta de "collage" de código fuente. Toma como base
unos módulos y les aplica una serie de parches en un orden determinado para 
conseguir un proyecto modificado de cierta forma, que cumpla ciertas especificaciones.

Es una buena forma para mantener centenares de versiones distintas del mismo programa
al día, gestionando correctamente los cambios propios que tiene cada versión.

Assembler: Uso
------------------------

Para empezar, necesitaremos 2 repositorios adicionales:

    * Módulos Oficiales
    * Extensiones

Si tenemos cuenta en github, el procedimiento estándar para clonar los dos repositorios es el siguiente::

    $ cd ~/git
    $ ssh-add
    $ git clone git@github.com:gestiweb/eneboo-modules
    $ git clone git@github.com:gestiweb/eneboo-features

Si no tenemos cuenta en github, el procedimiento es::
    
    $ cd ~/git
    $ git clone git://github.com/gestiweb/eneboo-tools.git


Para instalar los comandos que tenemos en eneboo-tools es suficiente con 
ejecutar "sudo make install" desde la carpeta del proyecto.

El comando "eneboo-assembler" es el que usaremos normalmente para realizar las 
mezclas desde consola. Es muy sencillo y práctico. 

Este comando tiene unas configuraciones y una base de datos de caché. Para que 
genere los primeros ficheros es conveniente lanzar la acción "dbupdate"::

    $ eneboo-assembler dbupdate

Cabe destacar que eneboo-assembler no depende de en qué carpeta lo ejecutes. 
Todas sus acciones leen los directorios de las configuraciones. Para que esto 
funcione como debe, es necesario revisar la configuración que nos 
crea en $HOME/.eneboo-tools/assembler-config.ini

En ese fichero, que es muy sencillo de editar a mano, debemos incluir las 
rutas donde hemos puesto los módulos y las funcionalidades (extensiones). Se
deben modificar las rutas si no son las mismas en nuestro caso, o si tenemos
repositorios privados, se pueden agregar también. Hay que tener en cuenta que
las líneas de abajo toman preferencia sobre las de arriba. Se recomienda poner
al final siempre los repositorios públicos para que tomen preferencia.

Este sería un ejemplo de configuración::

    [module]
    modulefolders = 
            ~/git/eneboo-modules
    featurefolders = 
            ~/git/eneboo-features
    buildcache = ~/.eneboo-tools/buildcache

Siempre que modificamos la ruta de una extensión, o ponemos o quitamos 
alguna, es necesario ejecutar "dbupdate", que almacenará en caché dónde 
están los módulos y extensiones. Si no lo hacéis luego os dará errores 
de que no encuentra las extensiones nuevas::

    $ eneboo-assembler dbupdate -v

Las extensiones si os fijáis son carpetas con ficheros de configuración y con 
los parches para aplicar dentro. Hay un proyecto de ejemplo creado que une 
cuatro extensiones muy básicas. 

Para crear un proyecto (lo que llamamos "compilar") se lanza la acción 
"build" seguida del proyecto y del target. El "target" es qué es lo que se 
quiere crear, la idea es muy similar al make. El modo de empleo es::
    
    $ eneboo-assembler build [FEATURE] [TARGET]
    
*[FEATURE]* es el nombre corto (quitando la numeración) de la funcionalidad,
es decir, para el proyecto *prj0002-standard* habría que poner *standard*.

*[TARGET]* puede tomar los valores:

    * **base:** 
        compila las dependencias del proyecto (todo lo que 
        necesitamos para poder aplicar los parches luego)
    * **final:** 
        todo lo que lleva base, mas los parches que existen 
        para este proyecto. (esto es lo que se envía al cliente)
    * **src:** 
        una copia del target final, donde realizar los cambios 
        a la extensión
    * **patch:** 
        calcula el parche de las diferencias entre src y final. (incremental)
    * **test-patch:** 
        el resultado de aplicar el parche "patch" sobre 
        "final", sirve para realizar las pruebas convenientes antes de 
        guardar el nuevo parche.
    * **fullpatch:** 
        calcula el parche de las diferencias entre src y base. (completo)
    * **revfullpatch:** 
        calcula el parche de las diferencias entre base y src. (completo)
    * **test-fullpatch:** 
        el resultado de aplicar el parche "fullpatch" sobre 
        "base", sirve para realizar las pruebas convenientes antes de 
        guardar el nuevo parche.

Novedad: Podemos usar "revfullpatch" para que nos calcule un parche inverso, lo
cual desaplicaría una extensión a un proyecto dado.

Cuando compilamos algo, nos lo deja dentro de la carpeta build/ en la 
carpeta de la extensión que habíamos compilado.

Por ejemplo::

    deavid:~$ eneboo-assembler build basic base
    Borrando carpeta /home/deavid/git/eneboo-features/prj001-basic/build/base . . . 
    Copiando facturacion/principal . . . 
    Copiando facturacion/facturacion . . . 
    Copiando contabilidad/informes . . . 
    Copiando contabilidad/principal . . . 
    Copiando facturacion/informes . . . 
    Copiando facturacion/tesoreria . . . 
    Copiando facturacion/almacen . . . 
    Aplicando parche (...)oo-features/ext0224-pgc2008/patches/pgc2008 . . .
    Aplicando parche (...)res/ext0014-recibosprov/patches/recibosprov . . .
    WARN: No hemos encontrado el bloque de código para las definiciones de la clase ifaceCtx, pondremos las nuevas al final del fichero.
    Aplicando parche (...)/ext0020-co_renumasiento/patches/co_renumasiento . . .
    WARN: No hemos encontrado el bloque de código para las definiciones de la clase ifaceCtx, pondremos las nuevas al final del fichero.
    Aplicando parche (...)/ext0048-listadoscliprov/patches/listadoscliprov . . .

    deavid:~$ cd /home/deavid/git/eneboo-features/prj001-basic/build/
    deavid:~/git/eneboo-features/prj001-basic/build$ ls
    base  base.build.xml

    deavid:~/git/eneboo-features/prj001-basic/build$ cat base.build.xml 
    <BuildInstructions feature="prj001-basic" target="base" path="/home/deavid/git/eneboo-features/prj001-basic" dstfolder="build/base">
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/facturacion/principal" dst="facturacion/principal" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/facturacion/facturacion" dst="facturacion/facturacion" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/contabilidad/informes" dst="contabilidad/informes" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/contabilidad/principal" dst="contabilidad/principal" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/facturacion/informes" dst="facturacion/informes" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/facturacion/tesoreria" dst="facturacion/tesoreria" create_dst="yes"/>
      <CopyFolderAction src="/home/deavid/git/eneboo-modules/facturacion/almacen" dst="facturacion/almacen" create_dst="yes"/>
      <ApplyPatchAction src="/home/deavid/git/eneboo-features/ext0224-pgc2008/patches/pgc2008"/>
      <ApplyPatchAction src="/home/deavid/git/eneboo-features/ext0014-recibosprov/patches/recibosprov"/>
      <ApplyPatchAction src="/home/deavid/git/eneboo-features/ext0020-co_renumasiento/patches/co_renumasiento"/>
      <ApplyPatchAction src="/home/deavid/git/eneboo-features/ext0048-listadoscliprov/patches/listadoscliprov"/>
    </BuildInstructions>

    deavid:~/git/eneboo-features/prj001-basic/build$ find base -maxdepth 2 -type d
    base/facturacion
    base/facturacion/principal
    base/facturacion/facturacion
    base/facturacion/informes
    base/facturacion/tesoreria
    base/facturacion/almacen
    base/contabilidad
    base/contabilidad/informes
    base/contabilidad/principal


Si os fijáis, la idea es en el futuro, "apilar" parches, es decir, que cuando modificamos una 
extensión creamos otro parche **distinto**, que tiene que ser aplicado **después** 
del original. Esto ayudará a que si dos personas trabajan a la vez sobre el 
mismo parche, sea mucho más fácil mezclarlo. 

De momento, no hay soporte para parche incremental, pues casi todos los diff y 
patch contextuales son incapaces de realizar un patch incremental (la única
excepción es el de XML). Así que de momento sólo se pueden guardar cambios 
reemplazando todos los anteriores (con fullpatch).

Para guardar un cambio, después de haberlo probado con test-fullpatch y habiendo
comprobado que no hemos perdido nada, se usa la acción "save-fullpatch" del siguiente
modo::

    $ eneboo-assembler save-fullpatch prj001-basic
    
Eso sí, la operación **ES DESTRUCTIVA** y reemplazará lo que había antes sin que
se pueda recuperar. No recomiento usar esto si no tenemos la carpeta bajo control
de versiones (GIT, SVN, etc), porque en un descuido nos podemos quedar sin parche.


Aún faltan cosas básicas por desarrollar, como por ejemplo:

    * Comando "save-patch" para guardar los cambios realizados en un parche incremental
    * Comando "blend-patches" para unir todos los parches en uno solo. (excepto los N últimos) 
    * Comando "export" para generar un tar.gz de los módulos (del target final)


Assembler: Creando extensiones nuevas
-----------------------------------------

Hasta hace poco para crear las extensiones nuevas que el assembler pueda leer
había que crear los ficheros y carpetas a mano. Como son unas cuantas, esto era
un tanto costoso.

Para facilitar las cosas hemos creado una acción "new" que contiene un asistente
que realizará las preguntas necesarias y luego escribirá en disco la extensión.

Si se ejecuta sin argumentos, preguntará los datos mínimos para crear la plantilla::

    $ eneboo-assembler new

    Qué tipo de funcionalidad va a crear?
        ext) extensión
        prj) proyecto
        set) conjunto de extensiones
    Seleccione una opción: ext

    Código para la nueva funcionalidad: A002

    Nombre corto de funcionalidad: mifun02

    Descripción de la funcionalidad: Funcionalidad 02 
    
Si se le pasa el nombre de la carpeta y la descripción, omite los pasos 
iniciales y pasa directamente al menú::
    
    $ eneboo-assembler new extA003-mifun03 "Funcionalidad 03" 
    
Aparecerá el menú principal como se muestra a continuación::

    **** Asistente de creación de nueva funcionalidad ****

     : Carpeta destino : /home/david/git/eneboo-features/extA003-mifun03
     : Nombre          : extensión - A003 - mifun03 
     : Descripción     : Funcionalidad 03 

     : Dependencias    : 0 módulos, 0 funcionalidades
     : Importar Parche : None

    --  Menú de opciones generales --
        c) Cambiar datos básicos
        d) Dependencias
        i) Importar parche
        e) Eliminar parche
        a) Aceptar y crear
        q) Cancelar y Salir
    Seleccione una opción: 


La opción *d) Dependencias* sirve para añadir módulos y funcionalidades. Una vez dentro del menú de dependencias, para facilitar la tarea de agregado podemos utilizar caracteres comodín. Por ejemplo, si introducimos "flfact*" y pulsamos tabulador, pondrá todos los módulos que empiecen por "flfact".

En el caso de las rutas, también existe autocompletado con el sistema de ficheros, que se activa con la tecla de tabulador.

Por defecto las extensiones se crean en la primera carpeta de extensiones que
haya en la configuración, se puede cambiar la carpeta de destino en una opción del
menú.

MergeTool: Introducción
------------------------
eneboo-mergetool es una herramienta orientada a calcular diferencias entre ficheros
y a aplicarlas en diferentes contextos. Generalmente siempre se le proveerá de
la ruta exacta a los ficheros y carpetas. Esta herramienta se usa internamente por
eneboo-assembler, aunque puede ser conveniente usarla en determinados casos donde
el assembler no cubre el uso exacto que queremos darle.

MergeTool: Uso
-------------------

Para sacar una ayuda y listado de acciones::

    $ eneboo-mergetool --help


Para sacar más ayuda de una acción::

    $ eneboo-mergetool --help nombre-accion


MergeTool: Acciones disponibles
---------------------------------

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


MergeTool: FOLDER DIFF
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


MergeTool: FOLDER PATCH
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
pero con los parches aplicados. El fichero XML del parche debe encontrarse en la
carpeta *mi_parche*.



MergeTool: DIFF QS
----------------------

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



MergeTool: DIFF XML
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


MergeTool: FILE CHECK
-----------------------

Es posible comprobar los ficheros con eneboo-mergetool. Esta comprobación se limita 
(hasta ahora) a los ficheros QS y a una comprobación sobre los bloques y las clases.

Además es posible generar un fichero de "parche" para corregir los fallos típicos en
la creación de bloques class_declaration y definition::

    $ for i in $(find . -iname '*.qs'); do eneboo-mergetool file-check qs-classes $i --patch-dest mypatch -v; done
    $ patch -p1 < mypatch
    

Packager
-----------------------------

Esta herramienta permite empaquetar código eneboo en un sólo fichero .eneboopkg. Este tipo de ficheros presentan varias ventajas frente al código tradicional ordenado en carpetas de módulos, a saber:

- Se pueden importar de forma cómoda desde la opción *Sistema > Administración > Cargar Paquete de Módulos* de eneboo.
- Ocupan menos, ya que el código está comprimido.
- Son más fáciles de trasladar y descargar.

Para empaquetar un directorio que contenga código eneboo podemos usar::

    $ eneboo-packager create ruta_directorio_codigo -v
    
Para conocer todas las opciones de la herramienta::
    
    $ eneboo-packager --help




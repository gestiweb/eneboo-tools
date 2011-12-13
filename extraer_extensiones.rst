Cómo extraer una o varias extensiones de un proyecto
=====================================================

Tenemos un proyecto enviado por un tercero, y no sabemos qué extensiones tiene.
Creemos que algunas de las extensiones, pero no todas, las tenemos ya extraídas
y funcionando en el sistema. 

Para extraer las restantes, el procedimiento propuesto es el siguiente:

Calcular el parche entre el proyecto y los módulos
-----------------------------------------------------
Hay que tener en cuenta que los parches se deben calcular contra lo que se envia
, sin las personalizaciones propias. Cuantas menos personalizaciones tenga el 
proyecto, mejor.

Si es un proyecto de GIT, y se controló separadamente los envíos, hay que recordar
hacer un checkout a la rama apropiada.

Para calcular un parche manualmente, haríamos algo así::

    $ eneboo-mergetool folder-diff /tmp/projectpatch ~/git/eneboo-modules ~/git/abanq.modules/myproject/

Esto creará una carpeta /tmp/projectpatch (atención: en /tmp normalmente se borra
al reiniciar el equipo). 

Esta carpeta contiene las diferencias encontradas.

Creamos el proyecto interno
------------------------------
Usaremos la utilidad de autodetección de eneboo-assembler new para que nos cree
un proyecto::

    $ eneboo-assembler new prjX101-project "Proyecto miProyecto" /tmp/projectpatch

Esto nos creará un proyecto con una extensión "unida" que lo incluye todo, con 
extensiones que teníamos ya creadas incluso. Nos habrá detectado automáticamente
los módulos, pero no las extensiones, ya que el parche se extrayó desde los 
módulos oficiales.

Hay que recordar actualizar la base de datos de assembler:

    $ eneboo-assembler dbupdate

Crear carpeta de source
--------------------------
Antes de continuar, debemos compilar la carpeta de código fuente para que la tome
como referencia en el trabajo de extracción::

    $ eneboo-assembler build project src

Esto nos creará la carpeta build/src para el futuro.


Analizar las dependencias más extensivamente
----------------------------------------------

Para encontrar qué dependencias nos faltaban por agregar, usaremos la acción
test-deps, que analiza esto mucho más a fondo. Nos dará un listado de extensiones::

    $ eneboo-assembler test-deps project
    
Agregamos las extensiones que nos indica a conf/required_features.

Recompilamos los objetivos base y test-fullpatch::

    $ eneboo-assembler build project base

    $ eneboo-assembler build project test-fullpatch
    
Cuando termine el proceso, revisaremos más a fondo las diferencias usando kdiff3::

    $ cd path/to/project/build/
    $ kdiff3 base test-fullpatch
    
Analizaremos primero unos tipos de fichero más sencillos, y luego los más 
complejos, para intentar encontrar qué extensiones puedan haber más y hayan
pasado inadvertidas y determinar qué extensiones estamos extrayendo.

Cuando se modifican las dependencias, se debe recompilar "base", "fullpatch" y "test-fullpatch".

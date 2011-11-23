# encoding: UTF8
import enebootools.lib.peewee as peewee
from mypeewee import BaseModel

"""
    - índices:
        En la base de datos vamos a indexar los siguientes elementos:
        - módulos:
            Un listado de módulos, y dónde los hemos encontrado. Si un módulo se encuentra
            dos veces, se omite la segunda.
        - funcionalidades:
            Un listado de funcionalidades y dónde las hemos encontrado. Si una extensión
            aparece dos veces, la segunda vez se ignora.
        - fecha-hora última modificación:
            de los módulos y las funcionalidades, cual es la fecha-hora más reciente de los ficheros.
            Cuando este valor se actualiza, se lanzan disparadores de invalidación de cachés.
    - cachés:
        Vamos a hacer caché de los siguientes elementos:
        - builds parciales:
            qué variantes de los módulos se han compilado ya, dónde se han compilado 
            y qué versiones (fecha de modificación) se usaron para éstas.
                    
"""


class KnownObjects(BaseModel):
    objid = peewee.PrimaryKeyField()
    objtype = peewee.CharField()
    abspath = peewee.CharField()
    relpath = peewee.CharField()
    filename = peewee.CharField()
    timestamp = peewee.IntegerField()
    extradata = peewee.TextField()

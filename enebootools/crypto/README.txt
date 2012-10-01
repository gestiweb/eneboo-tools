Eneboo Crypto - Criptografía para Eneboo-Tools
==========================================================

Este módulo provee de funciones de firma digital para módulos de Eneboo.
La firma digital *no cifra ni enmascara* el código. Únicamente provee una forma
segura de garantizar que autor del código es quien dice ser y saber qué código 
ha podido ser modificado después de firmarlo.

Esta funcionalidad está aún en desarrollo y no está lista para usarse.


Diferencias con el sistema de firmas original de AbanQ 2.4
-----------------------------------------------------------
El sistema de firmas es algo que recuerda al sistema implantado originalmente
por InfoSiAL, pero en cambio, tiene poco o nada que ver. Las principales
diferencias son las siguientes:

 - El código no firmado digitalmente funcionará y se ejecutará exactamente igual
   que el código firmado.
 
 - Las firmas digitales hacen uso de los principales estándares para este ámbito: 
   Parejas de llaves RSA y Certificados X.509. Todo esto usando ficheros PEM.
   
 - Las firmas se pueden quitar fácilmente borrando ciertos ficheros. También
   se pueden desactivar selectivamente en el fichero *.signatures; por lo que
   no se impide en ningún caso el modificar el código hecho por otra persona.
   
 - Las compilaciones de Eneboo no requerirán en ningún caso de parámetros 
   ocultos, de forma que cualquiera puede compilar un ejecutable Eneboo idéntico
   al oficial. 
   
 - La firma digital compara prácticamente todos los ficheros del módulo:
   formularios, tablas, acciones, código fuente, querys e informes.
 
 - Cualquiera puede firmar, solo se necesita una pareja de claves RSA 
   (recomendamos 2048 bits) y un certificado digital para esa clave pública.
   (Eneboo admitirá certificados autofirmados, pero no les dará ningún 
   tratamiento especial)
   
 - La firma digital es ignorada por los ejecutables que no la soporten, por lo
   que no es necesario actualizarse para poder usar módulos firmados digitalmente.


Requisitos para firmar los módulos 
----------------------------------------------------

Antes de empezar, es necesario que tengamos una pareja de claves RSA y un 
certificado digital para la clave pública RSA.

Una de las formas es seguir los pasos que se dan aquí:
http://svn.osafoundation.org/m2crypto/trunk/doc/howto.ca.html

Otro método es usar el programa "XCA" que es gráfico.

Al final debemos exportar en una carpeta dos ficheros en formato PEM, uno para
la clave privada RSA y otro para el certificado digital X509. Vamos a llamar a
estos ficheros "myprivatersa.pem" y "mycertificate.pem".

El fichero "myprivatersa.pem" debe estar protegido con contraseña y tanto el 
fichero como la contraseña de éste deben permanecer en el más absoluto secreto.

El fichero "mycertificate.pem" contiene únicamente información pública, más una 
firma del "Issuer" que nos garantiza que el certificado es válido. Este fichero
se puede publicar vía web, email, o como deseemos. Es lo que usará el resto de
la gente para comprobar que nuestra firma es válida.

Toda persona que posea a la vez estos dos ficheros y la contraseña, tendrá poder
para firmar bajo el nombre del certificado.

Asumiremos que estos dos ficheros los tenemos guardados en la carpeta ~/myssl/


Firmar los módulos con eneboo-crypto
----------------------------------------------------
Este comando funciona únicamente desde la carpeta del módulo, por lo que 
tendremos que entrar en la carpeta del módulo a firmar:

~$ cd git/eneboo.modules/proyecto-cliente1/
~/git/eneboo.modules/proyecto-cliente1$ cd facturacion/almacen
~/git/eneboo.modules/proyecto-cliente1/facturacion/almacen$

Desde la carpeta, lo único que debemos hacer es:

$ eneboo-crypto sign ~/myssl/mycertificate.pem ~/myssl/myprivatersa.pem

Y nos pedirá la contraseña para abrir la clave privada.
Una vez terminado el proceso habrá creado tres ficheros:

 - flfactalma.certificates : Contiene el certificado que firma.
 - flfactalma-2999-99-99a.checksums : Contiene un resumen de firmas hash para todos los ficheros de este módulo.
 - flfactalma.signature : Contiene la firma en sí misma, donde relaciona el certificado con el fichero de checksum.


Comprobar si la firma es válida
--------------------------------------
Cuando se genera, se comprueba que sea válida para evitar errores. Si deseamos
saber si la firma de un módulo sigue siendo válida, podemos hacerlo ejecutando
la orden:

$ eneboo-crypto check

Y nos debe decir cuantas firmas son válidas o los errores encontrados.





    


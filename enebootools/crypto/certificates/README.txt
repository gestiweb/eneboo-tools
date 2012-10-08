En esta carpeta se incorporan los certificados útiles a la hora de validar la
cadena de confianza de los mismos.

Se incluye un certificado de pruebas. Este certificado trae una clave privada 
para poder generar a su vez certificados válidos a modo de prueba.

El password para clave la privada de "Partner_Test.pem" es "test.eneboo.com"

Las claves son RSA, de un tamaño de 2048bits para Partners y CA. El certificado
raíz es de 4096bits para mayor seguridad. Los certificados de prueba son de 
1024bits.


Eneboo crypto incorpora una lista de las firmas válidas para certificado raíz.
Estas firmas están en SHA-256. Para comprobar la firma de un certificado, hay
que ejecutar sha256sum sobre el certificado en formato binario (DER).

$ openssl x509 -in Eneboo_Open_Source_ERP.crt -outform der | sha256sum
bea4a766093b1c64725c030da7c655f39bbc8a9f50887ee7ba50e6020fe39864  -



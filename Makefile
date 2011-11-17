PWD=`pwd`

all:
	@echo "No se hace nada. Ejecute sudo make install para instalar."

install:
	@echo "La carpeta de trabajo local es: $(PWD)"
	ln -sf $(PWD)/eneboo-* /usr/local/bin



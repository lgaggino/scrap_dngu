Scraping de Aspirantes  
Consulta automatizada de títulos universitarios en el Registro Nacional de Graduados  

¿Qué hace este script?  
Este script permite automatizar la búsqueda de antecedentes académicos (título, institución, año de egreso) de un listado de personas en el Registro Nacional de Graduados de SIU.

Funciona a partir de un archivo `aspirantes.csv` y genera un nuevo archivo `aspirantes_con_datos.csv` con los campos completados automáticamente para cada persona.

El script:

- Realiza una búsqueda por DNI y/o por nombre y apellido en el sitio oficial del SIU.
- Identifica si hay coincidencias múltiples, sin resultados o con datos completos.
- Extrae los datos de institución, título y egreso cuando están disponibles.
- Muestra el progreso en tiempo real y una notificación al finalizar.
- Guarda los resultados en un archivo nuevo listo para ser analizado o auditado.

¿Para quién es?  
- Equipos de recursos humanos que validan antecedentes educativos.  
- Personal administrativo que requiere verificar egresos académicos de forma automatizada.

Requisitos mínimos  
- Python 3.9+  
- Google Chrome instalado  
- Driver de Chrome compatible con tu versión del navegador (`chromedriver`)  
- Sistema operativo: Windows (se usa Tkinter para interfaz gráfica)  
- RAM: 4 GB o más

Estructura del archivo de entrada
El archivo aspirantes.csv debe contener las siguientes columnas:
nombre
apellido
edad (opcional)
dni
puntaje (opcional)

Ejemplo:
nombre,apellido,edad,dni,puntaje  
Juan,Pérez,28,12345678,95  
Ana,Gómez,32,23456789,90

Salida generada
El script genera un archivo llamado aspirantes_con_datos.csv con los siguientes campos nuevos:
Institucion
Titulo
Egreso

Posibles valores:
Datos completos extraídos correctamente.
"No": no se encontraron resultados.
"Revisar manualmente": se detectaron múltiples coincidencias o errores.

Advertencias
Este script automatiza una consulta pública. Usar con criterio para evitar sobrecargar el sitio.

Las búsquedas con nombres/apellidos comunes pueden devolver múltiples resultados y deben revisarse manualmente.

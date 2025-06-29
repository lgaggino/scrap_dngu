import logging
import sys
import pandas as pd
import time
import unicodedata
import tkinter as tk
from tkinter import ttk

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Función para mostrar la ventana flotante de "Finalizado"
def mostrar_mensaje():
    root = tk.Tk()
    root.title("")
    root.lift()
    root.attributes('-topmost', True)

    frame = tk.Frame(root)
    frame.pack(padx=20, pady=20)

    label = tk.Label(frame, text="Finalizado", font=("Arial", 20), fg="black")
    label.pack(pady=20)

    boton_cerrar = tk.Button(frame, text="Cerrar", font=("Arial", 12), command=root.destroy)
    boton_cerrar.pack(pady=20)

    root.mainloop()

# Función para normalizar texto y eliminar acentos
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

# Leer el archivo CSV
try:
    aspirantes = pd.read_csv('aspirantes.csv', sep=',', quotechar='"', encoding='latin1')
except Exception as e:
    logging.error(f"Error al leer el archivo CSV: {e}")
    sys.exit(1)

# Verificar columnas
logging.info(f"Nombres de columnas originales: {aspirantes.columns.tolist()}")
if len(aspirantes.columns) == 1:
    logging.info("Separando manualmente las columnas...")
    aspirantes = aspirantes[aspirantes.columns[0]].str.split(',', expand=True)
    # Ajustar a la estructura real del CSV
    aspirantes.columns = ['nombre', 'apellido', 'edad', 'dni', 'puntaje'] 

logging.info(f"Nombres de columnas después de corregir: {aspirantes.columns.tolist()}")

required_columns = {'nombre', 'apellido', 'dni'}
if not required_columns.issubset(aspirantes.columns):
    logging.error(f"Faltan columnas obligatorias en el CSV. Se encontraron: {aspirantes.columns.tolist()}")
    sys.exit(1)

# Limpiar datos
aspirantes = aspirantes.applymap(lambda x: x.strip('"').strip() if isinstance(x, str) else x)

# Agregar columnas vacías
aspirantes['Institucion'] = None
aspirantes['Titulo'] = None
aspirantes['Egreso'] = None

# Configurar el driver de Chrome en modo headless
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920x1080')

try:
    driver = webdriver.Chrome(options=options)
except WebDriverException as e:
    logging.error(f"No se pudo iniciar el driver de Chrome: {e}")
    sys.exit(1)


def obtener_datos_egresado(dni, apellido, nombre, max_reintentos=3):
    """
    - Hace hasta 3 reintentos en caso de error o "no_resultados"/ "sin_resultados".
    - Si la búsqueda trae varias tablas con datos, devolvemos "multiples_resultados".
    - Si hay una sola tabla con datos, concatenamos todas sus filas en una sola tupla (instituciones, titulos, egresos).
    """
    intentos = 0
    ultimo_resultado = None

    while intentos < max_reintentos:
        try:
            driver.get("https://registrograduados.siu.edu.ar/")
            
            # Seleccionar tipo de documento
            tipo_documento = Select(driver.find_element(By.ID, 'ef_form_2308_filtroid_tipo_documento'))
            
            if not dni.strip():
                tipo_documento.select_by_visible_text('-- Seleccione una opción --')
            else:
                tipo_documento.select_by_visible_text('Documento Nacional de Identidad')
                documento = driver.find_element(By.ID, 'ef_form_2308_filtrodocumento')
                documento.clear()
                documento.send_keys(dni)

            # Limpiar y normalizar textos
            campo_apellido = driver.find_element(By.ID, 'ef_form_2308_filtroapellido')
            campo_apellido.clear()
            campo_apellido.send_keys(normalizar_texto(apellido))

            campo_nombre = driver.find_element(By.ID, 'ef_form_2308_filtronombre')
            campo_nombre.clear()
            campo_nombre.send_keys(normalizar_texto(nombre))

            # Click en "Filtrar"
            boton_busqueda = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'form_2308_filtro_filtrar'))
            )
            boton_busqueda.click()

            # Esperar a que aparezca la tabla o "No se encontraron resultados"
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="overlay_contenido"]/div[2]/div')),
                        EC.presence_of_element_located((By.XPATH, '//*[@id="cuerpo_js_cuadro_2309_cuadro_sicer"]'))
                    )
                )
            except TimeoutException:
                ultimo_resultado = "sin_resultados"
                intentos += 1
                time.sleep(2)
                continue

            # Verificar cartel "No se encontraron resultados"
            try:
                cartel = driver.find_element(By.XPATH, '//*[@id="overlay_contenido"]/div[2]/div').text
                if "No se encontraron resultados" in cartel:
                    ultimo_resultado = "no_resultados"
                    intentos += 1
                    time.sleep(2)
                    continue
            except NoSuchElementException:
                pass

            # Buscar las tablas principales
            try:
                bloques = driver.find_elements(By.XPATH, '//*[@id="cuerpo_js_cuadro_2309_cuadro_sicer"]/tbody/tr[2]/td/table')
            except NoSuchElementException:
                ultimo_resultado = "sin_resultados"
                intentos += 1
                time.sleep(2)
                continue

            # Si no hay tablas, "sin_resultados"
            if not bloques:
                ultimo_resultado = "sin_resultados"
                intentos += 1
                time.sleep(2)
                continue

            # Filtrar sólo las tablas que realmente tengan filas de datos
            tablas_con_datos = []
            for bloque in bloques:
                filas = bloque.find_elements(By.XPATH, './/tbody/tr')
                tiene_datos = False
                for fila in filas:
                    try:
                        inst = fila.find_element(By.XPATH, './/td[5]').text
                        tit = fila.find_element(By.XPATH, './/td[6]').text
                        egr = fila.find_element(By.XPATH, './/td[7]').text
                        if ("Institución" in inst) or ("Título" in tit) or ("Egreso" in egr):
                            continue
                        if inst and tit and egr:
                            tiene_datos = True
                            break
                    except NoSuchElementException:
                        continue
                if tiene_datos:
                    tablas_con_datos.append(bloque)

            if len(tablas_con_datos) == 0:
                ultimo_resultado = "sin_resultados"
                intentos += 1
                time.sleep(2)
                continue
            elif len(tablas_con_datos) > 1:
                # Varias tablas con datos => varias posibles personas
                return "multiples_resultados"
            else:
                # Exactamente 1 tabla con datos => parsear y concatenar
                bloque_unico = tablas_con_datos[0]
                instituciones = []
                titulos = []
                egresos = []

                filas = bloque_unico.find_elements(By.XPATH, './/tbody/tr')
                for fila in filas:
                    try:
                        inst = fila.find_element(By.XPATH, './/td[5]').text
                        tit = fila.find_element(By.XPATH, './/td[6]').text
                        egr = fila.find_element(By.XPATH, './/td[7]').text
                        
                        if ("Institución" in inst) or ("Título" in tit) or ("Egreso" in egr):
                            continue

                        if inst and tit and egr:
                            instituciones.append(inst)
                            titulos.append(tit)
                            egresos.append(egr)

                    except NoSuchElementException:
                        continue

                if instituciones:
                    institucion_str = " || ".join(instituciones)
                    titulo_str = " || ".join(titulos)
                    egreso_str = " || ".join(egresos)
                    return (institucion_str, titulo_str, egreso_str)
                else:
                    ultimo_resultado = "sin_resultados"
                    intentos += 1
                    time.sleep(2)

        except (NoSuchElementException, TimeoutException, WebDriverException) as e:
            logging.warning(
                f"Error al obtener datos para DNI={dni}, Apellido={apellido}, "
                f"Nombre={nombre}, intento {intentos + 1}: {e}"
            )
            intentos += 1
            time.sleep(2)

    # Sin "return", devolvemos lo último que tengamos
    if ultimo_resultado is None:
        ultimo_resultado = "sin_resultados"
    return ultimo_resultado

# Crear ventana de progreso
root = tk.Tk()
root.title("Progreso")
root.geometry("400x150")
root.resizable(False, False)

frame = tk.Frame(root)
frame.pack(pady=20)

label = tk.Label(frame, text="Progreso: 0%", font=("Arial", 14))
label.pack(pady=10)

progress = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
progress.pack()

root.update()

# Procesar aspirantes con progreso
total_registros = len(aspirantes)

for index, row in aspirantes.iterrows():
    dni = str(row['dni']).strip()
    apellido = normalizar_texto(str(row['apellido']).strip())
    nombre = normalizar_texto(str(row['nombre']).strip())

    resultado = obtener_datos_egresado(dni, apellido, nombre)

    if resultado == "no_resultados":
        aspirantes.at[index, 'Institucion'] = "No"
        aspirantes.at[index, 'Titulo'] = "No"
        aspirantes.at[index, 'Egreso'] = "No"
    elif resultado == "sin_resultados":
        aspirantes.at[index, 'Institucion'] = "Revisar manualmente"
        aspirantes.at[index, 'Titulo'] = "Revisar manualmente"
        aspirantes.at[index, 'Egreso'] = "Revisar manualmente"
    elif resultado == "multiples_resultados":
        aspirantes.at[index, 'Institucion'] = "Revisar manualmente"
        aspirantes.at[index, 'Titulo'] = "Revisar manualmente"
        aspirantes.at[index, 'Egreso'] = "Revisar manualmente"
    else:
        institucion_str, titulo_str, egreso_str = resultado
        aspirantes.at[index, 'Institucion'] = institucion_str
        aspirantes.at[index, 'Titulo'] = titulo_str
        aspirantes.at[index, 'Egreso'] = egreso_str

    # Actualizar progreso
    porcentaje = int(((index + 1) / total_registros) * 100)
    label.config(text=f"Progreso: {porcentaje}%")
    progress["value"] = porcentaje
    root.update()

# Cerrar ventana de progreso
root.destroy()

# Guardar resultados
try:
    aspirantes.to_csv('aspirantes_con_datos.csv', index=False, encoding='utf-8-sig', na_rep='')
    logging.info("Archivo 'aspirantes_con_datos.csv' guardado correctamente.")
except Exception as e:
    logging.error(f"No se pudo guardar el archivo de resultados: {e}")

# Cerrar el driver y mostrar mensaje final
driver.quit()
mostrar_mensaje()

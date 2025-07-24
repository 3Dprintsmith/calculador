import chardet
import pandas as pd
from io import BytesIO
import streamlit as st

def detectar_separador(file_bytes):
    """Detecta si el CSV usa ',' o ';' como separador."""
    muestra = file_bytes.decode("utf-8", errors="ignore")[:1024]
    if muestra.count(";") > muestra.count(","):
        return ";"
    return ","

def cargar_archivo(uploaded_file):
    """
    Carga robusta de archivos CSV o XLSX detectando encoding y separador.
    Devuelve un DataFrame o None.
    """
    if uploaded_file is None:
        return None

    try:
        if uploaded_file.name.endswith(".csv"):
            file_bytes = uploaded_file.read()
            encoding = chardet.detect(file_bytes)["encoding"] or "utf-8"
            sep = detectar_separador(file_bytes)
            df = pd.read_csv(BytesIO(file_bytes), encoding=encoding, sep=sep)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        return None

    st.info(f"Columnas detectadas: {list(df.columns)}")
    st.dataframe(df.head(), use_container_width=True)
    return df

# Ejemplo de uso en tu app Streamlit:
uploaded_piezas = st.file_uploader("Sube tu archivo de piezas (CSV o XLSX)", type=["csv", "xlsx"])
df_piezas = cargar_archivo(uploaded_piezas)

if df_piezas is not None:
    st.success("Archivo cargado correctamente y listo para procesar.")
    # Aquí continúa tu lógica de procesamiento...

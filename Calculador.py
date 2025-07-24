import math
from io import BytesIO

import chardet
import pandas as pd
import streamlit as st

"""
App Streamlit – Cálculo de consumo de tableros, formicas y cantos
-----------------------------------------------------------------
Características:
- Carga de archivos (CSV/XLSX) con la lista de piezas a cortar.
- Manejo de materiales por separado (MDF RH 18 / 15 / 2.7, Madecor, Madefondo, Formicas, etc.).
- Consideración de orientación de veta (H / V / LIBRE) para validar dimensiones contra el formato.
- Cálculo de m² totales por material/espesor y número de planchas necesarias.
- Cálculo de metros lineales de canto por tipo.
- Descarga de resultados a Excel.

Estructura esperada de los archivos:
1) **Piezas (tableros / formicas)**
   Columnas mínimas:
   - Nombre (str)
   - Material (str)
   - Espesor_mm (float/int)
   - Largo_mm (float/int)
   - Ancho_mm (float/int)
   - Cantidad (int)
   - OrientacionVeta (str: "H", "V" o "LIBRE")

2) **Cantos**
   Columnas mínimas:
   - Tipo (str)  (ej: "Canto_blanco_22x0.5", "Canto_blanco_22x15")
   - Longitud_mm (float/int)
   - Cantidad (int)

Puedes editar el mapeo de formatos por material desde la propia app.
"""

st.set_page_config(page_title="Consumo de tableros, formicas y cantos", layout="wide")
st.title("📐 Consumo de tableros, formicas y cantos")
st.caption("Calculadora interactiva en Streamlit – con control de vetas")

# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------

def to_m2(largo_mm: float, ancho_mm: float, cantidad: int) -> float:
    return (largo_mm * ancho_mm * cantidad) / 1_000_000


def ceil_div(a: float, b: float) -> int:
    return math.ceil(a / b) if b else 0


def normaliza_material(s: str) -> str:
    return str(s).strip().upper().replace(" ", "_")


def make_download_link_excel(dfs: dict, filename: str = "resumen_consumos.xlsx"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for sheet, df in dfs.items():
            df.to_excel(writer, index=False, sheet_name=sheet[:31])
    st.download_button(
        label="⬇️ Descargar Excel con resultados",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def detectar_separador(file_bytes):
    """Detecta el separador más probable en un archivo CSV."""
    sample = file_bytes.decode("utf-8", errors="ignore")
    if sample.count(";") > sample.count(","):
        return ";"
    return ","


def corregir_nombres_columnas(cols, mapping):
    """Corrige nombres de columnas usando un mapping flexible."""
    cols_corr = []
    for c in cols:
        c_norm = c.strip().lower().replace(" ", "_")
        encontrado = False
        for canonico, variantes in mapping.items():
            if c_norm in variantes:
                cols_corr.append(canonico)
                encontrado = True
                break
        if not encontrado:
            cols_corr.append(c)
    return cols_corr


def cargar_archivo_piezas(uploaded_file, columnas_esperadas, mapping_columnas):
    """Carga robusta de archivos CSV/XLSX, detecta separador y corrige nombres."""
    if uploaded_file is None:
        return None, None

    try:
        if uploaded_file.name.endswith(".csv"):
            # Detectar encoding y separador
            file_bytes = uploaded_file.read()
            encoding = chardet.detect(file_bytes)["encoding"] or "utf-8"
            sep = detectar_separador(file_bytes)
            df = pd.read_csv(BytesIO(file_bytes), sep=sep, encoding=encoding)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        return None, None

    # Corregir nombres de columnas
    df.columns = corregir_nombres_columnas(df.columns, mapping_columnas)

    # Mostrar columnas detectadas y primeras filas
    st.info(f"Columnas detectadas: {list(df.columns)}")
    st.dataframe(df.head(), use_container_width=True)

    # Validar columnas requeridas
    faltantes = [col for col in columnas_esperadas if col not in df.columns]
    if faltantes:
        st.warning(f"⚠️ Faltan columnas requeridas: {faltantes}")
        return None, df  # Devuelve el df para inspección, pero no procesa

    return df, None


# ------------------------------------------------------------------
# Base de datos de formatos por material (puedes editarla en la app)
# ------------------------------------------------------------------

formato_default = pd.DataFrame(
    [
        {"Material_key": "MADECOR_MUF_BLANCO", "Espesor_mm": 15, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "MDF_RH", "Espesor_mm": 18, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "MDF_RH", "Espesor_mm": 15, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "MDF_2_7", "Espesor_mm": 2.7, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "MDF_UNICOR_MUF_NEVADO", "Espesor_mm": 18, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "MADEFONDO_MUF_BLANCO", "Espesor_mm": 5.5, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1830},
        {"Material_key": "FORMICA_BLANCA_NIEVE_2102", "Espesor_mm": 0.8, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1220},
        {"Material_key": "FORMICA_FASHION_WHITE_IT_2125", "Espesor_mm": 0.8, "Largo_formato_mm": 2440, "Ancho_formato_mm": 1220},
    ]
)

st.sidebar.header("⚙️ Parámetros")
st.sidebar.write("**Edita los formatos por material/espesor** (si tu proveedor usa otro formato):")
formatos_user = st.sidebar.data_editor(
    formato_default.copy(),
    num_rows="dynamic",
    use_container_width=True,
    key="formatos_user",
)

# ------------------------------------------------------------------
# Carga de archivos
# ------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(["Piezas (tableros / formicas)", "Cantos", "Plantillas & Ayuda"])  # noqa: E231

with tab1:
    uploaded_piezas = st.file_uploader("Sube tu archivo de piezas (CSV o XLSX)", type=["csv", "xlsx"])

    if uploaded_piezas is None:
        st.info("Sube tu archivo para comenzar, o usa el ejemplo en la pestaña 'Plantillas & Ayuda'.")
        df_piezas = None
    else:
        # --- Configura tus columnas esperadas y mapping de nombres ---
        columnas_esperadas = [
            "Nombre", "Material", "Espesor_mm", "Largo_mm", "Ancho_mm", "Cantidad", "OrientacionVeta"
        ]
        mapping_columnas = {
            "Nombre": {"nombre", "name"},
            "Material": {"material"},
            "Espesor_mm": {"espesor_mm", "espesor", "grosor", "thickness"},
            "Largo_mm": {"largo_mm", "largo", "longitud", "alto", "altura", "length", "height"},
            "Ancho_mm": {"ancho_mm", "ancho", "width"},
            "Cantidad": {"cantidad", "qty", "cantidad_piezas", "numero"},
            "OrientacionVeta": {"orientacionveta", "veta", "orientacion", "orientación", "orientacion_veta"},
        }

        df_piezas, error_df = cargar_archivo_piezas(uploaded_piezas, columnas_esperadas, mapping_columnas)
        if error_df is not None:
            st.info("Corrige tu archivo y vuelve a intentarlo.")
        elif df_piezas is not None:
            st.success("Archivo cargado correctamente y listo para procesar.")
            # Aquí continúa tu lógica de procesamiento...

            # Normalización de claves de materiales para empatar con la tabla de formatos
            df_piezas["Material_key"] = df_piezas["Material"].apply(normaliza_material)
            formatos_user["Material_key"] = formatos_user["Material_key"].apply(normaliza_material)

            # Merge para traer largo/ancho de formato (si el usuario no lo puso en la fila)
            df_merge = pd.merge(
                df_piezas,
                formatos_user,
                how="left",
                left_on=["Material_key", "Espesor_mm"],
                right_on=["Material_key", "Espesor_mm"],
                suffixes=("", "_fmt"),
            )

            # Si el usuario especificó manualmente Largo_formato_mm/Ancho_formato_mm en df_piezas, respétalo; si no, usa el del merge
            if "Largo_formato_mm" not in df_merge.columns:
                df_merge["Largo_formato_mm"] = df_merge["Largo_formato_mm_fmt"]
            else:
                df_merge["Largo_formato_mm"] = df_merge["Largo_formato_mm"].fillna(df_merge["Largo_formato_mm_fmt"])
            if "Ancho_formato_mm" not in df_merge.columns:
                df_merge["Ancho_formato_mm"] = df_merge["Ancho_formato_mm_fmt"]
            else:
                df_merge["Ancho_formato_mm"] = df_merge["Ancho_formato_mm"].fillna(df_merge["Ancho_formato_mm_fmt"])

            # Cálculo de áreas
            df_merge["Area_m2"] = (
                df_merge["Largo_mm"] * df_merge["Ancho_mm"] * df_merge["Cantidad"] / 1_000_000
            )

            # Área de la plancha
            df_merge["Area_plancha_m2"] = (
                df_merge["Largo_formato_mm"] * df_merge["Ancho_formato_mm"] / 1_000_000
            )

            # Validación básica de vetas (no optimiza, solo avisa)
            def valida_veta(row):
                orient = str(row.get("OrientacionVeta", "LIBRE")).upper()
                Lp = row["Largo_mm"]
                Ap = row["Ancho_mm"]
                Lf = row["Largo_formato_mm"]
                Af = row["Ancho_formato_mm"]
                if orient == "LIBRE" or pd.isna(Lf) or pd.isna(Af):
                    return "OK"
                # Consideramos la veta a lo largo del LARGO del formato (Lf)
                # H => la veta de la pieza va a lo largo del LARGO de la pieza; entonces Lp debe caber en Lf
                # V => la veta va a lo largo del ANCHO de la pieza; entonces Ap debe caber en Lf
                try:
                    if orient == "H" and Lp > max(Lf, Af):
                        return "Largo pieza > largo vetado del formato"
                    if orient == "V" and Ap > max(Lf, Af):
                        return "Ancho pieza > largo vetado del formato"
                    return "OK"
                except Exception:
                    return "OK"

            df_merge["Check_veta"] = df_merge.apply(valida_veta, axis=1)

            st.subheader("Resultado por pieza (con validación de veta)")
            st.dataframe(df_merge, use_container_width=True, height=400)

            # Resumen por material/espesor
            resumen = (
                df_merge.groupby(["Material", "Material_key", "Espesor_mm", "Area_plancha_m2"], dropna=False)["Area_m2"]
                .sum()
                .reset_index()
            )
            resumen["Planchas_necesarias"] = resumen.apply(
                lambda r: ceil_div(r["Area_m2"], r["Area_plancha_m2"]) if r["Area_plancha_m2"] > 0 else 0,
                axis=1,
            )
            resumen["Rendimiento_%"] = (
                (resumen["Area_m2"] / (resumen["Planchas_necesarias"] * resumen["Area_plancha_m2"]).replace(0, pd.NA))
                * 100
            )

            st.subheader("🧾 Resumen por material / espesor")
            st.dataframe(resumen, use_container_width=True)

            # Avance: flags de veta problemáticos
            problemas_veta = df_merge[df_merge["Check_veta"] != "OK"]
            if len(problemas_veta):
                st.warning("⚠️ Se encontraron piezas que podrían violar la orientación de la veta.")
                st.dataframe(problemas_veta, use_container_width=True)

            # ------------------------------------------------------------------
            # CANTOS
            # ------------------------------------------------------------------
            if df_cantos is not None:
                df_cantos = df_cantos.copy()
                df_cantos["Tipo"] = df_cantos["Tipo"].astype(str)
                df_cantos["Metros_lineales"] = df_cantos["Longitud_mm"] * df_cantos["Cantidad"] / 1000
                cantos_resumen = df_cantos.groupby("Tipo")["Metros_lineales"].sum().reset_index()

                st.subheader("📏 Metros lineales de canto por tipo")
                st.dataframe(cantos_resumen, use_container_width=True)
            else:
                cantos_resumen = pd.DataFrame(columns=["Tipo", "Metros_lineales"])  # vacío

            # Descarga a Excel
            make_download_link_excel(
                {
                    "Piezas_con_vetas": df_merge,
                    "Resumen_materiales": resumen,
                    "Cantos": cantos_resumen,
                }
            )

with tab2:
    uploaded_cantos = st.file_uploader("Sube tu archivo de cantos (CSV o XLSX)", type=["csv", "xlsx"], key="cantos")

    if uploaded_cantos is None:
        df_cantos = None
    else:
        if uploaded_cantos.name.endswith(".csv"):
            df_cantos = pd.read_csv(uploaded_cantos, sep=",", decimal=".")
        else:
            df_cantos = pd.read_excel(uploaded_cantos)

        st.subheader("Cantos cargados")
        st.dataframe(df_cantos, use_container_width=True, height=250)

with tab3:
    st.markdown("""
    ### 📄 Plantilla de **Piezas** (CSV/XLSX)
    Columnas mínimas:
    - **Nombre**
    - **Material** (ej: MDF RH, Madecor MUF Blanco, Formica Fashion White IT 2125, etc.)
    - **Espesor_mm** (ej: 18, 15, 2.7, 0.8)
    - **Largo_mm**
    - **Ancho_mm**
    - **Cantidad**
    - **OrientacionVeta** ("H" = veta paralela al largo de la plancha (2440), "V" = paralela al ancho (1830 o 1220), "LIBRE")

    Opcionales:
    - **Largo_formato_mm** / **Ancho_formato_mm** (si quieres sobreescribir el formato por fila)

    ---

    ### 📄 Plantilla de **Cantos** (CSV/XLSX)
    Columnas mínimas:
    - **Tipo** (ej: Canto_blanco_22x0.5, Canto_blanco_22x15)
    - **Longitud_mm**
    - **Cantidad**
    """)

    st.write("Ejemplo mínimo de **piezas**:")
    ejemplo_piezas = pd.DataFrame({
        "Nombre": ["Base", "Internos-laterales"],
        "Material": ["MADECOR MUF BLANCO", "MDF RH"],
        "Espesor_mm": [15, 18],
        "Largo_mm": [1829, 1003],
        "Ancho_mm": [1003, 594],
        "Cantidad": [1, 2],
        "OrientacionVeta": ["H", "LIBRE"],
    })
    st.dataframe(ejemplo_piezas, use_container_width=True)

    st.write("Ejemplo mínimo de **cantos**:")
    ejemplo_cantos = pd.DataFrame({
        "Tipo": ["Canto_blanco_22x0.5", "Canto_blanco_22x15"],
        "Longitud_mm": [1634, 180.5],
        "Cantidad": [2, 2],
    })
    st.dataframe(ejemplo_cantos, use_container_width=True)

# ------------------------------------------------------------------
# Procesamiento si hay datos cargados
# ------------------------------------------------------------------

if df_piezas is not None:
    # Normalización de claves de materiales para empatar con la tabla de formatos
    df_piezas["Material_key"] = df_piezas["Material"].apply(normaliza_material)
    formatos_user["Material_key"] = formatos_user["Material_key"].apply(normaliza_material)

    # Merge para traer largo/ancho de formato (si el usuario no lo puso en la fila)
    df_merge = pd.merge(
        df_piezas,
        formatos_user,
        how="left",
        left_on=["Material_key", "Espesor_mm"],
        right_on=["Material_key", "Espesor_mm"],
        suffixes=("", "_fmt"),
    )

    # Si el usuario especificó manualmente Largo_formato_mm/Ancho_formato_mm en df_piezas, respétalo; si no, usa el del merge
    if "Largo_formato_mm" not in df_merge.columns:
        df_merge["Largo_formato_mm"] = df_merge["Largo_formato_mm_fmt"]
    else:
        df_merge["Largo_formato_mm"] = df_merge["Largo_formato_mm"].fillna(df_merge["Largo_formato_mm_fmt"])
    if "Ancho_formato_mm" not in df_merge.columns:
        df_merge["Ancho_formato_mm"] = df_merge["Ancho_formato_mm_fmt"]
    else:
        df_merge["Ancho_formato_mm"] = df_merge["Ancho_formato_mm"].fillna(df_merge["Ancho_formato_mm_fmt"])

    # Cálculo de áreas
    df_merge["Area_m2"] = (
        df_merge["Largo_mm"] * df_merge["Ancho_mm"] * df_merge["Cantidad"] / 1_000_000
    )

    # Área de la plancha
    df_merge["Area_plancha_m2"] = (
        df_merge["Largo_formato_mm"] * df_merge["Ancho_formato_mm"] / 1_000_000
    )

    # Validación básica de vetas (no optimiza, solo avisa)
    def valida_veta(row):
        orient = str(row.get("OrientacionVeta", "LIBRE")).upper()
        Lp = row["Largo_mm"]
        Ap = row["Ancho_mm"]
        Lf = row["Largo_formato_mm"]
        Af = row["Ancho_formato_mm"]
        if orient == "LIBRE" or pd.isna(Lf) or pd.isna(Af):
            return "OK"
        # Consideramos la veta a lo largo del LARGO del formato (Lf)
        # H => la veta de la pieza va a lo largo del LARGO de la pieza; entonces Lp debe caber en Lf
        # V => la veta va a lo largo del ANCHO de la pieza; entonces Ap debe caber en Lf
        try:
            if orient == "H" and Lp > max(Lf, Af):
                return "Largo pieza > largo vetado del formato"
            if orient == "V" and Ap > max(Lf, Af):
                return "Ancho pieza > largo vetado del formato"
            return "OK"
        except Exception:
            return "OK"

    df_merge["Check_veta"] = df_merge.apply(valida_veta, axis=1)

    st.subheader("Resultado por pieza (con validación de veta)")
    st.dataframe(df_merge, use_container_width=True, height=400)

    # Resumen por material/espesor
    resumen = (
        df_merge.groupby(["Material", "Material_key", "Espesor_mm", "Area_plancha_m2"], dropna=False)["Area_m2"]
        .sum()
        .reset_index()
    )
    resumen["Planchas_necesarias"] = resumen.apply(
        lambda r: ceil_div(r["Area_m2"], r["Area_plancha_m2"]) if r["Area_plancha_m2"] > 0 else 0,
        axis=1,
    )
    resumen["Rendimiento_%"] = (
        (resumen["Area_m2"] / (resumen["Planchas_necesarias"] * resumen["Area_plancha_m2"]).replace(0, pd.NA))
        * 100
    )

    st.subheader("🧾 Resumen por material / espesor")
    st.dataframe(resumen, use_container_width=True)

    # Avance: flags de veta problemáticos
    problemas_veta = df_merge[df_merge["Check_veta"] != "OK"]
    if len(problemas_veta):
        st.warning("⚠️ Se encontraron piezas que podrían violar la orientación de la veta.")
        st.dataframe(problemas_veta, use_container_width=True)

    # ------------------------------------------------------------------
    # CANTOS
    # ------------------------------------------------------------------
    if df_cantos is not None:
        df_cantos = df_cantos.copy()
        df_cantos["Tipo"] = df_cantos["Tipo"].astype(str)
        df_cantos["Metros_lineales"] = df_cantos["Longitud_mm"] * df_cantos["Cantidad"] / 1000
        cantos_resumen = df_cantos.groupby("Tipo")["Metros_lineales"].sum().reset_index()

        st.subheader("📏 Metros lineales de canto por tipo")
        st.dataframe(cantos_resumen, use_container_width=True)
    else:
        cantos_resumen = pd.DataFrame(columns=["Tipo", "Metros_lineales"])  # vacío

    # Descarga a Excel
    make_download_link_excel(
        {
            "Piezas_con_vetas": df_merge,
            "Resumen_materiales": resumen,
            "Cantos": cantos_resumen,
        }
    )

else:
    st.info("Carga tus datos para ver los cálculos.")

st.markdown("---")
st.caption(
    "App generada por Streamlit. Puedes desplegarla gratis en Streamlit Community Cloud con tu repo de GitHub."
)

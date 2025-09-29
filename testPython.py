#!/usr/bin/env python3
"""
EDA de imágenes por página de PDF
---------------------------------
Suposiciones:
- Tienes un PDF base (p. ej., "E-4034-21-05-2025 EDIFICIO TELLO.pdf").
- Tienes una carpeta "VIEW SCREENSHOTS" con subcarpetas "01", "02", ... donde
  cada carpeta corresponde a una página del PDF.
- Dentro de cada subcarpeta hay imágenes (PNG/JPG) capturadas de esa página.

Qué hace:
- Cuenta páginas del PDF (si está instalado PyPDF2).
- Recorre TODAS las imágenes de TODAS las carpetas (01..NN).
- Calcula tamaño (KB), resolución (ancho/alto), megapíxeles y formato por imagen.
- Agrega por página: # imágenes, tamaño promedio, ancho/alto promedio.
- Genera gráficos (uno por figura) y CSVs con resúmenes.

Uso:
- Ajusta rutas en la sección CONFIG si quieres.
- Ejecuta:  python eda_images_by_pdf_page.py

Requerimientos:
- pillow, matplotlib, pandas, PyPDF2
  (instala con: pip install pillow matplotlib pandas PyPDF2)
"""

import os
import re
from typing import List

import pandas as pd
import matplotlib.pyplot as plt

try:
    from PIL import Image
except Exception as e:
    raise SystemExit("Necesitas instalar pillow: pip install pillow") from e

# PyPDF2 es opcional, pero recomendado para contar páginas.
try:
    import PyPDF2
    HAVE_PYPDF2 = True
except Exception:
    HAVE_PYPDF2 = False

# =====================
# CONFIG (ajusta aquí)
# =====================
PDF_PATH = "/Users/cardan/Documents/MultimodalRAG/doc/doc/Edificio Tello/E-4034-21-05-2025 EDIFICIO TELLO.pdf"   # ruta al PDF
SCREENSHOTS_DIR = "/Users/cardan/Documents/MultimodalRAG/doc/doc/Edificio Tello/VIEW SCREENSHOTS"                # carpeta con 01, 02, ...
OUTPUT_DIR = "/Users/cardan/Documents/MultimodalRAG/eda_output"                           # salida para figuras/CSVs


def ensure_out():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def count_pdf_pages(pdf_path: str) -> int:
    if HAVE_PYPDF2 and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    return -1  # desconocido


def is_img(fn: str) -> bool:
    return fn.lower().endswith((".png", ".jpg", ".jpeg"))


def folder_is_page(name: str) -> bool:
    # acepta "01", "1", "12" ...
    return bool(re.fullmatch(r"\d{1,3}", name))


def page_key(name: str) -> str:
    # normaliza a dos dígitos si es posible
    if name.isdigit():
        return f"{int(name):02d}"
    return name


def scan_images(base_dir: str) -> pd.DataFrame:
    rows: List[list] = []
    if not os.path.isdir(base_dir):
        print(f"[WARN] Directorio no existe: {base_dir}")
        return pd.DataFrame(columns=[
            "pdf_page", "filename", "format", "size_kb", "width", "height", "mpix", "path"
        ])

    for entry in sorted(os.listdir(base_dir)):
        entry_path = os.path.join(base_dir, entry)
        if os.path.isdir(entry_path) and folder_is_page(entry):
            page = page_key(entry)
            for fn in sorted(os.listdir(entry_path)):
                if is_img(fn):
                    p = os.path.join(entry_path, fn)
                    try:
                        size_kb = os.path.getsize(p) / 1024.0
                    except Exception:
                        size_kb = float("nan")
                    try:
                        with Image.open(p) as im:
                            w, h = im.size
                            fmt = (im.format or os.path.splitext(fn)[1].strip(".")).upper()
                    except Exception:
                        w, h, fmt = float("nan"), float("nan"), os.path.splitext(fn)[1].strip(".").upper()
                    mpix = (w * h) / 1_000_000 if (isinstance(w, (int, float)) and isinstance(h, (int, float))) else float("nan")
                    rows.append([page, fn, fmt, size_kb, w, h, mpix, p])

        # también consideramos imágenes sueltas directamente dentro de SCREENSHOTS_DIR
        elif os.path.isfile(entry_path) and is_img(entry):
            p = entry_path
            try:
                size_kb = os.path.getsize(p) / 1024.0
            except Exception:
                size_kb = float("nan")
            try:
                with Image.open(p) as im:
                    w, h = im.size
                    fmt = (im.format or os.path.splitext(entry)[1].strip(".")).upper()
            except Exception:
                w, h, fmt = float("nan"), float("nan"), os.path.splitext(entry)[1].strip(".").upper()
            mpix = (w * h) / 1_000_000 if (isinstance(w, (int, float)) and isinstance(h, (int, float))) else float("nan")
            rows.append(["otros", entry, fmt, size_kb, w, h, mpix, p])

    df = pd.DataFrame(
        rows,
        columns=["pdf_page", "filename", "format", "size_kb", "width", "height", "mpix", "path"]
    )
    return df


def make_plots(df: pd.DataFrame, pdf_pages_total: int):
    ensure_out()

    # --- Conteo de imágenes por página ---
    if not df.empty:
        count_by_page = df.groupby("pdf_page").size().reindex(sorted(df["pdf_page"].unique()), fill_value=0)
        ax = count_by_page.plot(kind="bar", figsize=(10, 5))
        ax.set_title("Número de imágenes por página del PDF")
        ax.set_xlabel("Página (carpeta)")
        ax.set_ylabel("Cantidad de imágenes")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_images_per_pdf_page.png"), dpi=160)
        plt.close(fig)

    # --- Tamaño promedio (KB) por página ---
    if not df.empty:
        avg_size = df.groupby("pdf_page")["size_kb"].mean()
        ax = avg_size.plot(kind="bar", figsize=(10, 5))
        ax.set_title("Tamaño promedio de imágenes por página (KB)")
        ax.set_xlabel("Página (carpeta)")
        ax.set_ylabel("KB promedio")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_avg_size_per_page.png"), dpi=160)
        plt.close(fig)

    # --- Resolución promedio (ancho/alto) por página ---
    if not df.empty:
        avg_dims = df.groupby("pdf_page")[["width", "height"]].mean()
        ax = avg_dims["width"].plot(kind="bar", figsize=(10, 5))
        ax.set_title("Ancho promedio por página (px)")
        ax.set_xlabel("Página (carpeta)")
        ax.set_ylabel("px")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_avg_width_per_page.png"), dpi=160)
        plt.close(fig)

        ax = avg_dims["height"].plot(kind="bar", figsize=(10, 5))
        ax.set_title("Alto promedio por página (px)")
        ax.set_xlabel("Página (carpeta)")
        ax.set_ylabel("px")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_avg_height_per_page.png"), dpi=160)
        plt.close(fig)

    # --- Distribución de anchos y altos (histogramas) ---
    if not df.empty:
        ax = df["width"].dropna().plot(kind="hist", bins=20, figsize=(10,5))
        ax.set_title("Distribución de anchos de imagen (px)")
        ax.set_xlabel("Ancho (px)")
        ax.set_ylabel("Frecuencia")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_hist_widths.png"), dpi=160)
        plt.close(fig)

        ax = df["height"].dropna().plot(kind="hist", bins=20, figsize=(10,5))
        ax.set_title("Distribución de altos de imagen (px)")
        ax.set_xlabel("Alto (px)")
        ax.set_ylabel("Frecuencia")
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_hist_heights.png"), dpi=160)
        plt.close(fig)

    # --- Formatos (pie chart) ---
    if not df.empty:
        fmt_counts = df["format"].value_counts()
        fig, ax = plt.subplots(figsize=(6,6))
        ax.pie(fmt_counts.values, labels=fmt_counts.index, autopct="%1.1f%%", startangle=90)
        ax.set_title("Distribución de formatos de imagen")
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_formats_pie.png"), dpi=160)
        plt.close(fig)

    # --- Cobertura de páginas del PDF con screenshots ---
    if pdf_pages_total > 0:
        expected = [f"{i:02d}" for i in range(1, pdf_pages_total + 1)]
        present = sorted(df["pdf_page"].unique()) if not df.empty else []
        coverage = pd.DataFrame({
            "pdf_page": expected,
            "has_screenshots": [1 if p in present else 0 for p in expected]
        })
        ax = coverage.set_index("pdf_page")["has_screenshots"].plot(kind="bar", figsize=(10,4))
        ax.set_title("Cobertura de páginas del PDF con screenshots (1=sí, 0=no)")
        ax.set_xlabel("Página del PDF")
        ax.set_yticks([0,1])
        fig = ax.get_figure()
        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, "fig_pdf_coverage.png"), dpi=160)
        plt.close(fig)


def main():
    ensure_out()
    pages = count_pdf_pages(PDF_PATH)
    if pages > 0:
        print(f"[INFO] Páginas en PDF: {pages}")
    else:
        print("[WARN] No se pudo determinar el total de páginas del PDF (PyPDF2 no instalado o PDF no encontrado).")

    df = scan_images(SCREENSHOTS_DIR)
    if df.empty:
        print(f"[WARN] No se encontraron imágenes en {SCREENSHOTS_DIR}.")
    else:
        print(f"[INFO] Imágenes detectadas: {len(df)}")
        # Exportar datos crudos y agregados
        df.to_csv(os.path.join(OUTPUT_DIR, "images_by_page.csv"), index=False)
        agg = df.groupby("pdf_page").agg(
            images=("filename", "count"),
            kb_avg=("size_kb", "mean"),
            width_avg=("width", "mean"),
            height_avg=("height", "mean"),
            mpix_avg=("mpix", "mean")
        ).reset_index().sort_values("pdf_page")
        agg.to_csv(os.path.join(OUTPUT_DIR, "images_by_page_summary.csv"), index=False)
        print(f"[OK] CSVs generados en {OUTPUT_DIR}/")

    make_plots(df, pages)
    print(f"[OK] Figuras generadas en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

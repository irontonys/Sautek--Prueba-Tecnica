# Odoo 17 con las dependencias del motor de resurtido (pandas y openpyxl), para que el
# asistente "Importar inventario (Excel)" corra el mismo código que la CLI, y pdftotext
# (poppler-utils) para leer las cotizaciones en PDF de los proveedores.
FROM odoo:17.0
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/resurtido-requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/resurtido-requirements.txt
USER odoo

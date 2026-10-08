# Libro de Excel: cómo se arma

Esta carpeta es para quien cambia el código del libro. El comprador solo usa `Resurtido.xlsm`.

| Ruta | Contenido |
|---|---|
| `vba/*.bas` | Código VBA del libro, como texto, para revisarlo en los commits |
| `build.py` | Arma `Resurtido.xlsm` a partir de `vba/` usando Excel para Mac |
| `tools/Constructor.bas` | Macro que importa los módulos y guarda el libro |
| `tools/constructor.xlsm` | Libro que contiene `Constructor.bas`; lo abre `build.py` |

Los `.bas` van sin acentos: el editor de VBA no importa bien UTF-8. `build.py` lo revisa, junto con que las variables y constantes de cada módulo vayan antes de la primera función (si no, Excel se traba sin mostrar el error).

Las reglas del libro son las mismas que las de `resurtido/` en Python: **una regla se cambia en los dos lados**. Después de armar el libro, corre `python -m pytest`; `tests/test_excel_paridad.py` compara los dos resultados y falla si se desfasan.

## Preparación (una sola vez)

1. En Excel: **Excel → Preferencias → Seguridad** y activa **Confiar en el acceso al modelo de objetos de proyectos de VBA**.
2. Crea `tools/constructor.xlsm`:
   1. En Excel, crea un libro en blanco.
   2. **Herramientas → Macro → Editor de Visual Basic**.
   3. **Archivo → Importar archivo…** y elige `excel/tools/Constructor.bas`.
   4. Cierra el editor y guarda el libro como **Libro de Excel habilitado para macros (.xlsm)** en `excel/tools/constructor.xlsm`.

## Armar el libro

Desde la raíz del repositorio:

```bash
python excel/build.py
```

La primera vez, Excel pide permiso para leer la carpeta `excel/`: dale **Seleccionar** o **Conceder acceso**.

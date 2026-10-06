"""Escenarios de la capacidad `ejecucion-cli`."""

import subprocess
import sys

import pytest
from openpyxl import Workbook

from resurtido import cli


def make_workbook(path, sheets):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name in sheets:
        workbook.create_sheet(name)
    workbook.save(path)
    return path


def test_sin_argumentos_lee_excel_por_omision_y_crea_output(tmp_path, monkeypatch, capsys):
    output = tmp_path / "output"
    monkeypatch.setattr(cli, "DEFAULT_OUTPUT", output)

    assert cli.main([]) == 0

    assert output.is_dir()
    assert str(cli.DEFAULT_INPUT) in capsys.readouterr().out


def test_rutas_personalizadas(tmp_path, capsys):
    source = make_workbook(tmp_path / "otro.xlsx", cli.EXPECTED_SHEETS)
    output = tmp_path / "resultados"

    assert cli.main(["--input", str(source), "--output", str(output)]) == 0

    assert output.is_dir()
    assert str(source) in capsys.readouterr().out


def test_archivo_inexistente(tmp_path, capsys):
    missing = tmp_path / "no_existe.xlsx"

    assert cli.main(["--input", str(missing), "--output", str(tmp_path / "out")]) != 0

    assert str(missing) in capsys.readouterr().err


def test_archivo_que_no_es_excel(tmp_path, capsys):
    fake = tmp_path / "falso.xlsx"
    fake.write_text("esto no es un Excel", encoding="utf-8")

    assert cli.main(["--input", str(fake), "--output", str(tmp_path / "out")]) != 0

    assert "No se pudo leer como Excel" in capsys.readouterr().err


def test_hoja_faltante(tmp_path, capsys):
    sheets = [name for name in cli.EXPECTED_SHEETS if name != "Minimos"]
    source = make_workbook(tmp_path / "sin_minimos.xlsx", sheets)
    output = tmp_path / "out"

    assert cli.main(["--input", str(source), "--output", str(output)]) != 0

    assert "Minimos" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("content", [None, "esto no es un Excel"])
def test_errores_de_entrada_sin_traceback(tmp_path, content):
    source = tmp_path / "entrada.xlsx"
    if content is not None:
        source.write_text(content, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "resurtido", "--input", str(source), "--output", str(tmp_path / "out")],
        cwd=cli.REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("Error:")

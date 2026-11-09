import pandas as pd
import pytest

from core.clasificacion import clasificar_archivos, contiene_base_netvalle, cuentas_en_archivo


def test_clasifica_netvalle_y_sap(archivos_sinteticos):
    cruce, sap = archivos_sinteticos
    assert contiene_base_netvalle(cruce) and not contiene_base_netvalle(sap)
    assert cuentas_en_archivo(sap) >= {"210106001", "610501001"}
    r = clasificar_archivos([cruce, sap])
    assert r == {"NETVALLE": [cruce], "SAP": [sap], "OTROS": []}


def test_hoja_consolidado_cuenta_como_netvalle(tmp_path):
    ruta = tmp_path / "x.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(ruta, sheet_name="CONSOLIDADO", index=False)
    assert contiene_base_netvalle(str(ruta))


def test_rechaza_archivo_no_clasificable(tmp_path, archivos_sinteticos):
    cruce, sap = archivos_sinteticos
    otro = tmp_path / "otro.xlsx"
    pd.DataFrame({"x": [1]}).to_excel(otro, index=False)
    with pytest.raises(Exception, match="No se pudieron clasificar: .*otro.xlsx"):
        clasificar_archivos([cruce, sap, str(otro)])


def test_exige_un_netvalle_y_sap_con_ambas_cuentas(tmp_path, archivos_sinteticos):
    cruce, sap = archivos_sinteticos
    with pytest.raises(Exception) as e:
        clasificar_archivos([sap])
    assert "Se esperaba exactamente 1 archivo NETVALLE; se identificaron 0." in str(e.value)
    solo_iva = tmp_path / "iva.xlsx"
    pd.DataFrame({"Cuenta de mayor": ["210106001"]}).to_excel(solo_iva, index=False)
    with pytest.raises(Exception, match="El SAP no contiene la cuenta de IT 610501001."):
        clasificar_archivos([cruce, str(solo_iva)])


def test_archivo_corrupto_da_mensaje_claro(tmp_path):
    malo = tmp_path / "malo.xlsx"
    malo.write_bytes(b"no es un excel")
    with pytest.raises(Exception, match="No se pudo abrir"):
        clasificar_archivos([str(malo)])

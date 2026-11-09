"""Cálculo de impuestos con Decimal y ROUND_HALF_UP. Origen: legacy.redondear_impuesto."""

from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd


def redondear_impuesto(valor, tasa):

    if pd.isna(valor):

        return np.nan

    try:

        resultado = (Decimal(str(valor)) * Decimal(str(tasa))).quantize(

            Decimal("0.01"), rounding=ROUND_HALF_UP

        )

        return float(resultado)

    except Exception:

        return np.nan

import { Card, CardContent } from "@/components/ui/card";
import type { Tarjeta } from "@/lib/api";
import { CLASES_TONO, formatoBs, tonoDeResultado } from "@/lib/estado";
import { cn } from "@/lib/utils";

export function TarjetaIndicador({ t }: { t: Tarjeta }) {
  const tono = tonoDeResultado(t.resultado);
  const clases = CLASES_TONO[tono];
  return (
    <Card data-testid="tarjeta" data-tono={tono} className={cn("border-l-4", clases.borde)}>
      <CardContent className="space-y-3 pt-1">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t.control}</h3>
        <span className={cn("inline-block rounded-md px-2.5 py-1 text-sm font-bold", clases.insignia)}>{t.resultado}</span>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <dt className="text-muted-foreground">Cantidad</dt>
            <dd className="text-lg font-semibold tabular-nums">{t.cantidad ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Total Bs</dt>
            <dd className="text-lg font-semibold tabular-nums">{formatoBs(t.total_facturas_bs)}</dd>
          </div>
        </dl>
        {t.dato_clave && <p className="text-sm font-medium">{t.dato_clave}</p>}
        {t.que_significa && <p className="text-sm text-muted-foreground">{t.que_significa}</p>}
        {t.que_hacer && <p className="text-sm"><span className="font-semibold">Qué hacer: </span>{t.que_hacer}</p>}
      </CardContent>
    </Card>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { TarjetaIndicador } from "@/components/tarjeta-indicador";
import { buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ErrorApi, obtenerEstado, urlExcel, type EstadoControl } from "@/lib/api";
import { tonoDeResultado } from "@/lib/estado";
import { cn } from "@/lib/utils";

export default function Resultado() {
  const { id } = useParams<{ id: string }>();
  const [e, setE] = useState<EstadoControl | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;
    let t: ReturnType<typeof setTimeout>;
    const consultar = async () => {
      try {
        const est = await obtenerEstado(id);
        if (!vigente) return;
        setE(est);
        if (est.estado === "en cola" || est.estado === "procesando") t = setTimeout(consultar, 1000);
      } catch (x) {
        if (!vigente) return;
        setError(x instanceof ErrorApi && x.status === 404
          ? "Este control no existe o ya expiró (los resultados se conservan 24 horas)."
          : x instanceof Error ? x.message : "Error");
      }
    };
    void consultar();
    return () => { vigente = false; clearTimeout(t); };
  }, [id]);

  if (error) return <p role="alert" className="rounded-md bg-[#FCE4D6] p-4 text-[#9C0006]">{error}</p>;
  if (!e) return <p role="status" className="text-muted-foreground">Cargando…</p>;

  if (e.estado === "en cola" || e.estado === "procesando") {
    return (
      <section className="mx-auto max-w-xl space-y-4 pt-10 text-center">
        <h1 className="text-xl font-bold text-[#1F4E78]">Generando el control…</h1>
        <Progress value={e.progreso} aria-label="Progreso del control" />
        <p className="text-sm text-muted-foreground" role="status">Estado: {e.estado} ({e.progreso}%)</p>
      </section>
    );
  }

  if (e.estado === "error") {
    return (
      <section className="mx-auto max-w-2xl space-y-4">
        <h1 className="text-xl font-bold text-[#9C0006]">No se pudo generar el control</h1>
        <p role="alert" className="whitespace-pre-line rounded-md bg-[#FCE4D6] p-4 text-sm text-[#9C0006]">{e.error}</p>
        <Link href="/" className={buttonVariants()}>Volver a intentar</Link>
      </section>
    );
  }

  const r = e.resumen!;
  const general = r.tarjetas.find((x) => x.control === "RESULTADO GENERAL");
  const todoOk = !!general && tonoDeResultado(general.resultado) === "verde";
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-[#1F4E78]">Resultado del control</h1>
        <div className="flex gap-3">
          <Link href={`/controles/${id}/observaciones`} className={cn(buttonVariants({ variant: "outline" }))}>
            Ver observaciones ({r.observaciones_total})
          </Link>
          <a href={urlExcel(id)} className={buttonVariants()} download>Descargar Excel</a>
        </div>
      </div>
      {general && (
        <div
          role="status"
          data-testid="banner-general"
          className={cn(
            "rounded-xl border-l-8 p-5 text-lg font-bold",
            todoOk ? "border-l-[#548235] bg-[#E2F0D9] text-[#20613C]" : "border-l-[#C00000] bg-[#FCE4D6] text-[#9C0006]",
          )}
        >
          {todoOk
            ? "✔ TODO OK: no hay observaciones pendientes. El control cuadra."
            : `⚠ Hay ${r.observaciones_total} observación(es) para revisar antes de dar por bueno el control.`}
          <p className="mt-1 text-sm font-normal">{general.que_significa}</p>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {r.tarjetas.map((t) => <TarjetaIndicador key={t.control} t={t} />)}
      </div>
      <p className="text-xs text-muted-foreground">Disponible hasta {new Date(e.expira * 1000).toLocaleString("es-BO")}.</p>
    </section>
  );
}

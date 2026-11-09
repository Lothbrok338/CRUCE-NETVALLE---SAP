"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorApi, obtenerEstado } from "@/lib/api";
import { borrarHistorial, leerHistorial, type EntradaHistorial } from "@/lib/historial";

type Fila = EntradaHistorial & { estado: string };

export default function Historial() {
  const [filas, setFilas] = useState<Fila[] | null>(null);

  useEffect(() => {
    const h = leerHistorial();
    Promise.all(h.map(async (e): Promise<Fila> => {
      try { return { ...e, estado: (await obtenerEstado(e.id)).estado }; }
      catch (x) { return { ...e, estado: x instanceof ErrorApi && x.status === 404 ? "expirado" : "sin conexión" }; }
    })).then(setFilas);
  }, []);

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#1F4E78]">Historial</h1>
          <p className="text-sm text-muted-foreground">Controles de este navegador. Los resultados expiran a las 24 horas.</p>
        </div>
        {!!filas?.length && <Button variant="outline" onClick={() => { borrarHistorial(); setFilas([]); }}>Limpiar historial</Button>}
      </div>
      {filas === null ? <p role="status" className="text-muted-foreground">Cargando…</p>
        : !filas.length ? <p className="text-muted-foreground">Todavía no hay controles en esta sesión.</p>
        : (
          <ul className="divide-y rounded-lg border bg-white">
            {filas.map((f) => (
              <li key={f.id} className="flex flex-wrap items-center gap-4 p-4 text-sm">
                <span className="w-44 tabular-nums">{new Date(f.creado).toLocaleString("es-BO")}</span>
                <span className="min-w-0 flex-1 truncate">{f.netvalle} + {f.sap.join(", ")}</span>
                <span className="rounded bg-muted px-2 py-0.5 font-medium">{f.estado}</span>
                {f.estado === "listo" || f.estado === "procesando" || f.estado === "en cola" || f.estado === "error"
                  ? <Link className="font-semibold text-primary hover:underline" href={`/controles/${f.id}`}>Abrir</Link>
                  : <span className="text-muted-foreground">—</span>}
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}

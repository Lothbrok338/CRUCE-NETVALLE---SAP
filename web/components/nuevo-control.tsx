"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { clasificar, crearControl, type Clasificacion } from "@/lib/api";
import { guardarEnHistorial } from "@/lib/historial";
import { cn } from "@/lib/utils";

type Seleccion = "NETVALLE" | "SAP" | "IGNORAR";
const ETIQUETA: Record<Seleccion, string> = { NETVALLE: "CRUCE (NETVALLE)", SAP: "SAP (IVA/IT)", IGNORAR: "Ignorar" };

export function NuevoControl() {
  const router = useRouter();
  const entrada = useRef<HTMLInputElement>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [clasif, setClasif] = useState<Clasificacion | null>(null);
  const [seleccion, setSeleccion] = useState<Seleccion[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function recibir(lista: FileList | File[]) {
    const nuevos = [...lista];
    if (!nuevos.length) return;
    const todos = [...archivos, ...nuevos];
    setArchivos(todos);
    setError(null);
    setCargando(true);
    try {
      const c = await clasificar(todos);
      setClasif(c);
      setSeleccion(c.archivos.map((a) => (a.tipo === "OTROS" ? "IGNORAR" : a.tipo)));
    } catch (e) {
      setClasif(null);
      setError(e instanceof Error ? e.message : "No se pudo clasificar los archivos.");
    } finally {
      setCargando(false);
    }
  }

  function quitar(i: number) {
    const resto = archivos.filter((_, k) => k !== i);
    setArchivos(resto);
    setClasif(null);
    setSeleccion([]);
    if (resto.length) {
      setCargando(true);
      clasificar(resto)
        .then((c) => { setClasif(c); setSeleccion(c.archivos.map((a) => (a.tipo === "OTROS" ? "IGNORAR" : a.tipo))); })
        .catch((e) => setError(e instanceof Error ? e.message : "Error"))
        .finally(() => setCargando(false));
    }
  }

  const netvalles = clasif ? clasif.archivos.filter((_, i) => seleccion[i] === "NETVALLE") : [];
  const saps = clasif ? clasif.archivos.filter((_, i) => seleccion[i] === "SAP") : [];
  const problemaSeleccion =
    !clasif ? null
    : netvalles.length !== 1 ? "Debe haber exactamente 1 archivo CRUCE (NETVALLE)."
    : saps.length < 1 ? "Debe haber al menos 1 archivo SAP."
    : null;

  async function procesar() {
    if (!clasif || problemaSeleccion) return;
    setCargando(true);
    setError(null);
    try {
      const { id } = await crearControl(archivos, netvalles[0].nombre, saps.map((s) => s.nombre));
      guardarEnHistorial({ id, creado: Date.now(), netvalle: netvalles[0].nombre, sap: saps.map((s) => s.nombre) });
      router.push(`/controles/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear el control.");
      setCargando(false);
    }
  }

  return (
    <div className="space-y-6">
      <div
        role="button"
        tabIndex={0}
        data-testid="zona-carga"
        onClick={() => entrada.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); void recibir(e.dataTransfer.files); }}
        className={cn(
          "cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors",
          arrastrando ? "border-primary bg-primary/5" : "border-border hover:border-primary/60",
        )}
      >
        <p className="text-base font-semibold text-primary">Arrastra aquí los archivos Excel</p>
        <p className="mt-1 text-sm text-muted-foreground">
          El CRUCE depurado (motor 1) y uno o más mayores SAP con IVA e IT. También puedes hacer clic para elegirlos.
        </p>
        <input
          ref={entrada}
          data-testid="entrada-archivos"
          type="file"
          multiple
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={(e) => { if (e.target.files) void recibir(e.target.files); e.target.value = ""; }}
        />
      </div>

      {cargando && <p className="text-sm text-muted-foreground" role="status">Procesando…</p>}
      {error && <p role="alert" className="whitespace-pre-line rounded-md bg-[#FCE4D6] p-3 text-sm text-[#9C0006]">{error}</p>}

      {clasif && (
        <Card>
          <CardContent className="space-y-4">
            <h2 className="text-base font-semibold">Clasificación automática</h2>
            <p className="text-sm text-muted-foreground">Revisa y corrige si algún archivo quedó mal clasificado.</p>
            <ul className="divide-y">
              {clasif.archivos.map((a, i) => (
                <li key={`${a.nombre}-${i}`} className="flex flex-wrap items-center gap-3 py-2">
                  <span className="min-w-0 flex-1 truncate text-sm font-medium" title={a.nombre}>{a.nombre}</span>
                  {a.cuentas.map((c) => (
                    <span key={c} className="rounded bg-[#DDEBF7] px-2 py-0.5 text-xs font-semibold text-[#1F4E78]">{c}</span>
                  ))}
                  {a.detalle && <span className="text-xs text-muted-foreground">{a.detalle}</span>}
                  <select
                    aria-label={`Tipo de ${a.nombre}`}
                    value={seleccion[i]}
                    onChange={(e) => setSeleccion(seleccion.map((s, k) => (k === i ? (e.target.value as Seleccion) : s)))}
                    className="h-9 rounded-md border bg-background px-2 text-sm"
                  >
                    {(Object.keys(ETIQUETA) as Seleccion[]).map((k) => <option key={k} value={k}>{ETIQUETA[k]}</option>)}
                  </select>
                  <Button variant="ghost" size="sm" onClick={() => quitar(i)} aria-label={`Quitar ${a.nombre}`}>Quitar</Button>
                </li>
              ))}
            </ul>
            {problemaSeleccion && <p role="alert" className="text-sm text-[#9C0006]">{problemaSeleccion}</p>}
            {!problemaSeleccion && !clasif.valido && (
              <p className="text-sm text-[#7F6000]">La clasificación automática tenía observaciones; se usará tu selección.</p>
            )}
            <Button onClick={procesar} disabled={!!problemaSeleccion || cargando}>Generar control</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

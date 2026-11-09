"use client";

import { flexRender, getCoreRowModel, useReactTable, type ColumnDef, type SortingState } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { obtenerObservaciones, type PaginaObservaciones } from "@/lib/api";
import { formatoBs } from "@/lib/estado";

type Fila = Record<string, string | number | null>;
const MONEDA = /Bs$/;
const ANCHAS = new Set(["QUÉ PASÓ", "QUÉ REVISAR"]);

export function TablaObservaciones({ id }: { id: string }) {
  const [datos, setDatos] = useState<PaginaObservaciones | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pagina, setPagina] = useState(1);
  const [porPagina, setPorPagina] = useState(25);
  const [busqueda, setBusqueda] = useState("");
  const [q, setQ] = useState("");
  const [control, setControl] = useState("");
  const [punto, setPunto] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);

  useEffect(() => {
    const t = setTimeout(() => { setQ(busqueda); setPagina(1); }, 300);
    return () => clearTimeout(t);
  }, [busqueda]);

  useEffect(() => {
    let vigente = true;
    obtenerObservaciones(id, {
      pagina, por_pagina: porPagina, q, control, punto,
      orden: sorting[0]?.id, direccion: sorting[0]?.desc ? "desc" : "asc",
    })
      .then((d) => { if (vigente) { setDatos(d); setError(null); } })
      .catch((e) => vigente && setError(e instanceof Error ? e.message : "Error"));
    return () => { vigente = false; };
  }, [id, pagina, porPagina, q, control, punto, sorting]);

  const columnas = useMemo<ColumnDef<Fila>[]>(
    () => (datos?.columnas ?? []).map((c) => ({
      accessorKey: c,
      header: c,
      cell: ({ getValue }) => {
        const v = getValue<string | number | null>();
        if (typeof v === "number") return <span className="tabular-nums">{MONEDA.test(c) ? formatoBs(v) : v}</span>;
        return v ?? "—";
      },
    })),
    [datos?.columnas],
  );

  const tabla = useReactTable({
    data: (datos?.filas ?? []) as Fila[],
    columns: columnas,
    state: { sorting },
    onSortingChange: (u) => { setSorting(u); setPagina(1); },
    manualPagination: true,
    manualSorting: true,
    enableSortingRemoval: true,
    getCoreRowModel: getCoreRowModel(),
  });

  const select = "h-9 rounded-md border bg-background px-2 text-sm";
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input aria-label="Buscar" placeholder="Buscar factura, punto, asiento…" value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)} className="max-w-xs" />
        <select aria-label="Filtrar por CONTROL" className={select} value={control}
          onChange={(e) => { setControl(e.target.value); setPagina(1); }}>
          <option value="">Todos los CONTROL</option>
          {datos?.filtros.CONTROL.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select aria-label="Filtrar por PUNTO" className={select} value={punto}
          onChange={(e) => { setPunto(e.target.value); setPagina(1); }}>
          <option value="">Todos los PUNTO</option>
          {datos?.filtros.PUNTO.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select aria-label="Filas por página" className={select} value={porPagina}
          onChange={(e) => { setPorPagina(Number(e.target.value)); setPagina(1); }}>
          {[25, 50, 100].map((n) => <option key={n} value={n}>{n} por página</option>)}
        </select>
      </div>

      {error && <p role="alert" className="rounded-md bg-[#FCE4D6] p-3 text-sm text-[#9C0006]">{error}</p>}

      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            {tabla.getHeaderGroups().map((g) => (
              <TableRow key={g.id}>
                {g.headers.map((h) => {
                  const orden = h.column.getIsSorted();
                  return (
                    <TableHead key={h.id} onClick={h.column.getToggleSortingHandler()}
                      aria-sort={orden === "asc" ? "ascending" : orden === "desc" ? "descending" : "none"}
                      className="cursor-pointer select-none whitespace-nowrap bg-[#1F4E78] text-white hover:bg-[#1F4E78]/90">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {orden === "asc" ? " ▲" : orden === "desc" ? " ▼" : ""}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {tabla.getRowModel().rows.length ? tabla.getRowModel().rows.map((r) => (
              <TableRow key={r.id}>
                {r.getVisibleCells().map((c) => (
                  <TableCell key={c.id} className={ANCHAS.has(c.column.id) ? "min-w-80 max-w-md align-top whitespace-normal" : "align-top whitespace-nowrap"}>
                    {flexRender(c.column.columnDef.cell, c.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            )) : (
              <TableRow><TableCell colSpan={Math.max(columnas.length, 1)} className="py-8 text-center text-muted-foreground">
                {datos ? "No hay observaciones con esos filtros." : "Cargando…"}
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span data-testid="total">{datos ? `${datos.total} observación(es)` : ""}</span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>Anterior</Button>
          <span>Página {datos?.pagina ?? 1} de {datos?.paginas ?? 1}</span>
          <Button variant="outline" size="sm" disabled={!datos || pagina >= datos.paginas} onClick={() => setPagina(pagina + 1)}>Siguiente</Button>
        </div>
      </div>
    </div>
  );
}

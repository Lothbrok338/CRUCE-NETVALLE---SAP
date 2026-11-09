export type TipoArchivo = "NETVALLE" | "SAP" | "OTROS";

export interface ArchivoClasificado { nombre: string; tipo: TipoArchivo; cuentas: string[]; detalle: string | null }
export interface Clasificacion { valido: boolean; archivos: ArchivoClasificado[]; problemas: string[] }
export interface Tarjeta {
  control: string; resultado: string; cantidad: number | null; total_facturas_bs: number | null;
  dato_clave: string | null; que_significa: string | null; que_hacer: string | null;
}
export interface EstadoControl {
  id: string; estado: "en cola" | "procesando" | "listo" | "error"; progreso: number; creado: number; expira: number;
  resumen: { tarjetas: Tarjeta[]; observaciones_total: number } | null; error: string | null;
}
export interface PaginaObservaciones {
  total: number; pagina: number; por_pagina: number; paginas: number; columnas: string[];
  filas: Record<string, string | number | null>[]; filtros: { CONTROL: string[]; PUNTO: string[] };
}

export class ErrorApi extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function leer<T>(r: Response): Promise<T> {
  if (r.ok) return r.json() as Promise<T>;
  let detalle = `Error ${r.status}`;
  try {
    const j = await r.json();
    if (typeof j.detail === "string") detalle = j.detail;
    else if (Array.isArray(j.detail)) detalle = j.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch { /* cuerpo no JSON */ }
  throw new ErrorApi(detalle, r.status);
}

const formulario = (archivos: File[]) => {
  const f = new FormData();
  archivos.forEach((a) => f.append("archivos", a));
  return f;
};

export const clasificar = (archivos: File[]) =>
  fetch("/api/clasificar", { method: "POST", body: formulario(archivos) }).then((r) => leer<Clasificacion>(r));

export const crearControl = (archivos: File[], netvalle: string, sap: string[]) => {
  const f = formulario(archivos);
  f.append("netvalle", netvalle);
  sap.forEach((s) => f.append("sap", s));
  return fetch("/api/controles", { method: "POST", body: f }).then((r) => leer<{ id: string }>(r));
};

export const obtenerEstado = (id: string) =>
  fetch(`/api/controles/${id}`, { cache: "no-store" }).then((r) => leer<EstadoControl>(r));

export interface ParamsObs { pagina: number; por_pagina: number; q?: string; control?: string; punto?: string; orden?: string; direccion?: "asc" | "desc" }

export const obtenerObservaciones = (id: string, p: ParamsObs) => {
  const qs = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
  return fetch(`/api/controles/${id}/observaciones?${qs}`, { cache: "no-store" }).then((r) => leer<PaginaObservaciones>(r));
};

export const urlExcel = (id: string) => `/api/controles/${id}/excel`;

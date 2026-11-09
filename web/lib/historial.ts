export interface EntradaHistorial { id: string; creado: number; netvalle: string; sap: string[] }
const CLAVE = "ct_historial";

export function leerHistorial(): EntradaHistorial[] {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE) ?? "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

export function guardarEnHistorial(e: EntradaHistorial) {
  try {
    const resto = leerHistorial().filter((x) => x.id !== e.id);
    localStorage.setItem(CLAVE, JSON.stringify([e, ...resto].slice(0, 50)));
  } catch { /* almacenamiento no disponible */ }
}

export function borrarHistorial() {
  try { localStorage.removeItem(CLAVE); } catch { /* nada */ }
}

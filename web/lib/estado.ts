export type Tono = "verde" | "rojo" | "amarillo" | "azul";

/** Color de cada tarjeta según el texto de RESULTADO (mismas reglas que el Excel). */
export function tonoDeResultado(resultado: string): Tono {
  const r = resultado.toUpperCase();
  if (r.includes("REVISAR") || r.includes("OBSERV")) return "rojo";
  if (r.includes("TODO CUADRA") || r === "OK" || r.includes("SIN PENDIENTES")) return "verde";
  if (r.includes("SIN EFECTO NETO")) return "amarillo";
  return "azul";
}

export const CLASES_TONO: Record<Tono, { borde: string; insignia: string }> = {
  verde: { borde: "border-l-[#548235]", insignia: "bg-[#E2F0D9] text-[#20613C]" },
  rojo: { borde: "border-l-[#C00000]", insignia: "bg-[#FCE4D6] text-[#9C0006]" },
  amarillo: { borde: "border-l-[#BF9000]", insignia: "bg-[#FFF2CC] text-[#7F6000]" },
  azul: { borde: "border-l-[#1F4E78]", insignia: "bg-[#DDEBF7] text-[#1F4E78]" },
};

export const formatoBs = (n: number | null | undefined) =>
  n === null || n === undefined || Number.isNaN(n)
    ? "—"
    : n.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

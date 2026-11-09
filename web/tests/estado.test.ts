import { describe, expect, it, vi, afterEach } from "vitest";
import { formatoBs, tonoDeResultado } from "@/lib/estado";
import { autorizado } from "@/lib/acceso";
import { borrarHistorial, guardarEnHistorial, leerHistorial } from "@/lib/historial";

describe("tonoDeResultado (mismas reglas que el Excel)", () => {
  it.each([
    ["TODO CUADRA", "verde"],
    ["SIN PENDIENTES", "verde"],
    ["REVISAR", "rojo"],
    ["REVISAR 11 CASO(S)", "rojo"],
    ["CON OBSERVACIONES", "rojo"],
    ["REVISAR IMPORTES", "rojo"],
    ["SIN EFECTO NETO", "amarillo"],
    ["INFORMATIVO", "azul"],
  ])("%s -> %s", (texto, tono) => expect(tonoDeResultado(texto)).toBe(tono));
});

describe("formatoBs", () => {
  it("formatea dos decimales y guion para vacíos", () => {
    expect(formatoBs(1234.5)).toMatch(/1.?234[,.]50/);
    expect(formatoBs(null)).toBe("—");
    expect(formatoBs(NaN)).toBe("—");
  });
});

describe("acceso con contraseña", () => {
  afterEach(() => vi.unstubAllEnvs());
  it("sin WEB_ACCESS_PASSWORD deja pasar", () => expect(autorizado(null)).toBe(true));
  it("con contraseña exige Basic correcto", () => {
    vi.stubEnv("WEB_ACCESS_PASSWORD", "secreta");
    expect(autorizado(null)).toBe(false);
    expect(autorizado("Basic " + btoa("x:mala"))).toBe(false);
    expect(autorizado("Basic " + btoa("x:secreta"))).toBe(true);
    expect(autorizado("Bearer abc")).toBe(false);
    expect(autorizado("Basic ###")).toBe(false);
  });
});

describe("historial local", () => {
  it("guarda sin duplicar, más reciente primero, y borra", () => {
    borrarHistorial();
    guardarEnHistorial({ id: "a", creado: 1, netvalle: "c.xlsx", sap: ["s.xlsx"] });
    guardarEnHistorial({ id: "b", creado: 2, netvalle: "c.xlsx", sap: ["s.xlsx"] });
    guardarEnHistorial({ id: "a", creado: 3, netvalle: "c.xlsx", sap: ["s.xlsx"] });
    expect(leerHistorial().map((e) => e.id)).toEqual(["a", "b"]);
    borrarHistorial();
    expect(leerHistorial()).toEqual([]);
  });
});

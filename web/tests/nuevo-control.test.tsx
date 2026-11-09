import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { NuevoControl } from "@/components/nuevo-control";

const xlsx = (n: string) => new File(["x"], n, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
const json = (b: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(b), { status }));

const CLASIF = {
  valido: true, problemas: [],
  archivos: [
    { nombre: "CRUCE.xlsx", tipo: "NETVALLE", cuentas: [], detalle: null },
    { nombre: "SAP.xlsx", tipo: "SAP", cuentas: ["IVA", "IT"], detalle: null },
    { nombre: "otro.xlsx", tipo: "OTROS", cuentas: [], detalle: "No es NETVALLE ni contiene las cuentas de IVA/IT." },
  ],
};

beforeEach(() => { push.mockReset(); localStorage.clear(); });

async function subir(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal("fetch", fetchMock);
  render(<NuevoControl />);
  await userEvent.upload(screen.getByTestId("entrada-archivos"), [xlsx("CRUCE.xlsx"), xlsx("SAP.xlsx"), xlsx("otro.xlsx")]);
  await screen.findByText("Clasificación automática");
}

describe("Nuevo control", () => {
  it("clasifica, muestra IVA/IT y permite generar el control con la selección", async () => {
    const f = vi.fn()
      .mockImplementationOnce(() => json(CLASIF))
      .mockImplementationOnce(() => json({ id: "abc123" }, 202));
    await subir(f);
    expect(screen.getByText("IVA")).toBeInTheDocument();
    expect(screen.getByLabelText("Tipo de otro.xlsx")).toHaveValue("IGNORAR");
    await userEvent.click(screen.getByRole("button", { name: "Generar control" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/controles/abc123"));
    const cuerpo = f.mock.calls[1][1].body as FormData;
    expect(cuerpo.get("netvalle")).toBe("CRUCE.xlsx");
    expect(cuerpo.getAll("sap")).toEqual(["SAP.xlsx"]);
    expect(JSON.parse(localStorage.getItem("ct_historial")!)[0].id).toBe("abc123");
  });

  it("permite corregir la clasificación y bloquea combinaciones inválidas", async () => {
    await subir(vi.fn().mockImplementation(() => json(CLASIF)));
    const boton = screen.getByRole("button", { name: "Generar control" });
    expect(boton).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Tipo de SAP.xlsx"), { target: { value: "IGNORAR" } });
    expect(screen.getByText("Debe haber al menos 1 archivo SAP.")).toBeInTheDocument();
    expect(boton).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Tipo de SAP.xlsx"), { target: { value: "NETVALLE" } });
    expect(screen.getByText("Debe haber exactamente 1 archivo CRUCE (NETVALLE).")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Tipo de SAP.xlsx"), { target: { value: "SAP" } });
    expect(boton).toBeEnabled();
  });

  it("muestra el error de la API sin avanzar", async () => {
    const f = vi.fn()
      .mockImplementationOnce(() => json(CLASIF))
      .mockImplementationOnce(() => json({ detail: "El SAP no contiene la cuenta de IT 610501001." }, 422));
    await subir(f);
    await userEvent.click(screen.getByRole("button", { name: "Generar control" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El SAP no contiene la cuenta de IT 610501001.");
    expect(push).not.toHaveBeenCalled();
  });

  it("muestra el error si la clasificación falla", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => json({ detail: "'datos.csv' no es un archivo Excel (.xlsx)." }, 422)));
    render(<NuevoControl />);
    await userEvent.setup({ applyAccept: false }).upload(screen.getByTestId("entrada-archivos"), [xlsx("datos.csv")]);
    expect(await screen.findByRole("alert")).toHaveTextContent("no es un archivo Excel");
  });
});

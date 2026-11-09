import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TarjetaIndicador } from "@/components/tarjeta-indicador";

const base = { cantidad: 3, total_facturas_bs: 1500, dato_clave: "dato", que_significa: "significa", que_hacer: "hacerlo" };

describe("TarjetaIndicador", () => {
  it.each([
    ["TODO CUADRA", "verde"], ["REVISAR 2 CASO(S)", "rojo"], ["SIN EFECTO NETO", "amarillo"], ["INFORMATIVO", "azul"],
  ])("%s usa el color %s", (resultado, tono) => {
    render(<TarjetaIndicador t={{ ...base, control: "X", resultado }} />);
    expect(screen.getByTestId("tarjeta")).toHaveAttribute("data-tono", tono);
    expect(screen.getByText(resultado)).toBeInTheDocument();
  });

  it("muestra cantidad, total y textos; guion si no hay total", () => {
    render(<TarjetaIndicador t={{ ...base, control: "LIBROS EXENTOS", resultado: "INFORMATIVO", total_facturas_bs: null }} />);
    expect(screen.getByText("LIBROS EXENTOS")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("hacerlo")).toBeInTheDocument();
  });
});

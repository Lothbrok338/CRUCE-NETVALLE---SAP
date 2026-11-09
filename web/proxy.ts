import type { NextRequest } from "next/server";
import { autorizado, respuestaNoAutorizado } from "@/lib/acceso";

// Protege las páginas. /api/* se protege dentro del route handler (para no almacenar en memoria los archivos subidos).
export function proxy(request: NextRequest) {
  if (!autorizado(request.headers.get("authorization"))) return respuestaNoAutorizado();
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon.ico).*)"],
};

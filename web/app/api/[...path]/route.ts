import { autorizado, respuestaNoAutorizado } from "@/lib/acceso";

export const dynamic = "force-dynamic";

const COPIAR = ["content-type", "content-disposition", "content-length", "cache-control"];

/**
 * Proxy hacia la API (FastAPI). El token de la API vive solo en el servidor (API_TOKEN):
 * el navegador nunca lo ve. Los archivos se transmiten en streaming.
 */
async function manejar(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  if (!autorizado(req.headers.get("authorization"))) return respuestaNoAutorizado();

  const { path } = await ctx.params;
  const base = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const destino = `${base}/api/${path.map(encodeURIComponent).join("/")}${new URL(req.url).search}`;

  const headers = new Headers();
  const tipo = req.headers.get("content-type");
  if (tipo) headers.set("content-type", tipo);
  if (process.env.API_TOKEN) headers.set("authorization", `Bearer ${process.env.API_TOKEN}`);

  const conCuerpo = !["GET", "HEAD"].includes(req.method);
  let respuesta: Response;
  try {
    respuesta = await fetch(destino, {
      method: req.method,
      headers,
      body: conCuerpo ? req.body : undefined,
      // @ts-expect-error `duplex` es requerido por Node para enviar streams
      duplex: "half",
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return Response.json({ detail: "No se pudo contactar el servicio de cálculo. Intenta de nuevo en un momento." }, { status: 502 });
  }

  const salida = new Headers();
  for (const nombre of COPIAR) {
    const valor = respuesta.headers.get(nombre);
    if (valor) salida.set(nombre, valor);
  }
  return new Response(respuesta.body, { status: respuesta.status, headers: salida });
}

export { manejar as GET, manejar as POST };

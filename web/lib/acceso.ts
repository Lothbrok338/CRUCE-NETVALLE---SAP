/** Acceso opcional a la web con contraseña (HTTP Basic). Se activa definiendo WEB_ACCESS_PASSWORD. */
export function autorizado(authorization: string | null): boolean {
  const clave = process.env.WEB_ACCESS_PASSWORD;
  if (!clave) return true;
  if (!authorization?.startsWith("Basic ")) return false;
  try {
    const decodificado = atob(authorization.slice(6));
    const recibida = decodificado.slice(decodificado.indexOf(":") + 1);
    return recibida === clave;
  } catch {
    return false;
  }
}

export const respuestaNoAutorizado = () =>
  new Response("Acceso restringido", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Control Tributario Integral"' },
  });

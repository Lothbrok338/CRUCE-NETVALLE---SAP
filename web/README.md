# web/

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Table.

```bash
npm install
API_URL=http://localhost:8000 npm run dev    # http://localhost:3000
npm test                                      # vitest
node e2e/smoke.cjs                            # recorrido con navegador (ver cabecera del archivo)
```
El navegador solo habla con la web: `app/api/[...path]/route.ts` reenvía a la API agregando `API_TOKEN` en el servidor.

import { NuevoControl } from "@/components/nuevo-control";

export default function Page() {
  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#1F4E78]">Nuevo control</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Cruza NETVALLE contra los mayores SAP de IVA e IT. Los resultados se conservan 24 horas.
        </p>
      </div>
      <NuevoControl />
    </section>
  );
}

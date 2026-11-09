"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { TablaObservaciones } from "@/components/tabla-observaciones";
import { buttonVariants } from "@/components/ui/button";
import { urlExcel } from "@/lib/api";

export default function Observaciones() {
  const { id } = useParams<{ id: string }>();
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-[#1F4E78]">Observaciones</h1>
        <div className="flex gap-3">
          <Link href={`/controles/${id}`} className={buttonVariants({ variant: "outline" })}>Volver al resultado</Link>
          <a href={urlExcel(id)} className={buttonVariants()} download>Descargar Excel</a>
        </div>
      </div>
      <TablaObservaciones id={id} />
    </section>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { AvisoFacturasAtrasadas } from "@/components/facturas-faltantes/AvisoFacturasAtrasadas";
import { formatFechaHora } from "@/lib/format";
import {
  ejecutarRutina, getEstadoRutina, type AlcanceRutina, type CorridaRutina,
} from "@/services/documentosNuevosApi";

const ESTADO: Record<string, string> = {
  en_curso: "En curso",
  ok: "Terminó bien",
  con_problemas: "Terminó con cosas a revisar",
  incompleta: "Se cortó antes de terminar",
};

const TEXTOS: Record<AlcanceRutina, { titulo: string; descripcion: string; boton: string }> = {
  documentos: {
    titulo: "Mails y carpetas",
    descripcion: "Lee los mails nuevos y revisa las carpetas de Compras e Impuestos.",
    boton: "Buscar en mails y carpetas",
  },
  portales: {
    titulo: "Portales",
    descripcion: "Entra a las cuentas con sincronización automática y baja lo nuevo, de a una.",
    boton: "Buscar en portales",
  },
};

/** La fecha-hora (local, sin zona) dos días después, para mostrar cuándo corre sola. */
function enDosDias(inicio: string): string {
  const m = inicio.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  if (!m) return "—";
  const f = new Date(+m[1], +m[2] - 1, +m[3] + 2, +m[4], +m[5]);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(f.getDate())}/${p(f.getMonth() + 1)}/${f.getFullYear()} ${p(f.getHours())}:${p(f.getMinutes())}`;
}

function Resumen({ alcance, u }: { alcance: AlcanceRutina; u: CorridaRutina | null }) {
  if (!u) return <p className="mt-1 text-ink-muted">Todavía no corrió.</p>;
  const detalle = alcance === "documentos"
    ? `${u.mailsLeidos} mails`
    : `${u.cuentasCorridas} cuentas${u.cuentasConProblemas ? ` (${u.cuentasConProblemas} con problemas)` : ""}`;
  return (
    <p className="mt-1 text-ink-secondary">
      Última: {formatFechaHora(u.inicio)} · {ESTADO[u.estado] ?? u.estado} · {detalle}
      {u.alcance === alcance && (
        <> · {u.documentosNuevos} documentos nuevos ({u.cargadosSolos} cargados solos, {u.paraCargarAMano} para cargar a mano)</>
      )}
      {u.mensaje && <span className="block text-amber-900">{u.mensaje}</span>}
    </p>
  );
}

function Rutina({ alcance, u, enCola, otraCorriendo }: {
  alcance: AlcanceRutina; u: CorridaRutina | null; enCola: boolean; otraCorriendo: boolean;
}) {
  const qc = useQueryClient();
  const [pedida, setPedida] = useState(false);
  const ejecutar = useMutation({
    mutationFn: () => ejecutarRutina(alcance),
    onSuccess: () => { setPedida(true); qc.invalidateQueries({ queryKey: ["documentos-nuevos"] }); },
  });
  const t = TEXTOS[alcance];
  const enCurso = u?.estado === "en_curso";

  return (
    <div className="flex-1 rounded-md border border-border px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-medium">{t.titulo}</h3>
        <SoloLectura>
          <button type="button" disabled={enCurso || enCola || ejecutar.isPending} onClick={() => ejecutar.mutate()}
            className="rounded-md border border-border px-3 py-1 text-xs font-medium disabled:opacity-50">
            {enCurso ? "Buscando..." : enCola ? "En espera..." : t.boton}
          </button>
        </SoloLectura>
      </div>
      <p className="text-ink-secondary">{t.descripcion}</p>
      {pedida && enCola && otraCorriendo && (
        <p className="text-ink-secondary">Arranca cuando termine la otra búsqueda.</p>
      )}
      {pedida && enCola && !otraCorriendo && <p className="text-ink-secondary">Pedido recibido: arranca enseguida.</p>}
      {ejecutar.isError && <p className="text-amber-900">No se pudo iniciar: {ejecutar.error.message}</p>}
      <Resumen alcance={alcance} u={u} />
      {u && !enCurso && u.alcance === alcance && u.paraCargarAMano + u.cargadosSolos > 0 && (
        <Link href="/compras?nuevos=1" className="text-xs text-finance underline">Ver los documentos para revisar</Link>
      )}
      {u?.inicio && !enCurso && (
        <p className="text-xs text-ink-muted">
          Si no la pedís antes, corre sola el {enDosDias(u.inicio)}.
        </p>
      )}
    </div>
  );
}

/** Búsqueda de documentos nuevos (043), separada en dos (06/11/2026): mails y carpetas por un lado, portales por
 * otro, cada una con su botón; a pedido, y sola si pasan 2 días sin correr. Lo que encuentran queda para revisar en el menú de cada módulo. */
export function RutinaPanel() {
  const q = useQuery({
    queryKey: ["documentos-nuevos", "rutina"], queryFn: getEstadoRutina,
    refetchInterval: (s) => (s.state.data?.ultima?.estado === "en_curso" || s.state.data?.pedidos.length ? 3000 : 15000),
  });
  const qc = useQueryClient();
  const corriendo = q.data?.ultima?.estado === "en_curso" ? q.data.ultima.alcance : null;
  // Al terminar una búsqueda, refrescar ya los avisos del menú (si no, esperan hasta 5 minutos).
  const antes = useRef<string | null>(null);
  useEffect(() => {
    if (antes.current && !corriendo) qc.invalidateQueries({ queryKey: ["documentos-nuevos"] });
    antes.current = corriendo;
  }, [corriendo, qc]);
  if (!q.data) return null;
  const d = q.data;

  return (
    <>
      <AvisoFacturasAtrasadas />
      <section className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
        <h2 className="font-semibold">Buscar documentos nuevos</h2>
        <p className="text-ink-secondary">Corren solo cuando las pedís. Si alguna pasa 2 días sin correr, corre sola.</p>
        <div className="mt-2 flex flex-col gap-2 md:flex-row">
          {(["documentos", "portales"] as const).map((a) => (
            <Rutina key={a} alcance={a}
              u={(a === "documentos" ? d.ultimaDocumentos : d.ultimaPortales)}
              enCola={d.pedidos.includes(a)}
              otraCorriendo={corriendo !== null && corriendo !== a} />
          ))}
        </div>
      </section>
    </>
  );
}

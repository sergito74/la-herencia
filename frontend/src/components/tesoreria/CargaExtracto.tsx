"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { CargaExcel } from "./CargaExcel";
import { CargaExtractoPdf } from "./CargaExtractoPdf";

/** Un solo botón para cargar el extracto del banco (auditoría de Tesorería, mejora 5): acepta el PDF del resumen o el
 * Excel del home banking (Nación o Galicia) y muestra la vista previa en un panel; nada se graba sin confirmar. */
export function CargaExtracto() {
  const [abierto, setAbierto] = useState(false);
  const [archivo, setArchivo] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();
  const cerrar = () => {
    setAbierto(false);
    qc.invalidateQueries({ queryKey: ["tesoreria-movimientos"] });
    qc.invalidateQueries({ queryKey: ["tesoreria-resumen"] });
  };
  const esPdf = archivo?.name.toLowerCase().endsWith(".pdf");

  return (
    <>
      <Button variant="primary" onClick={() => { setArchivo(null); setAbierto(true); setTimeout(() => input.current?.click(), 50); }}>
        Cargar extracto
      </Button>
      <SideDrawer open={abierto} onClose={cerrar} maxWidthClass="max-w-4xl" title="Cargar extracto"
        subtitulo="PDF del resumen o Excel del home banking (Nación o Galicia). Primero ves qué se carga; no se graba nada hasta confirmar.">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input ref={input} type="file" accept=".pdf,.xls,.xlsx" className="hidden" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
            <Button onClick={() => input.current?.click()}>{archivo ? "Elegir otro archivo" : "Elegir archivo"}</Button>
            <span className="text-sm text-ink-secondary">{archivo?.name ?? "Ningún archivo elegido"}</span>
          </div>
          {archivo && (esPdf ? <CargaExtractoPdf key={archivo.name + archivo.size} archivoExterno={archivo} />
            : <CargaExcel key={archivo.name + archivo.size} archivoExterno={archivo} />)}
        </div>
      </SideDrawer>
    </>
  );
}

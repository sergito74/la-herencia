"use client";

import { useEffect, useRef, useState } from "react";

import { esRutaLocalWindows, limpiarRutaCopiada, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { seleccionarArchivo, ubicarArchivo } from "@/services/documentosApi";

interface Props {
  label: string;
  value: string;
  onChange: (ruta: string) => void;
  /** Clases del campo de texto (para que coincida con el resto del formulario). */
  inputClassName: string;
  className?: string;
}

/**
 * Campo "ruta de archivo" con tres formas de cargarlo: escribir/pegar la ruta,
 * arrastrar el archivo sobre el campo, o el menú "Archivo" → "Buscar en esta PC…"
 * (selector de Windows). Un navegador no entrega la ruta completa de un archivo
 * arrastrado ni de un <input type=file>, por eso ambas vías pasan por el backend,
 * que corre en esta misma PC.
 */
export function ArchivoVinculado({ label, value, onChange, inputClassName, className }: Props) {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [arrastrando, setArrastrando] = useState(false);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuAbierto) return;
    const cerrarAlClickAfuera = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuAbierto(false);
    };
    const cerrarConEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuAbierto(false);
    };
    document.addEventListener("mousedown", cerrarAlClickAfuera);
    document.addEventListener("keydown", cerrarConEsc);
    return () => {
      document.removeEventListener("mousedown", cerrarAlClickAfuera);
      document.removeEventListener("keydown", cerrarConEsc);
    };
  }, [menuAbierto]);

  async function buscarEnPc() {
    setMenuAbierto(false);
    setAviso(null);
    setOcupado("Esperando la selección en la ventana de Windows…");
    try {
      const ruta = await seleccionarArchivo(label, value ? limpiarRutaCopiada(value) : null);
      if (ruta) onChange(ruta);
    } catch (e) {
      setAviso(e instanceof Error ? e.message : "No se pudo abrir el selector de archivos.");
    } finally {
      setOcupado(null);
    }
  }

  async function alSoltar(e: React.DragEvent) {
    e.preventDefault();
    setArrastrando(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) {
      setAviso("Soltá un archivo desde el Explorador de Windows.");
      return;
    }
    setAviso(null);
    setOcupado("Buscando el archivo en el disco…");
    try {
      const ruta = await ubicarArchivo(file);
      if (ruta) onChange(ruta);
      else
        setAviso(
          `No encontré «${file.name}» en el disco (busqué en Dropbox, Escritorio, Descargas y Documentos). Usá «Archivo → Buscar en esta PC…» para elegirlo.`
        );
    } catch (err) {
      setAviso(err instanceof Error ? err.message : "No se pudo ubicar el archivo.");
    } finally {
      setOcupado(null);
    }
  }

  const tieneValor = value.trim() !== "";
  const itemMenu = "block w-full px-3 py-1.5 text-left text-xs hover:bg-surface-sunken";

  return (
    <div className={className}>
      <span className="text-xs text-ink-secondary">{label}</span>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={alSoltar}
        className={`rounded-md border border-dashed p-0.5 transition-colors ${
          arrastrando ? "border-finance bg-finance/10" : "border-transparent"
        }`}
      >
        <div className="flex items-center gap-1">
          <input
            className={inputClassName}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={(e) => onChange(limpiarRutaCopiada(e.target.value))}
            placeholder={arrastrando ? "Soltá el archivo acá…" : "Arrastrá el PDF acá, o escribí/pegá la ruta…"}
          />
          {tieneValor && (
            <a
              href={urlParaAbrirDocumento(value, "", urlDocumentoLocal)}
              target="_blank"
              rel="noreferrer"
              title={
                esRutaLocalWindows(value, "")
                  ? "Abre el PDF servido por el backend desde el disco de esta PC."
                  : undefined
              }
              className="whitespace-nowrap text-xs text-finance underline"
            >
              Abrir
            </a>
          )}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={menuAbierto}
              disabled={ocupado !== null}
              onClick={() => setMenuAbierto((v) => !v)}
              className="whitespace-nowrap rounded-md border border-border bg-surface px-2 py-1 text-xs hover:bg-surface-sunken disabled:cursor-not-allowed disabled:opacity-60"
            >
              Archivo ▾
            </button>
            {menuAbierto && (
              <div
                role="menu"
                className="absolute right-0 z-20 mt-1 w-52 overflow-hidden rounded-md border border-border bg-surface shadow-lg"
              >
                <button type="button" role="menuitem" className={itemMenu} onClick={buscarEnPc}>
                  Buscar en esta PC…
                </button>
                {tieneValor && (
                  <>
                    <a
                      role="menuitem"
                      className={itemMenu}
                      href={urlParaAbrirDocumento(value, "", urlDocumentoLocal)}
                      target="_blank"
                      rel="noreferrer"
                      onClick={() => setMenuAbierto(false)}
                    >
                      Abrir archivo
                    </a>
                    <button
                      type="button"
                      role="menuitem"
                      className={`${itemMenu} text-status-danger`}
                      onClick={() => {
                        onChange("");
                        setAviso(null);
                        setMenuAbierto(false);
                      }}
                    >
                      Quitar vínculo
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      {ocupado && <p className="mt-0.5 text-xs text-ink-secondary">{ocupado}</p>}
      {aviso && <p className="mt-0.5 text-xs text-status-danger">{aviso}</p>}
    </div>
  );
}

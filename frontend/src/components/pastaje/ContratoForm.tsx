"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ArchivoVinculado } from "@/components/ui/ArchivoVinculado";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { NumberInput } from "@/components/ui/NumberInput";
import {
  actualizarContrato,
  categoriasHacienda,
  crearContrato,
  type ContratoFicha,
  type Tarifa,
  type TipoTarifa,
} from "@/services/pastajeApi";

import { btnPrimario, btnSecundario, inputCls, tarifaTexto } from "./comunes";

const CLAUSULAS_DEFECTO = {
  clausulaInfraestructura:
    "El titular del campo mantiene en buenas condiciones alambrados, aguadas y molinos para contener la hacienda y asegurar el agua.",
  clausulaSanidad: "Los tratamientos veterinarios y el plan sanitario están a cargo del dueño de la hacienda.",
  clausulaMortandad: "El dueño de la hacienda asume los riesgos de mortandad por causas naturales.",
};

interface TarifaEdit {
  idTipoHacienda: number;
  tipoTarifa: TipoTarifa;
  valor: number | null;
  vigenteDesde: string;
}

/** Alta (sin `contrato`) o edición de un contrato vigente. Las tarifas existentes no se editan: se agregan nuevas con vigencia. */
export function ContratoForm({ contrato, onListo }: { contrato?: ContratoFicha; onListo: (c: ContratoFicha) => void }) {
  const cache = useQueryClient();
  const cats = useQuery({ queryKey: ["pastaje-categorias"], queryFn: categoriasHacienda, staleTime: Infinity });
  const [cliente, setCliente] = useState<number | null>(contrato?.idContacto ?? null);
  const [razon, setRazon] = useState<string | null>(contrato?.cliente ?? null);
  const [inicio, setInicio] = useState(contrato?.fechaInicio ?? "");
  const [fin, setFin] = useState(contrato?.fechaFin ?? "");
  const [carpeta, setCarpeta] = useState(contrato?.carpetaDocumentos ?? "");
  const [archivo, setArchivo] = useState(contrato?.archivoContrato ?? "");
  const [cl, setCl] = useState({
    clausulaInfraestructura: contrato?.clausulaInfraestructura ?? CLAUSULAS_DEFECTO.clausulaInfraestructura,
    clausulaSanidad: contrato?.clausulaSanidad ?? CLAUSULAS_DEFECTO.clausulaSanidad,
    clausulaMortandad: contrato?.clausulaMortandad ?? CLAUSULAS_DEFECTO.clausulaMortandad,
    otrasClausulas: contrato?.otrasClausulas ?? "",
  });
  const [tarifas, setTarifas] = useState<TarifaEdit[]>(contrato ? [] : [{ idTipoHacienda: 3, tipoTarifa: "kg_novillo", valor: 5, vigenteDesde: "" }]);
  const primero = useRef<HTMLDivElement>(null);
  useEffect(() => primero.current?.querySelector("input")?.focus(), []);

  const guardar = useMutation({
    mutationFn: () => {
      const base = {
        idContacto: cliente!,
        fechaInicio: inicio,
        fechaFin: fin || null,
        carpetaDocumentos: carpeta || null,
        archivoContrato: archivo || null,
        ...cl,
        otrasClausulas: cl.otrasClausulas || null,
      };
      const ts: Tarifa[] = tarifas.map((t) => ({
        idTipoHacienda: t.idTipoHacienda,
        tipoTarifa: t.tipoTarifa,
        valor: String(t.valor ?? 0),
        vigenteDesde: t.vigenteDesde || (contrato ? null : inicio),
      }));
      return contrato
        ? actualizarContrato(contrato.id, { ...base, tarifasNuevas: ts, version: contrato.version })
        : crearContrato({ ...base, tarifas: ts });
    },
    onSuccess: (c) => {
      cache.invalidateQueries({ queryKey: ["pastaje"] });
      onListo(c);
    },
  });

  const valido = cliente && inicio && (contrato || tarifas.length > 0) && tarifas.every((t) => (t.valor ?? 0) > 0 && (!contrato || t.vigenteDesde));

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        guardar.mutate();
      }}
    >
      <div ref={primero}>
        <ContactoSelect
          label="Cliente (dueño de la hacienda)"
          value={cliente}
          razonSocial={razon}
          tipoContacto={["Comprador", "Multiple", "Proveedor", "Consignatario"]}
          onChange={(id, nombre) => {
            setCliente(id);
            setRazon(nombre);
          }}
        />
        <p className="mt-1 text-xs text-ink-secondary">Si el cliente no existe, dalo de alta primero en Contactos.</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          Inicio
          <input type="date" className={inputCls} required value={inicio} onChange={(e) => setInicio(e.target.value)} />
        </label>
        <label className="text-sm">
          Fin (opcional)
          <input type="date" className={inputCls} value={fin} onChange={(e) => setFin(e.target.value)} />
        </label>
      </div>
      <p className="text-sm text-ink-secondary">Establecimiento La Herencia · mes vencido · contado · IVA 21%.</p>

      <fieldset className="space-y-2 rounded-sm border border-border p-3">
        <legend className="px-1 text-sm font-semibold">{contrato ? "Agregar tarifa con nueva vigencia" : "Categorías y tarifa"}</legend>
        {contrato?.tarifas.map((t) => (
          <p key={t.id} className="text-sm">
            {cats.data?.find((c) => c.id === t.idTipoHacienda)?.nombre ?? t.idTipoHacienda}: {tarifaTexto(t)} desde {t.vigenteDesde}
          </p>
        ))}
        {tarifas.map((t, i) => (
          <div key={i} className="grid grid-cols-[1fr_1fr_7rem_auto] items-end gap-2">
            <label className="text-sm">
              Categoría
              <select
                className={inputCls}
                value={t.idTipoHacienda}
                onChange={(e) => setTarifas((p) => p.map((x, k) => (k === i ? { ...x, idTipoHacienda: Number(e.target.value) } : x)))}
              >
                {cats.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Tarifa
              <select
                className={inputCls}
                value={t.tipoTarifa}
                onChange={(e) => setTarifas((p) => p.map((x, k) => (k === i ? { ...x, tipoTarifa: e.target.value as TipoTarifa } : x)))}
              >
                <option value="kg_novillo">kg de novillo / cab / mes (INMAG)</option>
                <option value="fijo_ars">$ fijo / cab / mes</option>
                <option value="fijo_usd">us$ fijo / cab / mes</option>
              </select>
            </label>
            <label className="text-sm">
              Valor
              <NumberInput className={inputCls} value={t.valor} maxDecimales={4} onChange={(v) => setTarifas((p) => p.map((x, k) => (k === i ? { ...x, valor: v } : x)))} />
            </label>
            <button type="button" className={btnSecundario} onClick={() => setTarifas((p) => p.filter((_, k) => k !== i))} aria-label="Quitar tarifa">
              Quitar
            </button>
            {contrato && (
              <label className="col-span-4 text-sm">
                Rige desde
                <input type="date" className={inputCls} required value={t.vigenteDesde} onChange={(e) => setTarifas((p) => p.map((x, k) => (k === i ? { ...x, vigenteDesde: e.target.value } : x)))} />
              </label>
            )}
          </div>
        ))}
        <button type="button" className="text-sm underline" onClick={() => setTarifas((p) => [...p, { idTipoHacienda: 3, tipoTarifa: "kg_novillo", valor: 5, vigenteDesde: "" }])}>
          + Agregar categoría
        </button>
      </fieldset>

      {(
        [
          ["clausulaInfraestructura", "Infraestructura (alambrados, aguadas, molinos)"],
          ["clausulaSanidad", "Sanidad"],
          ["clausulaMortandad", "Mortandad y riesgos"],
          ["otrasClausulas", "Otras cláusulas"],
        ] as const
      ).map(([k, label]) => (
        <label key={k} className="block text-sm">
          {label}
          <textarea className={inputCls} rows={2} value={cl[k]} onChange={(e) => setCl((p) => ({ ...p, [k]: e.target.value }))} />
        </label>
      ))}
      <ArchivoVinculado label="Contrato escrito (PDF, opcional)" value={archivo} onChange={setArchivo} inputClassName={inputCls} />
      <label className="block text-sm">
        Carpeta donde se guardan las liquidaciones
        <input className={inputCls} value={carpeta} placeholder="Por defecto: Documents\La Herencia\Ganaderia\Pastaje - La Herencia" onChange={(e) => setCarpeta(e.target.value)} />
      </label>

      {guardar.error && (
        <p role="alert" className="text-sm text-status-danger">
          {(guardar.error as Error).message}
        </p>
      )}
      <button className={btnPrimario} disabled={!valido || guardar.isPending}>
        {guardar.isPending ? "Guardando…" : contrato ? "Guardar cambios" : "Crear contrato"}
      </button>
    </form>
  );
}

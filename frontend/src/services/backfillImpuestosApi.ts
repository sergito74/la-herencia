import { apiGet } from '@/services/apiClient';
export interface PagoBackfill {
  medio:string;idMovimiento:number;fecha:string|null;concepto:string;importe:string;
  importeAGenerar:string;importeCubierto:string;
  estado:string;motivo:string;huella:string;referenciaContable:{origen:string;idOrigen:number}[];
}
export interface DiagnosticoBackfill {
  items:PagoBackfill[];total:number;page:number;pageSize:number;organismo:string;
  huellaFuente:string;saldoActual:string;totalFaltanteConfirmado:string;saldoProyectado:string;
  sinContacto:number;advertencias:string[];
  totalesPorEstado:Record<string,{cantidad:number;importe:string}>;
}
export const organismosBackfill=()=>apiGet<{items:{idOrganismo:number;organismo:string}[]}>('/api/impuestos/backfill/diagnostico');
export const diagnosticoBackfill=(id:number,page:number)=>apiGet<DiagnosticoBackfill>('/api/impuestos/backfill/diagnostico',{organismoId:id,page});

import { apiPost,apiPatch,API_BASE_URL,ApiError } from '@/services/apiClient';
export interface ArchivoBackfill {archivoId:string;nombre:string;idOrganismo:number|null;usado:boolean;fecha:string|null}
export type TipoBackfill={modo:'generico'}|{modo:'existente';idTipoImpuesto:number};
export interface DecisionBackfill {medio:string;idMovimiento:number;accion:'incluir'|'excluir';fuente?:'generada'|'comprobante';archivoId?:string;tipoImpuesto?:TipoBackfill;confirmacionDocumento?:boolean;periodoLiquidado?:string;numeroDocumento?:string}
export interface PropuestaBackfill extends Omit<DiagnosticoBackfill,'items'> {items:(PagoBackfill&{fuente:string;candidatos:ArchivoBackfill[]})[];tipos:{idTipoImpuesto:number;nombre:string}[];archivos:ArchivoBackfill[];coberturaBusqueda:boolean}
export interface RevisionBackfill {huellaPropuesta:string;preparacion:string;cantidad:number;total:string;saldoProyectado:string}
export const propuestaBackfill=(organismoId:number,page:number)=>apiGet<PropuestaBackfill>('/api/impuestos/backfill/propuesta',{organismoId,page});
export const validarBackfill=(body:unknown)=>apiPost<RevisionBackfill>('/api/impuestos/backfill/validar',body);
export const confirmarBackfill=(body:unknown)=>apiPost<{lote:{IdLote:string;Cantidad:number;Total:string};repetido:boolean}>('/api/impuestos/backfill/confirmar',body);
export const archivoUrl=(id:string,org:number)=>`${API_BASE_URL}/api/impuestos/backfill/comprobantes/${id}?organismoId=${org}`;
export async function estadoRespaldo(token:string):Promise<{estado:string;backupId?:string;motivo?:string}>{
 const res=await fetch(`${API_BASE_URL}/api/impuestos/backfill/respaldo`,{credentials:'include',headers:{'X-Backfill-Preparacion':token}});
 if(!res.ok)throw new ApiError(res.status,'No se pudo verificar el respaldo');return res.json();
}
export async function crearRespaldo(token:string):Promise<{estado:string;backupId:string}>{
 const res=await fetch(`${API_BASE_URL}/api/impuestos/backfill/respaldo`,{method:'POST',credentials:'include',headers:{'X-Backfill-Preparacion':token}});
 if(!res.ok){const t=await res.text().catch(()=>'');let m=t;try{m=JSON.parse(t).detail??t;}catch{}throw new ApiError(res.status,m||'No se pudo generar el respaldo');}
 return res.json();
}
export const lotesBackfill=(page=1)=>apiGet<{items:{idLote:string;idOrganismo:number;estado:string;cantidad:number;total:string}[];total:number}>('/api/impuestos/backfill/lotes',{page});
export const detalleLote=(id:string)=>apiGet<{Estado:string;boletas:{idImpuesto:number|null;idImpuestoHistorico:number;origenCreacion:string;tieneComprobante:boolean;version:string}[];eventos:{tipo:string;usuario:string;fecha:string}[]}>(`/api/impuestos/backfill/lotes/${id}`);
export const preRevertir=(id:string)=>apiPost<{bloqueos:string[];preparacion?:string;huellaReversion:string}>(`/api/impuestos/backfill/lotes/${id}/reversion/validar`,{});
export const revertirBackfill=(id:string,body:unknown)=>apiPost(`/api/impuestos/backfill/lotes/${id}/revertir`,body);
export const corregirTipo=(id:number,version:string,idTipoImpuesto:number)=>apiPatch(`/api/impuestos/backfill/boletas/${id}/tipo`,{version,idTipoImpuesto});
export const adjuntarBackfill=(id:number,version:string,archivoId:string)=>apiPatch(`/api/impuestos/backfill/boletas/${id}/comprobante`,{version,archivoId,confirmadoPorUsuario:true});

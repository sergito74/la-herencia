import { apiGet, apiPost, apiPatch, API_BASE_URL } from './apiClient';
export interface FacturaOP { idCompra: number; numero: string | null; fecha: string | null; total: number; pagado: number; saldo: number; reservado: number; disponible: number }
export interface MedioOP { medio: 'Transferencia' | 'Efectivo' | 'Cheque'; cuenta: string; importe: number }
export interface OrdenInput { idContacto: number; fecha: string; fechaPago: string; moneda: 'ARS'; observaciones: string; facturas: { idCompra: number; importe: number }[]; medios: MedioOP[]; version?: number }
export interface OrdenOP extends OrdenInput { idOrdenPago: number; proveedor: string; importeTotal: number; estado: 'Borrador'|'Emitida'|'Pagada'|'Anulada'; facturas: { idCompra: number; importe: number; numero: string | null }[] }
export interface ReciboOP { idDocumentoNuevo: number; idContacto: number | null; proveedor: string | null; numero: string | null; fecha: string | null; total: number | null; revisado: string | null; idRecibo: number | null; idOrdenPago: number | null }
export interface MovimientoOP { origenMovimiento: 'galicia'|'bna'|'efectivo'; idMovimiento: number; fecha: string | null; importe: number; disponible: number }
export interface AplicacionOP { origenMovimiento: MovimientoOP['origenMovimiento']; idMovimiento: number; idCompra: number; importe: number }
export interface VincularOP { idContacto: number; numero: string; fecha: string; total: number; moneda: 'ARS'; idOrdenPago: number | null; aplicaciones: AplicacionOP[] }
const base='/api/ordenes-pago';
export const listarOP=(params: {idContacto?:number;estado?:string;page?:number})=>apiGet<{items:OrdenOP[];total:number}>(base,params);
export const obtenerOP=(id:number)=>apiGet<OrdenOP>(`${base}/${id}`);
export const facturasOP=(idContacto:number,excluirOrden?:number,incluirSaldadas=false)=>apiGet<FacturaOP[]>(`${base}/facturas`,{idContacto,excluirOrden,incluirSaldadas:String(incluirSaldadas)});
export const guardarOP=(body:OrdenInput,id?:number)=>id?apiPatch<OrdenOP>(`${base}/${id}`,body):apiPost<OrdenOP>(base,body);
export const estadoOP=(id:number,accion:'emitir'|'anular')=>apiPost<OrdenOP>(`${base}/${id}/${accion}`,{});
export const recibosOP=(params:{idContacto?:number;revisados?:boolean;page?:number})=>apiGet<{items:ReciboOP[];total:number}>(`${base}/recibos`,{...params,revisados:params.revisados?"true":undefined});
export const movimientosOP=(idContacto:number)=>apiGet<MovimientoOP[]>(`${base}/movimientos`,{idContacto});
export const vincularOP=(id:number,body:VincularOP)=>apiPost(`${base}/recibos/${id}/vincular`,body);
export const pdfOP=(id:number)=>`${API_BASE_URL}${base}/recibos/${id}/pdf`;

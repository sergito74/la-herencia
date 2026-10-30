import { apiGet, apiPost, apiPatch, apiPut, apiDelete, API_BASE_URL } from './apiClient';
export interface FacturaOP { idCompra: number; numero: string | null; fecha: string | null; moneda?: string | null; tc?: number | null; total: number; pagado: number; saldo: number; reservado: number; disponible: number }
export interface MedioOP { medio: 'Transferencia' | 'Efectivo' | 'Cheque'; cuenta: string; importe: number }
export interface OrdenInput { idContacto: number; fecha: string; fechaPago: string; moneda: 'ARS'; observaciones: string; facturas: { idCompra: number; importe: number }[]; medios: MedioOP[]; retenciones?: RetencionOP[]; repartoNeto?: { idCompra: number; importe: number; numero: string | null }[]; version?: number }
export interface OrdenOP extends OrdenInput { idOrdenPago: number; proveedor: string; importeTotal: number; retencionGanancias: number; retenciones?: RetencionOP[]; estado: 'Borrador'|'Emitida'|'Pagada'|'Anulada'; facturas: { idCompra: number; importe: number; numero: string | null }[] }
export interface ReciboOP { idDocumentoNuevo: number; idContacto: number | null; proveedor: string | null; numero: string | null; fecha: string | null; total: number | null; revisado: string | null; idRecibo: number | null; idOrdenPago: number | null }
export interface MovimientoOP { origenMovimiento: 'galicia'|'bna'|'efectivo'; idMovimiento: number; fecha: string | null; importe: number; disponible: number }
export interface AplicacionOP { origenMovimiento: MovimientoOP['origenMovimiento']; idMovimiento: number; idCompra: number; importe: number }
export interface VincularOP { idContacto: number; numero: string; fecha: string; total: number; moneda: 'ARS'; idOrdenPago: number | null; aplicaciones: AplicacionOP[]; retencion: number; certificadoRetencion: string | null; anticipo: number }
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
export interface RetencionOP { codRegimen: number; concepto: string; basePago: number; pagosAnteriores: number; retencionesAnteriores: number; alicuota: number; noSujeto: number; retencion: number; simulador?: string }
export interface PropuestaRetencion { condicion: { retiene: boolean; motivo?: string; aviso?: string; inscripto?: boolean; padronAl?: string }; lineas: RetencionOP[]; total: number; avisos: string[] }
export interface RubroRetencion { idRubro: number; rubro: string; codRegimen: number | null; estado: 'Borrador'|'Validado contador'|'Ratificado estudio'; observaciones: string | null }
export interface Regimen { codRegimen: number; concepto: string; alicuota: number; noSujeto: number }
export interface Exclusion { idExclusion: number; idContacto: number; proveedor: string; desde: string; hasta: string; observaciones: string | null }
export const proponerRetencion=(body:{idContacto:number;fechaPago:string;facturas:{idCompra:number;importe:number}[];excluirOrden?:number})=>apiPost<PropuestaRetencion>(`${base}/retenciones/proponer`,body);
export const rubrosRetencion=()=>apiGet<RubroRetencion[]>(`${base}/retenciones/rubros`);
export const regimenesRetencion=()=>apiGet<Regimen[]>(`${base}/retenciones/regimenes`);
export const guardarRubroRetencion=(id:number,body:Omit<RubroRetencion,'idRubro'|'rubro'>)=>apiPut(`${base}/retenciones/rubros/${id}`,body);
export const exclusionesRetencion=()=>apiGet<Exclusion[]>(`${base}/retenciones/exclusiones`);
export const agregarExclusion=(body:{idContacto:number;desde:string;hasta:string;observaciones:string})=>apiPost(`${base}/retenciones/exclusiones`,body);
export const borrarExclusion=(id:number)=>apiDelete(`${base}/retenciones/exclusiones/${id}`);
export const actualizarPadron=()=>apiPost<{contactosConCuit:number;encontrados:number;actualizado:string}>(`${base}/retenciones/padron`,{});
export const mailEstudioOP=(id:number)=>`${API_BASE_URL}${base}/${id}/mail-estudio`;
export const conciliarEmitidas=()=>apiPost<{pagadas:number[];ambiguas:number[]}>(`${base}/conciliar-emitidas`,{});

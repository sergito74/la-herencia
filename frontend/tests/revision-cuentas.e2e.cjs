// 036 — Revisión sistemática de cuentas: tablero, cola con lote, ficha con pagos sin factura y saldo externo, y archivos incompletos.
// API simulada (no toca WC). Servidor en el puerto 3100: `node tests/revision-cuentas.e2e.cjs`.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');

const CORS={'access-control-allow-origin':'http://127.0.0.1:3100','access-control-allow-credentials':'true','access-control-allow-headers':'content-type,x-lock-token','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'};

const tablero={corte:'2026-09-30',totalCuentas:518,
 porEstado:{pendiente:517,'en-proceso':0,'esperando-evidencia':0,'esperando-sergio':1,cerrada:0,'cerrada-con-excepcion':0,reabierta:0},
 casillas:[{cola:'D',etapa:'E1',cuentas:75,importe:38000000},{cola:'I',etapa:'E4',cuentas:16,importe:1200000},{cola:'A',etapa:'E0',cuentas:363,importe:500000}],
 totalesPorCola:{A:{cuentas:363,importe:500000},D:{cuentas:75,importe:38000000},I:{cuentas:16,importe:1200000}},
 comparacion:{semanaAnterior:'2026-10-05',cerradasEnLaSemana:12,variacionExcepciones:-2},preguntas:1};
const preguntas=[{idContacto:7,razonSocial:'Agroneyer S.A.',cola:'D',etapa:'E1',pregunta:'¿Hay estado de cuenta del proveedor de 2015?',desde:'2026-10-08T10:00:00'}];

const criterios=(cumpleC1)=>[
 {codigo:'C1',etapa:'E1',cumple:cumpleC1,medido:cumpleC1?'0 pagos sin factura desde 2021':'1 pago sin factura por $ 1.582.000,00',texto:'Hay pagos sin factura que los respalde',evidencia:null},
 {codigo:'C2',etapa:'E2',cumple:true,medido:'Sin contactos duplicados ni movimientos sin contacto',texto:'Los movimientos y contactos están bien asignados',evidencia:null},
 {codigo:'C3',etapa:'E4',cumple:true,medido:'Diferencia contra el saldo del proveedor: $ 0,00 (cierra)',texto:'El saldo está respaldado por evidencia externa',evidencia:'portal'},
 {codigo:'C4',etapa:'E3',cumple:true,medido:'0 casos de doble conteo con tarjeta',texto:'La tarjeta no se cuenta dos veces',evidencia:null},
 {codigo:'C5',etapa:'E5',cumple:true,medido:'Imputaciones completas y sin sobrantes',texto:'Las imputaciones están sanas',evidencia:null},
 {codigo:'C6',etapa:'E4',cumple:true,medido:'Sin impuestos sin boleta ni retenciones sin certificado',texto:'Los pendientes están tipificados',evidencia:null},
 {codigo:'C7',etapa:'E6',cumple:true,medido:'Inventario de fuentes confirmado y saldo estable al corte',texto:'La cuenta tiene trazabilidad',evidencia:null}];

(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  // estado de la API simulada
  let lote=null,tildadas=[],aplicado=false,marcas=[],saldosCargados=[],estadoFicha='pendiente',cierres=[],decisiones=[],marcaPago=null;
  const loteJson=()=>({idCorreccion:600,regla:'aprobar-cierre',cola:'A',estado:aplicado?'aplicada':'simulada',respaldo:aplicado?'WC_lote-036-600.bak':null,
   cuentas:[{idContacto:1,razonSocial:'Unipase',tildada:tildadas.includes(1),cumple:true,saldoAntes:10,saldoDespues:10,detalle:''},
            {idContacto:2,razonSocial:'Sin evidencia SRL',tildada:false,cumple:false,saldoAntes:0,saldoDespues:0,detalle:'No cumple: C3: Sin saldo externo y sin coincidencia con el Access'}]});
  const fichaJson=()=>({idContacto:7,razonSocial:'Agroneyer S.A.',corte:'2026-09-30',estado:estadoFicha,estadoEfectivo:estadoFicha,etapa:marcaPago?'E6':'E1',cola:marcaPago?'A':'D',otrosProblemas:[],
   saldoAlCorte:-1500,moneda:'Pesos',saldoEsperado:null,criterios:criterios(Boolean(marcaPago)),inventarioFuentes:[{tipo:'access',disponible:true}],pagosSinFactura:marcaPago?0:1,saldosExternos:saldosCargados.length,
   antecedente035:{estado:'revisada',nota:'Revisada con otro criterio',fecha:'2026-10-02T10:00:00'},fifoAplicadoAntes:true,pregunta:null,
   cierre:estadoFicha==='cerrada'?{corte:'2026-09-30',saldoAlCierre:-1500,usuario:'fixture',fecha:'2026-10-09T10:00:00',conExcepcion:false,motivoExcepcion:null}:null,historial:[]});
  const pagoJson=()=>({medio:'galicia',idMovimiento:2794,fecha:'2025-09-18',importe:1563484.73,retencionAsociada:18515.27,importeEsperadoFactura:1582000,
   fechaEsperadaDesde:'2025-09-08',fechaEsperadaHasta:'2025-09-16',confianza:'alta',anteriorA2021:false,marca:marcaPago});

  await page.route('**/api/**',async route=>{
   const req=route.request(),u=new URL(req.url()),path=u.pathname,m=req.method();
   const json=(x,status=200)=>route.fulfill({status,headers:CORS,contentType:'application/json',body:JSON.stringify(x)});
   if(m==='OPTIONS')return route.fulfill({status:204,headers:CORS});
   if(path==='/api/auth/me')return json({idUsuario:1,usuario:'fixture',nombre:'Fixture',rol:'Administrador'});
   // ---- 036
   if(path==='/api/revision-cuentas/tablero')return json(tablero);
   if(path==='/api/revision-cuentas/preguntas')return json(preguntas);
   if(path==='/api/revision-cuentas/reglas')return json([{regla:'aprobar-cierre',cola:'A',descripcion:'Cierra al corte las cuentas ya sanas, con la referencia del Access como evidencia'}]);
   if(path==='/api/revision-cuentas/colas/A')return json({cola:'A',total:2,pagina:1,cuentas:[
     {idContacto:1,razonSocial:'Unipase',movimientos:1,importe:100,saldo:10,moneda:'Pesos',etapa:'E0',estado:'pendiente',otrosProblemas:[]},
     {idContacto:2,razonSocial:'Sin evidencia SRL',movimientos:4,importe:900,saldo:0,moneda:'Pesos',etapa:'E0',estado:'pendiente',otrosProblemas:['I']}]});
   if(path==='/api/revision-cuentas/lotes/simular'&&m==='POST'){lote=true;return json(loteJson(),201);}
   if(path==='/api/revision-cuentas/lotes/600/cuentas'&&m==='PUT'){const b=req.postDataJSON();tildadas=b.tildarTodas?[1]:(b.idsContacto||[]);return json(loteJson());}
   if(path==='/api/revision-cuentas/lotes/600/aplicar'&&m==='POST'){aplicado=true;return json(loteJson());}
   if(path==='/api/revision-cuentas/archivos/incompletos')return json({raiz:'C:\\Compras',total:2,archivos:[
     {ruta:'C:\\Compras\\04 2025 - 03 2026\\20250923_JaureguiYMorales.crdownload',periodo:'04 2025 - 03 2026',proveedor:'JaureguiYMorales',fecha:'2025-09-23',estado:'comprobante-legible-extension-incorrecta',numero:'0009-00077393',importe:30017.03,cargado:true,idCompra:1},
     {ruta:'C:\\Compras\\04 2025 - 03 2026\\20251212_Otro.crdownload',periodo:'04 2025 - 03 2026',proveedor:'Otro',fecha:'2025-12-12',estado:'vacio',numero:null,importe:null,cargado:false,idCompra:null}]});
   if(path==='/api/revision-cuentas/cuentas/7/ficha'&&m==='GET')return json(fichaJson());
   if(path==='/api/revision-cuentas/cuentas/7/ficha'&&m==='PUT'){const b=req.postDataJSON();cierres.push(b);estadoFicha=b.estado;return json(fichaJson());}
   if(path==='/api/revision-cuentas/cuentas/7/pagos-sin-factura'&&m==='GET')return json({idContacto:7,corte:'2026-09-30',consistencia:{pagosSinFactura:1582000,facturasSinPago:0,saldo:1582000,cierra:true,sinApertura:false},
     pagos:marcaPago&&marcaPago.estado==='sin-documento'?[pagoJson()]:[pagoJson()],facturasSinPago:[]});
   if(path==='/api/revision-cuentas/cuentas/7/pagos-sin-factura/galicia/2794'&&m==='PUT'){const b=req.postDataJSON();marcas.push(b);marcaPago={estado:b.estado,nota:b.nota,idCompra:null,fuenteRespaldo:b.fuenteRespaldo};return json(pagoJson());}
   if(path==='/api/revision-cuentas/cuentas/7/saldos-externos'&&m==='GET')return json(saldosCargados);
   if(path==='/api/revision-cuentas/cuentas/7/saldos-externos'&&m==='POST'){const b=req.postDataJSON();const s={idSaldoExterno:1,...b,saldoCuentaALaFecha:-1500,diferencia:-1500-b.saldo,clasificacion:'cierra'};saldosCargados.push(s);return json(s,201);}
   if(path==='/api/revision-cuentas/cuentas/7/decisiones')return json(decisiones);
   // ---- 035 (pantalla de la cuenta)
   if(path==='/api/auditoria-cuentas/cuentas/7/revision')return json({idContacto:7,razonSocial:'Agroneyer S.A.',moneda:'Pesos',saldo:-1500,saldoEsperado:null,estado:'pendiente',fechaRevision:null,usuarioRevision:null,nota:null,saldoAlRevisar:null,dificultad:1,
     avisos:[],siguiente:null,anterior:null,revisadas:3,totalCuentas:505,historial:[]});
   if(path==='/api/auditoria-cuentas/cuentas/7/hallazgos')return json({idContacto:7,razonSocial:'Agroneyer S.A.',hallazgos:[]});
   if(path==='/api/auditoria-cuentas/cuentas/7/comprobantes')return json({});
   if(path==='/api/auditoria-cuentas/cuentas/7/correcciones')return json([]);
   if(path==='/api/auditoria-cuentas/cuentas/7/movimientos')return json({page:1,pageSize:100,total:0,saldoPesos:-1500,saldoDolares:0,tieneDolares:false,bimonetaria:false,gobierna:'Pesos',saldoGobierna:-1500,avisos:[],items:[]});
   return json({items:[],total:0});
  });

  // 1) Tablero
  await page.goto('http://127.0.0.1:3100/finanzas/revision-cuentas');
  await page.getByRole('heading',{name:'Revisión de cuentas'}).waitFor();
  await page.getByText('518').first().waitFor();
  assert.ok(await page.getByText(/16 \(3,1 %\)/).count()>0,'muestra la cola de excepciones y su porcentaje');
  await page.getByText(/\+12 cuentas\s+cerradas/).waitFor();
  await page.getByText('¿Hay estado de cuenta del proveedor de 2015?').waitFor();
  const filas=await page.locator('tbody tr').allInnerTexts();
  assert.ok(filas.some(f=>/D: Pago sin factura/.test(f)&&/75/.test(f)),'la cola D con 75 cuentas');
  assert.ok(filas.some(f=>/A: Ya sanas/.test(f)&&/363/.test(f)),'la cola A con 363 cuentas');

  // 2) Cola A y lote
  await page.getByRole('link',{name:/A: Ya sanas/}).click();
  await page.getByRole('heading',{name:/Cola A: Ya sanas/}).waitFor();
  await page.getByRole('link',{name:'Unipase'}).first().waitFor();
  await page.getByRole('button',{name:/Armar el lote/}).click();
  await page.getByText(/Lote\s+#600/).waitFor();
  assert.equal(await page.getByRole('checkbox',{name:/Tildar Unipase/}).isChecked(),false,'ninguna cuenta viene tildada de antemano');
  assert.equal(await page.getByRole('checkbox',{name:/Tildar Sin evidencia SRL/}).isDisabled(),true,'una cuenta que no cumple no se puede tildar');
  await page.getByRole('button',{name:'Tildar todas las que cumplen'}).click();
  await page.waitForTimeout(300);
  assert.equal(await page.getByRole('checkbox',{name:/Tildar Unipase/}).isChecked(),true);
  await page.getByRole('button',{name:'Aplicar a las tildadas'}).click();
  await page.getByRole('button',{name:'Sí, aplicar'}).click();
  await page.getByText('Lote aplicado.').waitFor();
  await page.getByRole('button',{name:'Revertir el lote'}).waitFor();

  // 3) Ficha de una cuenta: pagos sin factura, saldo externo y cierre
  await page.goto('http://127.0.0.1:3100/finanzas/auditoria-cuentas/cuenta/7');
  await page.getByRole('heading',{name:'Ficha de la cuenta'}).waitFor();
  assert.equal(await page.locator('ol[aria-label="Etapas"] li').count(),7,'siete etapas');
  assert.equal(await page.getByText(/^C[1-7]$/).count(),7,'siete criterios');
  await page.getByText(/Antecedente: se marcó/).waitFor();
  await page.getByText(/FIFO aplicado antes del método/).waitFor();
  await page.getByText(/Factura esperada:/).waitFor();
  assert.ok(await page.getByText(/1\.582\.000,00/).count()>0,'importe esperado de la factura');
  assert.equal(await page.getByRole('button',{name:'Cerrar al corte'}).isDisabled(),true,'no se puede cerrar con un criterio sin cumplir');
  await page.getByRole('button',{name:'Marcar',exact:true}).first().click();
  await page.getByLabel(/Nota/).last().fill('No hay documento: decisión mía');
  await page.getByRole('button',{name:'Guardar marca'}).click();
  await page.waitForTimeout(400);
  assert.ok(marcas.some(x=>x.estado==='sin-documento'&&x.nota==='No hay documento: decisión mía'),'se guardó la marca');
  await page.getByRole('button',{name:'Cargar un saldo'}).click();
  await page.locator('input[type="date"]').fill('2026-09-30');
  await page.getByLabel(/Qué informa el proveedor/).selectOption('nos-debe');
  await page.getByLabel(/Importe, sin signo/).fill('0,01');
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  await page.waitForTimeout(400);
  assert.equal(saldosCargados.length,1);
  assert.equal(saldosCargados[0].fuente,'portal');
  assert.equal(saldosCargados[0].saldo,0.01,'"nos debe" se guarda con signo positivo');
  await page.getByRole('button',{name:'Cerrar al corte'}).waitFor();
  await page.waitForTimeout(300);
  assert.equal(await page.getByRole('button',{name:'Cerrar al corte'}).isDisabled(),false,'con los 7 criterios se puede cerrar');
  await page.getByRole('button',{name:'Cerrar al corte'}).click();
  await page.getByRole('button',{name:'Sí, cerrar'}).click();
  await page.waitForTimeout(400);
  assert.ok(cierres.some(c=>c.estado==='cerrada'),'se pidió el cierre');
  await page.getByText(/Cerrada al corte del/).waitFor();

  // 4) Archivos incompletos
  await page.goto('http://127.0.0.1:3100/finanzas/revision-cuentas/archivos');
  await page.getByRole('heading',{name:'Archivos incompletos de comprobantes'}).waitFor();
  await page.getByText('20250923_JaureguiYMorales.crdownload').waitFor();
  await page.getByText('Ya está cargado').waitFor();
  await page.getByText('Falta cargar').waitFor();

  assert.deepEqual(errors,[]);
  console.log('OK: tablero, cola con lote (nada tildado de antemano, aplicar), ficha con pagos sin factura, saldo externo y cierre, y archivos incompletos.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});

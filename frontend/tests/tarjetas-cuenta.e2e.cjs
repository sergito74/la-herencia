const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let cruces=[],aprobados=0,consultasCuenta=[];
 const hallazgo={categoria:'consumo-sin-proveedor',idTarjeta:4,tarjeta:'Visa Galicia',medio:null,idMovimiento:null,idResumen:5,idLineaConsumo:9,fecha:'2026-01-01',importe:1000,motivo:'Parte del consumo sin proveedor ni factura vinculada'};
 const sugerencia={tipo:'devolucion-debito',idTarjeta:1,origen:{medio:'bna',idMovimiento:9426,fecha:'2025-09-17',importe:966654.2,concepto:'OTROS CONCEPTOS-VS'},destino:{medio:'bna',idMovimiento:18093,fecha:'2025-09-01',importe:966654.2,concepto:'PM/TOT. RES. AGRONACION'},diasDiferencia:16,diferenciaImporte:0,puntaje:0.88};
 const cuenta=(agrupar)=>({idTarjeta:1,tarjeta:'AgroNacion',idContacto:373,desde:null,hasta:null,saldoInicial:0,
  filas:[{fecha:'2026-09-01',origen:'Consumo',idResumen:7,codigo:'R7',detalle:'Consumo prueba',proveedor:'Proveedor',deuda:100,credito:0,saldo:-100,estadoVinculo:'vinculado',referencia:{tipo:'linea-consumo',idLineaConsumo:8,idResumen:7}},
         {fecha:'2026-09-20',origen:'Pago',idResumen:7,codigo:null,detalle:'PM/TOT RES',proveedor:null,deuda:0,credito:100,saldo:0,estadoVinculo:null,referencia:{tipo:'movimiento-bancario',medio:'bna',idMovimiento:50,idResumen:7}}],
  saldoFinal:0,detalleSaldo:{exigible:0,noResumido:0},cuotasAVencer:[],apertura:{idContactoAnterior:null,contactoAnterior:null,informativo:true},avisoSaldo:'El saldo es información de gestión: no sirve para IVA ni para impuestos.',_agrupar:agrupar});
 await page.route('**/api/**',async route=>{
  const req=route.request(),u=new URL(req.url()),path=u.pathname;
  const headers={'access-control-allow-origin':'http://127.0.0.1:3100','access-control-allow-credentials':'true','access-control-allow-headers':'content-type,x-lock-token','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'};
  const json=(x,status=200)=>route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(x)});
  if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
  if(path==='/api/auth/me')return json({idUsuario:1,usuario:'fixture',nombre:'Fixture',rol:'Administrador'});
  if(path==='/api/tarjetas')return json([{idTarjeta:1,nombre:'AgroNacion',banco:'BNA',activa:true}]);
  if(path==='/api/tarjetas-cuenta/resumen')return json({hasta:'2026-10-06',tarjetas:[{idTarjeta:1,tarjeta:'AgroNacion',banco:'BNA',activa:true,idContacto:373,deuda:200,credito:200,saldo:0,pendienteNeto:0,diferenciaConModuloTarjetas:0,ultimoMovimiento:'2026-09-20',cuotasAVencer:0}],total:{deuda:200,credito:200,saldo:0},tarjetasSinContacto:[],avisoSaldo:'aviso'});
  if(path==='/api/tarjetas-cuenta/control')return json({generado:'2026-10-06T10:00:00',resumenPorCategoria:{'consumo-sin-proveedor':1},hallazgos:[hallazgo]});
  if(path==='/api/tarjetas-cuenta/cruces/sugerencias')return json({sugerencias:u.searchParams.get('tipo')==='devolucion-debito'&&aprobados===0?[sugerencia]:[]});
  if(path==='/api/tarjetas-cuenta/cruces'&&req.method()==='POST'){aprobados++;const b=req.postDataJSON();assert.equal(b.origen.idMovimiento,9426);assert.equal(b.destino.idMovimiento,18093);cruces=[{idCruce:1,tipo:'devolucion-debito',idTarjeta:1,importe:966654.2,sugerido:true,usuario:'fixture',fecha:'2026-10-06T10:00:00',deshecho:false,usuarioDeshecho:null,fechaDeshecho:null}];return json({idCruce:1,tipo:'devolucion-debito',importe:966654.2,usuario:'fixture',fecha:'2026-10-06T10:00:00'},201);}
  if(path==='/api/tarjetas-cuenta/cruces')return json(cruces);
  if(path==='/api/tarjetas-cuenta/1'){consultasCuenta.push(u.search);return json(cuenta(u.searchParams.get('agrupar')));}
  return json({items:[],total:0});
 });
 const base='http://127.0.0.1:3100';
 await page.goto(base+'/finanzas/tarjetas');
 await page.getByText('Lo que se debe a cada tarjeta').waitFor();
 await page.getByRole('link',{name:'AgroNacion'}).first().click();
 await page.waitForURL(/\/finanzas\/tarjetas\/1\/cuenta-corriente/);
 await page.getByText('Saldo final').waitFor();
 await page.getByText('El saldo es información de gestión').waitFor();
 assert.equal(await page.getByRole('link',{name:'Exportar a Excel'}).getAttribute('href').then(h=>h.includes('/api/tarjetas-cuenta/1/exportar')),true);
 const tesoreria=await page.getByRole('link',{name:'PM/TOT RES'}).getAttribute('href');
 assert.match(tesoreria,/\/finanzas\/tesoreria\?medio=bna&highlight=50/);
 await page.getByLabel('Desde').fill('2026-09-01');
 await page.getByLabel('Ver por resumen').check();
 await page.waitForTimeout(500);
 assert.ok(consultasCuenta.some(q=>q.includes('desde=2026-09-01')&&q.includes('agrupar=resumenes')));
 await page.goto(base+'/finanzas/tarjetas/control');
 await page.getByText('Parte del consumo sin proveedor').waitFor();
 await page.getByText('Devoluciones del banco para cruzar con su débito').waitFor();
 await page.getByRole('button',{name:'Revisar y aprobar'}).click();
 await page.getByRole('button',{name:'Aprobar cruce'}).click();
 await page.getByText('#1').waitFor();
 assert.equal(aprobados,1);
 assert.deepEqual(errors,[]);
 console.log('OK: saldos, cuenta con filtros y por resumen, vínculo a Tesorería, control y aprobación de un cruce.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});

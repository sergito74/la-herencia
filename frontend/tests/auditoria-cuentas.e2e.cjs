const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let estado='pendiente',guardados=[],anulaciones=[],anuladas=false;
 const revision=()=>({idContacto:7,razonSocial:'Agroneyer S.A.',moneda:'Pesos',saldo:-1500,saldoEsperado:null,estado,fechaRevision:estado==='pendiente'?null:'2026-10-06T10:00:00',usuarioRevision:'fixture',nota:estado==='pendiente'?null:'ok',saldoAlRevisar:-1500,dificultad:2,
  avisos:[{tipo:'aplicacion-fuera-de-plazo',motivo:'Hay pagos aplicados a facturas de hace mucho tiempo',importe:null}],siguiente:{idContacto:8,razonSocial:'Agropark'},anterior:null,revisadas:3,totalCuentas:505,historial:[]});
 const hallazgos={idContacto:7,razonSocial:'Agroneyer S.A.',hallazgos:anuladas?[]:[{causa:'aplicacion-fuera-de-plazo',motivo:'El pago se aplicó a facturas de hace más de 24 meses',importe:5000,medio:'galicia',idMovimiento:3240,cantidadFacturas:2,facturaMasVieja:'2019-05-07',idsAplicacion:[11,12]}]};
 await page.route('**/api/**',async route=>{
  const req=route.request(),u=new URL(req.url()),path=u.pathname;
  const headers={'access-control-allow-origin':'http://127.0.0.1:3100','access-control-allow-credentials':'true','access-control-allow-headers':'content-type,x-lock-token','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'};
  const json=(x,status=200)=>route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(x)});
  if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
  if(path==='/api/auth/me')return json({idUsuario:1,usuario:'fixture',nombre:'Fixture',rol:'Administrador'});
  if(path==='/api/auditoria-cuentas/cuentas/7/revision'&&req.method()==='GET')return json(revision());
  if(path==='/api/auditoria-cuentas/cuentas/7/revision'&&req.method()==='PUT'){const b=req.postDataJSON();guardados.push(b);if(b.estado)estado=b.estado;return json(revision());}
  if(path==='/api/auditoria-cuentas/cuentas/7/hallazgos')return json({...hallazgos,hallazgos:anuladas?[]:hallazgos.hallazgos});
  if(path==='/api/auditoria-cuentas/cuentas/7/comprobantes')return json({'100':'04 2026 - 03 2027\\a.pdf#04 2026 - 03 2027\\a.pdf#'});
  if(path==='/api/auditoria-cuentas/cuentas/7/correcciones')return json([]);
  if(path==='/api/auditoria-cuentas/cuentas/7/anular-aplicaciones'){const b=req.postDataJSON();anulaciones.push(b);anuladas=true;return json({idCorreccion:1,aplicaciones:b.idsAplicacion.length,importe:5000},201);}
  if(path==='/api/auditoria-cuentas/cuentas/7/movimientos')return json({page:1,pageSize:100,total:2,saldoPesos:-1500,saldoDolares:-1.2,tieneDolares:true,bimonetaria:true,gobierna:'Mixta',saldoGobierna:-1500,avisos:[],items:[
   {fecha:'2026-09-01',documento:'Factura',numeroDocumento:'0001-1',moneda:'Dolares',deudaOriginal:15,creditoOriginal:0,tipoDeCambio:100,tcEstimado:false,deudaPesos:1500,creditoPesos:0,saldoPesos:-1500,saldoDolares:-15,origen:{tipo:'compra',idCompra:100,numeroDocumento:'0001-1',proveedor:'Agroneyer'},origenTipo:'Compras',idOrigen:100},
   {fecha:'2026-08-01',documento:'Pago',numeroDocumento:null,moneda:'Pesos',deudaOriginal:0,creditoOriginal:500,tipoDeCambio:null,tcEstimado:false,deudaPesos:0,creditoPesos:500,saldoPesos:0,saldoDolares:-9,origen:{tipo:'tesoreria',medio:'galicia',idMovimiento:3240},origenTipo:'Galicia',idOrigen:3240}]});
  if(path.startsWith('/api/revision-cuentas'))return json({detail:'sin datos en esta prueba'},404);
  return json({items:[],total:0});
 });
 await page.goto('http://127.0.0.1:3100/finanzas/auditoria-cuentas/cuenta/7');
 await page.getByRole('heading',{name:'Agroneyer S.A.'}).waitFor();
 await page.getByText('Pendiente de revisar').waitFor();
 await page.getByText('Hay pagos aplicados a facturas de hace mucho tiempo').first().waitFor();
 // movimientos con saldo acumulado y enlace al comprobante
 const filas=await page.locator('tbody tr').allInnerTexts();
 assert.ok(filas.some(f=>/0001-1/.test(f)&&/1\.500/.test(f)&&/TC/.test(f)));
 assert.ok(filas.some(f=>/Pago/.test(f)&&/500/.test(f)&&!/TC/.test(f)));
 await page.getByText(/En dólares/).first().waitFor();
 await page.getByText(/cada documento gobierna en su moneda/).waitFor();
 const pdf=await page.getByRole('link',{name:'Abrir PDF'}).first().getAttribute('href');
 assert.match(pdf,/a\.pdf/);
 // pasar a la siguiente
 assert.equal(await page.getByRole('link',{name:/Siguiente: Agropark/}).getAttribute('href'),'/finanzas/auditoria-cuentas/cuenta/8');
 // saldo esperado
 await page.getByLabel(/Saldo esperado/).selectOption('cero');
 await page.waitForTimeout(300);
 assert.ok(guardados.some(g=>g.saldoEsperado==='cero'));
 // anular imputaciones
 await page.getByRole('button',{name:'Anular estas imputaciones'}).click();
 await page.getByLabel('Motivo').fill('No corresponde');
 await page.getByRole('button',{name:'Anular',exact:true}).click();
 await page.waitForTimeout(400);
 assert.deepEqual(anulaciones[0],{idsAplicacion:[11,12],motivo:'No corresponde'});
 // marcar revisada
 await page.getByLabel('Nota de la revisión').fill('ok');
 await page.getByRole('button',{name:'Marcar como revisada'}).click();
 await page.waitForTimeout(400);
 assert.ok(guardados.some(g=>g.estado==='revisada'&&g.nota==='ok'));
 await page.getByText('Revisada',{exact:false}).first().waitFor();
 assert.deepEqual(errors,[]);
 console.log('OK: revisión de una cuenta con saldo acumulado, comprobante, siguiente, saldo esperado, anular imputaciones y marcar revisada.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});

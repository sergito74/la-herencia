const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let pagos=[],writes=0;
 const cargos=Object.fromEntries(['impuestoSellos','gastosAdmin','mantCuenta','renovAnual','promocionBNA','creditoContingente','intFinanc','intCompens','iva105','percepIVA105','iva21','percepIVA21','percepIIBB','ajusteResAnterior'].map(k=>[k,0]));
 const detalle=()=>({...cargos,idResumen:7,idTarjeta:1,tarjeta:'Agronación',codigo:'PRUEBA',fechaCierre:'2026-09-20',fechaVencimiento:'2026-10-01',totalCalculado:100,creditoAplicado:0,saldoPendiente:0,creditoDisponible:0,compensaciones:[],warnings:[],pagos,lineas:[{idLineaConsumo:8,fechaCompra:'2026-09-01',detalle:'Consumo prueba',importe:100,idContacto:20,comprasVinculadas:[]}]});
 await page.route('**/api/**',async route=>{
  const req=route.request(),u=new URL(req.url()),path=u.pathname;
  const headers={'access-control-allow-origin':'http://127.0.0.1:3100','access-control-allow-credentials':'true','access-control-allow-headers':'content-type,x-lock-token','access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS'};
  const json=x=>route.fulfill({status:200,headers,contentType:'application/json',body:JSON.stringify(x)});
  if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
  if(path==='/api/auth/me')return json({idUsuario:1,usuario:'fixture',nombre:'Fixture',rol:'Administrador'});
  if(path==='/api/tarjetas')return json([{idTarjeta:1,nombre:'Agronación',banco:'BNA',activa:true}]);
  if(path==='/api/contactos/20')return json({idContacto:20,razonSocial:'Proveedor inicial'});
  if(path==='/api/contactos')return json({items:[{idContacto:21,razonSocial:'Proveedor elegido'}],total:1});
  if(path.endsWith('/lock'))return json({idResumen:7,lockToken:'fixture'});
  if(path.endsWith('/pagos-candidatos'))return json([1,2].filter(id=>!pagos.some(p=>p.idMovimientoOrigen===id)).map(id=>({origen:'BNA',idMovimiento:id,fecha:'2026-10-01',importe:50,concepto:'Pago '+id})));
  if(path==='/api/tarjetas-resumenes/7/pagos') {const body=req.postDataJSON();pagos.push({...body,idPago:pagos.length+1});return json(pagos.at(-1));}
  if(path==='/api/tarjetas-resumenes/7') {if(req.method()==='PUT'){writes++;assert.equal(req.postDataJSON().lineas[0].idLineaConsumo,8);}return json(detalle());}
  if(path==='/api/tarjetas-resumenes')return json({items:[{...detalle(),lineasTotal:1,lineasVinculadas:0,pagoConciliado:true}],page:2,pageSize:50,total:51});
  if(path.endsWith('/movimientos'))return json({idTarjeta:1,tarjeta:'Agronación',movimientos:[{idResumen:7,fecha:'2026-09-01',codigo:'Z',origen:'Resumen',deuda:100,credito:0,saldoAcumulado:100},{idResumen:9,fecha:'2026-09-02',codigo:'A',origen:'Resumen',deuda:20,credito:0,saldoAcumulado:120}]});
  return json({items:[],total:0});
 });
 const listado='http://127.0.0.1:3100/finanzas/tarjetas/resumenes?idTarjeta=1&fechaCierreDesde=2026-01-01&page=2';
 await page.goto(listado);
 await page.getByRole('link',{name:'Editar',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('input[role="combobox"]')?.value==='Proveedor inicial');
 await page.locator('input[role="combobox"]').fill('Proveedor');
 await page.getByRole('button',{name:'Proveedor elegido'}).click();
 assert.equal(await page.locator('input[role="combobox"]').inputValue(),'Proveedor elegido');
 await page.getByRole('button',{name:'Guardar',exact:true}).click();
 await page.waitForURL(listado);assert.equal(writes,1);
 await page.getByRole('link',{name:'Editar',exact:true}).click();
 await page.getByRole('button',{name:'Cancelar',exact:true}).click();await page.waitForURL(listado);
 await page.getByRole('link',{name:'2026-09-20',exact:true}).click();
 await page.getByRole('button',{name:'Vincular como pago de este resumen'}).first().click();
 await page.waitForTimeout(600);
 await page.getByRole('button',{name:'Vincular como pago de este resumen'}).first().click();
 await page.waitForTimeout(600);assert.equal(pagos.length,2);
 await page.getByRole('link',{name:'Editar',exact:true}).click();
 await page.getByRole('button',{name:'Volver a Resúmenes'}).click();await page.waitForURL(listado);
 assert.deepEqual(errors,[]);
 console.log('OK: contacto, ID estable, guardar/cancelar/volver con filtros y página, dos pagos con saldo cubierto.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});

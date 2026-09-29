// Run against an existing local Next dev server. All API requests are fixtures.
// node tests/conciliacion-documentos.e2e.cjs (Playwright already installed locally)
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless:true});
  const results=[];
  try {
    for (const medio of ['bna','galicia','mercado-libre','efectivo','valores-propios','valores-recibidos']) {
      const context=await browser.newContext({viewport:{width:1440,height:1100}});
      const page=await context.newPage();
      let estado='sin_conciliar', restante=110, auditoria=null, rows=[], mode='ok', role='Administrador';
      const docs=[{origen:'Compras',idOrigen:1,importeOriginal:100,saldoPendiente:100},
        {origen:'Compras',idOrigen:2,importeOriginal:-20,saldoPendiente:-20},
        {origen:'Impuestos',idOrigen:1,importeOriginal:30,saldoPendiente:30}].map(d=>({
          ...d,fecha:'2026-09-29',tipoDocumento:'Documento fixture',numeroDocumento:String(d.idOrigen),
          moneda:'Pesos',tipoDeCambio:null,importePesos:d.importeOriginal,contraparte:'Proveedor fixture',vinculosPrevios:0}));
      function calculation(refs) {
        const chosen=refs.map(ref=>docs.find(d=>d.origen===ref.origen && d.idOrigen===ref.idOrigen));
        const total=chosen.reduce((n,d)=>n+d.saldoPendiente,0), diferencia=restante-total;
        return {estado:Math.abs(diferencia)<.1?'exacta':'parcial',diferencia,pagoParcial:diferencia<0,
          permiteParcial:diferencia>0,tcImplicito:null,tcReferencia:null,desvioTc:null,
          imputados:chosen.map(d=>({origen:d.origen,idOrigen:d.idOrigen,importeImputado:diferencia<0?restante*d.saldoPendiente/total:d.saldoPendiente}))};
      }
      await page.route('**/api/**',async route=>{
        const req=route.request(),url=new URL(req.url()),path=url.pathname;
        const headers={'access-control-allow-origin':'http://127.0.0.1:3100','access-control-allow-credentials':'true','access-control-allow-headers':'content-type'};
        const json=body=>route.fulfill({status:200,headers,contentType:'application/json',body:JSON.stringify(body)});
        if(req.method()==='OPTIONS') return route.fulfill({status:204,headers});
        if(path==='/api/auth/me') return json({idUsuario:1,usuario:'fixture',nombre:'Fixture',rol:role});
        if(path.endsWith('/documentos-buscar')) {
          if(mode==='error') return route.fulfill({status:409,headers,contentType:'application/json',body:JSON.stringify({detail:'Error de búsqueda fixture'})});
          return json(mode==='empty'?[]:docs);
        }
        if(path.endsWith('/candidatos')) return json({documentos:docs,sugerencias:[]});
        if(path.endsWith('/referencia')) return json({estado:'sin_coincidencia',candidatas:[]});
        if(path.endsWith('/conciliacion-preview')) return json(calculation(url.searchParams.getAll('documentos').map(x=>{const [origen,id]=x.split(':');return {origen,idOrigen:Number(id)};})));
        if(path.endsWith('/conciliacion-lote')) {
          const body=req.postDataJSON(), calc=calculation(body.documentos);
          rows.push(...calc.imputados.map((i,n)=>({...i,idConciliacion:rows.length+n+1,importe:i.importeImputado,idContacto:1,usuario:'fixture',fecha:'2026-09-29'})));
          restante-=calc.imputados.reduce((n,i)=>n+i.importeImputado,0);
          estado=restante>.1?'parcialmente_conciliado':'conciliado';
          if(body.aceptarDiferencia) {estado='conciliado';auditoria={...body.aceptarDiferencia,idEstado:1,estado:'DiferenciaAceptada',importeDiferencia:calc.diferencia,usuario:'fixture',fecha:'2026-09-29'};}
          return json(rows);
        }
        if(path.endsWith('/sin-documento')) {
          estado='sin_documento';auditoria={...req.postDataJSON(),idEstado:1,estado:'SinDocumento',importeDiferencia:null,usuario:'fixture',fecha:'2026-09-29'};
          return route.fulfill({status:204,headers});
        }
        if(path.endsWith('/estado') && req.method()==='DELETE') {auditoria=null;estado=restante<=.1?'conciliado':rows.length?'parcialmente_conciliado':'sin_conciliar';return route.fulfill({status:204,headers});}
        if(path.endsWith('/conciliacion')) return json({estado,importeTotal:110,saldoPendiente:auditoria?0:restante,conciliaciones:rows,auditoria,idContactoReconocido:null,contactoReconocido:null});
        if(path.endsWith('/movimientos')) return json({items:[{idMovimiento:1,idMovimientoBNA:1,idPagoEfectivo:1,idValor:1,fecha:'2026-09-29',importe:110,estadoConciliacion:estado}],total:1,page:1,pageSize:50});
        return json({items:[],total:0});
      });
      const url=`http://127.0.0.1:3100/finanzas/tesoreria?medio=${medio}`;
      await page.goto(url);
      await page.getByRole('button',{name:'Conciliar',exact:true}).click();
      await page.getByText('Saldo del movimiento:').waitFor();
      await page.getByRole('button',{name:'Carga manual',exact:true}).click();
      await page.getByPlaceholder('Buscar contacto…').waitFor();
      await page.getByRole('button',{name:'Documentos',exact:true}).click();
      await page.getByText('Proveedor fixture',{exact:true}).first().waitFor();
      assert.equal(await page.getByRole('checkbox').count(),4);
      results.push(`${medio}: buscador, tres documentos, vía manual`);
      if(medio==='galicia') {
        await page.setViewportSize({width:390,height:844});
        const box=await page.getByRole('dialog',{name:'Conciliar movimiento'}).boundingBox();
        assert.ok(box.x>=0 && box.x+box.width<=390 && box.height<=844);
        await page.screenshot({path:'C:/Temp/lh026-mobile.png',fullPage:true});
        await page.keyboard.press('Escape');
        await page.getByRole('button',{name:'Conciliar',exact:true}).waitFor();
        results.push('Galicia: diálogo dentro de viewport 390×844 y cierre con Escape');
      }
      if(medio==='mercado-libre') {
        mode='empty'; await page.getByPlaceholder('Escribí al menos 2 caracteres').fill('vacio');
        await page.getByText(/No hay coincidencias/).waitFor();
        mode='error'; await page.getByPlaceholder('Escribí al menos 2 caracteres').fill('error');
        await page.getByText('Error de búsqueda fixture',{exact:true}).waitFor();
        mode='ok'; await page.getByPlaceholder('Escribí al menos 2 caracteres').fill('proveedor');
        await page.getByText('Proveedor fixture',{exact:true}).first().waitFor();
        await page.getByRole('checkbox').nth(0).check();
        await page.getByRole('checkbox').nth(1).check();
        await page.getByText('Queda saldo pendiente del movimiento',{exact:true}).waitFor();
        assert.equal(await page.getByRole('dialog',{name:'Conciliar movimiento'}).isVisible(),true);
        await page.screenshot({path:'C:/Temp/lh026-conciliacion.png',fullPage:true});
        await page.getByRole('button',{name:'Confirmar conciliación',exact:true}).click();
        await page.getByText('Parcialmente conciliado',{exact:true}).waitFor();
        assert.equal(restante,30);
        // Finish with an explicit documented difference, then undo only the exception.
        await page.getByRole('checkbox').nth(0).check();
        await page.getByText('Pago parcial de los documentos: reparto proporcional',{exact:true}).waitFor();
        await page.getByLabel('Aceptar diferencia y cerrar el movimiento').check();
        await page.getByLabel('Motivo',{exact:false}).selectOption('Otro');
        assert.equal(await page.getByRole('button',{name:'Confirmar conciliación',exact:true}).isDisabled(),true);
        await page.getByLabel(/Detalle/).fill('Ajuste fixture');
        await page.getByRole('button',{name:'Confirmar conciliación',exact:true}).click();
        await page.getByText(/Diferencia aceptada: Otro Ajuste fixture/).waitFor();
        assert.equal(rows.length,3);
        await page.getByRole('button',{name:'Quitar estado (conservar pagos)'}).click();
        await page.getByText('Conciliado',{exact:true}).waitFor();
        assert.equal(rows.length,3);
        results.push('ML: vacío, error, NC, parcial, continuación, Otro obligatorio, diferencia y revocación');
        // Fresh movement fixture for the no-document flow and read-only role.
        rows=[];estado='sin_conciliar';restante=110;auditoria=null;
        await page.reload();
        await page.getByRole('button',{name:'Conciliar',exact:true}).click();
        await page.getByLabel('Este movimiento no tiene documento').check();
        await page.getByRole('button',{name:'Confirmar sin documento'}).click();
        await page.getByText(/Sin documento: Impuesto/).waitFor();
        assert.equal(await page.getByRole('button',{name:'Vincular traspaso',exact:true}).count(),0);
        await page.getByRole('button',{name:'Quitar estado (conservar pagos)'}).click();
        await page.getByLabel('Este movimiento no tiene documento').waitFor();
        role='Lectura';await page.reload();
        await page.getByRole('heading',{name:'Tesorería'}).waitFor();
        await page.waitForTimeout(300);
        assert.equal(await page.getByRole('button',{name:'Conciliar',exact:true}).count(),0);
        results.push('ML: sin documento, revocación, exclusión traspaso y rol Lectura');
      }
      await context.close();
    }
    console.log(JSON.stringify({passed:results},null,2));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

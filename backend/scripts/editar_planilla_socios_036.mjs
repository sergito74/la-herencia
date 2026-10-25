import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
// Dependencias del runtime compartido; no usa ni instala paquetes del repo.
const runtime=join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node');
const require=createRequire(join(runtime,'package.json'));
const {FileBlob,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const dir = resolve('backups/socios-inml-5050-20261025-036');
const originalWarn=console.warn;
let avisosVinculos=0;
console.warn=(...args)=>{
  if(args.some(x=>String(x).includes('missing a required sheetId')))avisosVinculos++;
  else originalWarn(...args);
};
const info=JSON.parse(await fs.readFile(`${dir}/respaldo-excel.json`,'utf8'));
const source=process.argv[2]==='verify'?`${dir}/Cajas Giamigli-actualizado-5050.xlsx`:info.original;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const mode=process.argv[2]??'preview';
if(mode==='verify'){
  for(const [name,range]of [['Cuenta Sergio','A431:N435'],['Cuenta Lucy','A510:N514'],['Cuenta Cond LSC','A44:N48'],['Cuenta Ceci','O1:U5']]){
    const p=await wb.render({sheetName:name,range,scale:1,format:'png'});
    await fs.writeFile(`${dir}/final-${name.replaceAll(' ','-')}.png`,new Uint8Array(await p.arrayBuffer()));
  }
  console.log('Vistas finales guardadas; vínculos originales preservados');
}else if(mode==='preview'){
  const p=await wb.render({sheetName:'Cuenta Cond LSC',range:'A1:N8',scale:1,format:'png'});
  await fs.writeFile(`${dir}/antes.png`,new Uint8Array(await p.arrayBuffer()));
  console.log('Vista previa guardada');
}else{
  const data=JSON.parse(await fs.readFile(`${dir}/cambios-excel.json`,'utf8'));
  for(const p of data){
    const s=wb.worksheets.getItem(p.hoja);
    const writeBlocks=(cells,kind)=>{
      const cols=new Map();
      for(const [address,value] of Object.entries(cells)){
        const [,col,row]=address.match(/^([A-Z]+)(\d+)$/);
        if(!cols.has(col))cols.set(col,[]);
        cols.get(col).push([Number(row),value]);
      }
      for(const [col,items]of cols){
        items.sort((a,b)=>a[0]-b[0]);
        let start=0;
        while(start<items.length){
          let end=start;
          while(end+1<items.length&&items[end+1][0]===items[end][0]+1)end++;
          s.getRange(`${col}${items[start][0]}:${col}${items[end][0]}`)[kind]=items.slice(start,end+1).map(x=>[x[1]]);
          start=end+1;
        }
      }
    };
    writeBlocks(p.valores,'values');
    writeBlocks(p.formulas,'formulas');
    const primeraAgregada=p.ultimaFila-p.agregados+1;
    if(p.agregados){
      s.getRange(`C${primeraAgregada}:C${p.ultimaFila}`).format.wrapText=true;
      s.getRange(`A${primeraAgregada}:W${p.ultimaFila}`).format.rowHeight=48;
    }
  }
  wb.recalculate();
  for(const name of ['Cuenta Sergio','Cuenta Lucy','Cuenta Cond LSC','Cuenta Ceci']){
    const p=await wb.render({sheetName:name,range:'A1:N8',scale:1,format:'png'});
    await fs.writeFile(`${dir}/despues-${name.replaceAll(' ','-')}.png`,new Uint8Array(await p.arrayBuffer()));
  }
  const output=await SpreadsheetFile.exportXlsx(wb);
  await output.save(`${dir}/editado-artifact.xlsx`);
  console.log('Editado y recalculado con Artifact Tool. Avisos de vínculos externos del original: '+avisosVinculos);
}

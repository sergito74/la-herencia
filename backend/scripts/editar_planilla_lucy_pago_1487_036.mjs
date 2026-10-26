import fs from 'node:fs/promises';
import {resolve} from 'node:path';
import {FileBlob,SpreadsheetFile} from '../../backups/cierre-cuentas-20261026/lucy-planilla-1487/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const dir=resolve('backups/cierre-cuentas-20261026/lucy-planilla-1487');
const info=JSON.parse(await fs.readFile(`${dir}/respaldo-excel.json`,'utf8'));
const mode=process.argv[2]??'preview';
const source=mode==='verify'?`${dir}/Cajas Giamigli-actualizado-5050.xlsx`:info.backup;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const changes=JSON.parse(await fs.readFile(`${dir}/cambios-excel.json`,'utf8'))[0];
const sheet=wb.worksheets.getItem('Cuenta Lucy');
const n=changes.ultimaFila;
if(mode==='edit'){
  sheet.getRange(`A${n}:W${n}`).copyFrom(sheet.getRange(`A${n-1}:W${n-1}`),'all');
  for(const [cell,value] of Object.entries(changes.valores))sheet.getRange(cell).values=[[value]];
  for(const [cell,value] of Object.entries(changes.formulas))sheet.getRange(cell).formulas=[[value]];
  sheet.getRange(`C${n}`).format.wrapText=true;
  sheet.getRange(`A${n}:W${n}`).format.rowHeight=48;
  wb.recalculate();
  const output=await SpreadsheetFile.exportXlsx(wb);
  await output.save(`${dir}/editado-artifact.xlsx`);
}
const preview=await wb.render({sheetName:'Cuenta Lucy',range:`A${n-2}:N${n}`,scale:1,format:'png'});
await fs.writeFile(`${dir}/${mode}.png`,new Uint8Array(await preview.arrayBuffer()));
console.log((await wb.inspect({kind:'region',sheetId:'Cuenta Lucy',range:`H${n}:Q${n}`,maxChars:1500,tableMaxRows:1,tableMaxCols:10})).ndjson);

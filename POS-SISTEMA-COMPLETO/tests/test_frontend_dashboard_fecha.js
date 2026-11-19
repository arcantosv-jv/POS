const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const calls = [];
const sandbox = {console, Vue: {}, PermisosUsuario: {}, window:{location:{origin:''}}, axios:{async get(url,options){calls.push({url,options});return {data:url.endsWith('/ventas-diarias')?{fecha:'2026-11-19',total_ventas:300,cantidad_transacciones:2}:url.endsWith('/productos-vendidos')?[]:{}};}}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/components.js'),'utf8')+'\nthis.dashboard=DashboardView;',sandbox);
(async()=>{
 const view={...sandbox.dashboard.data(),token:'test',$nextTick(){}};
 await sandbox.dashboard.methods.cargarDatos.call(view);
 assert.equal(calls[0].options.params,undefined);
 assert.equal(calls[1].options.params.fecha_inicio,'2026-11-19');
 assert.equal(calls[1].options.params.fecha_fin,'2026-11-19');
 assert.equal(view.ventasHoy,'300.00');
 assert.equal(calls.length,5);
 console.log('OK: dashboard usa la fecha CDMX del servidor en ambos límites.');
})().catch(e=>{console.error(e);process.exitCode=1;});

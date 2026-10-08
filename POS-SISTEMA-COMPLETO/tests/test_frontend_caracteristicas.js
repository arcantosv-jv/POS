const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let response = { modo: 'productos' }, requests = 0, event;
const sandbox = { Vue: {}, console, Intl, Date, Event: class { constructor(type) { this.type = type; } },
    window: { addEventListener() {}, removeEventListener() {}, dispatchEvent(e) { event = e.type; } },
    axios: { async get() { requests++; return { data: response }; }, async put(url, payload) { response = { modo: payload.panel_ventas }; return { data: payload }; } }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/components.js'), 'utf8') + '\nthis.views = { PanelVentas, CaracteristicasView, VentasView };', sandbox);
function instance(name) {
    const component = sandbox.views[name];
    const obj = { ...component.data(), token: 'test', activo: true };
    for (const [key, fn] of Object.entries(component.methods)) obj[key] = fn.bind(obj);
    return obj;
}
(async () => {
    const panel = instance('PanelVentas');
    await panel.actualizar(); assert.equal(panel.modo, 'productos');
    response = { modo: 'competencia', periodo: '2026-10', hay_ventas: true, sucursales: [{ nombre: 'Centro', barra: 100, lider: true }] };
    await panel.actualizar(); assert.equal(panel.modo, 'competencia');
    assert.match(sandbox.views.PanelVentas.computed.nombreMes.call(panel), /octubre/);
    response = { modo: 'oculto' }; await panel.actualizar();
    assert.equal(panel.modo, 'oculto'); assert.equal(panel.sucursales.length, 0);
    panel.activo = false; const before = requests; await panel.actualizar(); assert.equal(requests, before);
    panel.activo = true;
    sandbox.axios.get = async () => { throw new Error('offline'); };
    await panel.actualizar(); assert.equal(panel.modo, null); assert.ok(panel.error);
    // Una respuesta pendiente no debe volver a mostrar un modo obsoleto.
    let finish;
    sandbox.axios.get = () => new Promise(resolve => { finish = resolve; });
    const pending = panel.actualizar(); panel.activo = false; panel.reiniciar();
    finish({ data: { modo: 'productos' } }); await pending;
    assert.equal(panel.modo, null);
    const admin = instance('CaracteristicasView');
    admin.disponible = true; admin.modo = 'competencia';
    await admin.guardar(); assert.equal(event, 'caracteristicas-actualizadas'); assert.ok(admin.mensaje);
    const template = sandbox.views.PanelVentas.template;
    assert.match(template, /slot v-if="modo === 'productos'"/);
    assert.match(template, /v-else-if="modo === 'competencia'"/);
    assert.doesNotMatch(template, /aria-valuenow|title=|tooltip|formatoMoneda/);
    console.log('OK: modos excluyentes, actualización global, mes, fallos y respuestas obsoletas.');
})().catch(err => { console.error(err); process.exitCode = 1; });

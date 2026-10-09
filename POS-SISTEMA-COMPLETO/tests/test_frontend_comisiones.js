const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let root, enabled = false;
const calls = [];
const sandbox = { console, Intl, Date, Event: class {}, confirm: () => true,
    Vue: { createApp(config) { root = config; return { mount() {} }; } },
    window: { location: { origin: '' }, scrollTo() {}, dispatchEvent() {} },
    axios: { async get(url) { return { data: url.includes('acceso') ? { comisiones_habilitadas: enabled } : { comisiones: [] } }; },
        async post(url, data) { calls.push({ url, data }); return { data: {} }; },
        async put(url, data) { calls.push({ url, data }); return { data: {} }; },
        async delete(url) { calls.push({ url }); return { data: {} }; } }
};
vm.createContext(sandbox);
for (const file of ['components.js', 'comisiones.js', 'app.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', file), 'utf8'), sandbox);
vm.runInContext('this.comisiones = ComisionesView;', sandbox);
function instance(component) {
    const obj = { ...component.data(), token: 'test', userRole: 'employee', userId: 'employee' };
    for (const [key, fn] of Object.entries(component.methods)) obj[key] = fn.bind(obj);
    return obj;
}
(async () => {
    const app = instance(root);
    app.currentView = 'comisiones';
    await app.cargarAcceso();
    assert.equal(app.currentView, 'ventas');
    app.irAVista('comisiones'); assert.equal(app.currentView, 'ventas');
    enabled = true; await app.cargarAcceso(); app.irAVista('comisiones');
    assert.equal(app.currentView, 'comisiones');
    app.userRole = 'admin'; enabled = false; await app.cargarAcceso();
    assert.equal(app.currentView, 'comisiones');
    const view = instance(sandbox.comisiones);
    view.formulario = { dispositivo: 'Tablet', costo: '1000', metodo_pago: 'tarjeta', nombre_empleado: 'Jazmin' };
    await view.guardar();
    assert.equal(calls[0].data.nombre_empleado, 'Jazmin');
    assert.equal(calls[0].data.aprobada, undefined);
    assert.equal(calls[0].data.monto_comision, undefined);
    view.editar({ id: 'r', aprobada: true }); assert.equal(view.editandoId, null);
    const before = calls.length;
    await view.revisar({ id: 'r' }, true); assert.equal(calls.length, before);
    view.userRole = 'admin'; view.montos = { r: '150' };
    await view.revisar({ id: 'r' }, true);
    assert.equal(calls.at(-1).data.monto_comision, '150');
    assert.equal(calls.at(-1).data.aprobada, true);
    view.userRole = 'employee'; view.registros = [{ id: 'r' }];
    view.fallo({ response: { status: 403, data: { error: 'Desactivado' } } });
    assert.equal(view.registros.length, 0);
    assert.equal(view.error, 'Desactivado');
    console.log('OK: acceso por características, captura sin campos protegidos y revisión exclusiva de admin.');
})().catch(err => { console.error(err); process.exitCode = 1; });

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { console, Vue: {}, PermisosUsuario: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync('static/components.js', 'utf8') + '\nthis.component = ReclasificarProductosView; this.centro = CentroCategoriasView;', context);
const c = context.component;
function instance() {
    const o = { ...c.data(), token: 'test', $nextTick: fn => fn(), $refs: {} };
    for (const [name, fn] of Object.entries(c.methods)) o[name] = fn.bind(o);
    for (const [name, fn] of Object.entries(c.computed)) Object.defineProperty(o, name, { get: () => fn.call(o) });
    return o;
}
(async () => {
    const centro = { userRole: 'employee', $root: { puede: () => true } };
    assert.equal(context.centro.computed.tabs.call(centro).some(t => t.id === 'reclasificacion'), false);
    centro.userRole = 'admin';
    assert.equal(context.centro.computed.tabs.call(centro).some(t => t.id === 'reclasificacion'), true);
    const o = instance();
    o.revision = { id: 'r', version: 3, resumen: { sin_revisar: 20 }, filas: [] };
    let calls = 0;
    o.pedir = async () => { calls++; o.detener = true; return { ...o.revision, resumen: { sin_revisar: 10 } }; };
    await o.continuar();
    assert.equal(calls, 1); // Pausa al terminar el lote, sin perderlo.
    assert.equal(o.resumen.sin_revisar, 10);
    o.pedir = async () => { calls++; return { ...o.revision, resumen: {} }; };
    await o.continuar();
    assert.equal(calls, 2);
    o.revision.filas = [{id:'a', codigo:'A', nombre:'Ambiguo', estado:'pendiente'}, {id:'b', codigo:'B', nombre:'Corregido', estado:'listo'}];
    o.filtro = 'pendiente';
    assert.equal(o.visibles.length, 1);
    let payload;
    o.editor = { id: 'a' }; o.form.subcategoriaId = 'sub';
    o.pedir = async (ruta, body) => { payload = body; return { ...o.revision, version: 4 }; };
    await o.guardarEdicion();
    assert.equal(payload.subcategoria_id, 'sub');
    assert.equal(payload.producto_id, 'a');
    assert.equal(payload.version, 3);
    assert.equal(o.editor, null);
    c.beforeUnmount.call(o);
    assert.equal(o.viva, false);
    assert.equal(o.detener, true);
    console.log('OK: acceso admin, pausa/reanudación, edición y control de versión.');
})().catch(e => { console.error(e); process.exitCode = 1; });

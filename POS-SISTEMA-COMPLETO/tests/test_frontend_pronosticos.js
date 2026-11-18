const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const sandbox = { Intl, Date, console, axios: {}, window: { scrollTo() {} } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/pronosticos.js'), 'utf8')+'\nthis.component = PronosticosView;', sandbox);
const c = sandbox.component;
function instance() {
    const obj = { ...c.data(), token: 'test' };
    for (const [k, fn] of Object.entries(c.methods)) obj[k] = fn.bind(obj);
    for (const [k, fn] of Object.entries(c.computed)) Object.defineProperty(obj, k, { get: () => fn.call(obj) });
    return obj;
}
(async () => {
    const v = instance(); v.hoy = '2026-11-18'; v.cantidad = 7;
    assert.equal(v.rango().inicio, '2026-11-19'); assert.equal(v.rango().fin, '2026-11-25');
    v.periodo = 'meses'; v.hoy = '2028-01-30'; v.cantidad = 1;
    assert.equal(v.rango().fin, '2028-02-28'); // Exclusive same-date/clamped month end minus one day.
    v.hoy = '2026-12-31'; assert.equal(v.rango().inicio, '2027-01-01'); assert.equal(v.rango().fin, '2027-01-31');
    v.cantidad = 25; assert.throws(() => v.rango());
    v.cantidad = 1.5; assert.throws(() => v.rango());
    v.periodo = 'rango'; v.inicio = '2027-02-01'; v.fin = '2027-03-01';
    assert.equal(v.rango().fin, '2027-03-01');
    const source = { sucursal_id: 's', mes: '2026-10', categorias: [{ categoria_id: 'c', importe: '500', unidades: 2 }] };
    v.editarManual(source); v.manual.categorias[0].importe = '100';
    assert.equal(source.categorias[0].importe, '500'); assert.equal(v.confirmar, false);
    assert.equal(v.totalManual.importe, 100);
    let resolve;
    sandbox.axios.post = () => new Promise(r => { resolve = r; });
    v.actual = { id: 'old' }; const pending = v.explicar();
    v.actual = { id: 'new' }; v.solicitud++;
    resolve({ data: { explicacion: 'Old response' } }); await pending;
    assert.equal(v.actual.explicacion, undefined);
    sandbox.axios.post = async () => { throw { response: { data: { error: 'Gemini no disponible' } } }; };
    v.explicando = false; await v.explicar();
    assert.equal(v.actual.id, 'new'); assert.equal(v.errorIA, 'Gemini no disponible');
    console.log('OK: periodos CDMX, meses y año bisiesto, edición aislada y respuestas de IA obsoletas.');
})().catch(e => { console.error(e); process.exitCode = 1; });

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const calls = [];
const sandbox = { Intl, Date, axios: {
    async get(url) { if (url === '/api/productos') return { data: { productos: [{ id: 'p', nombre: 'Tablet', codigo: 'T', precio: 100, impuesto: 16 }], pages: 1 } }; return { data: { apartados: [] } }; },
    async post(url, data) { calls.push({ url, data }); return { data: { id: 'r', estado: 'pendiente', productos: data.productos } }; }
} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../static/apartados.js'), 'utf8') + '\nthis.view = ApartadosView;', sandbox);
(async () => {
    const c = sandbox.view;
    const obj = { ...c.data(), token: 'test', userRole: 'employee', $root: { userSucursal: 'otra', sucursalPrincipal: 'propia' } };
    for (const [name, fn] of Object.entries(c.methods)) obj[name] = fn.bind(obj);
    await obj.nuevo(); assert.equal(obj.form.sucursal_id, 'propia');
    obj.agregar(obj.productos[0]); obj.agregar(obj.productos[0]);
    assert.equal(obj.form.productos.length, 1); assert.equal(obj.form.productos[0].cantidad, 2);
    assert.equal(obj.form.productos[0].precio, '');
    obj.form.productos[0].precio = 75;
    assert.equal(c.computed.total.call(obj), 150);
    obj.form.anticipo = 50; obj.pago.efectivo = 20; obj.pago.tarjeta = 30;
    await obj.guardar(); assert.equal(calls[0].url, '/api/apartados');
    assert.equal(calls[0].data.pagos.length, 2); assert.equal(obj.creando, false);
    obj.preparar('abonar'); assert.equal(obj.pago.monto, 0); assert.equal(obj.pago.efectivo, 0);
    obj.userRole = 'admin'; obj.filtro = 'centro';
    await obj.nuevo(); assert.equal(obj.form.sucursal_id, 'centro');
    obj.filtro = ''; await obj.nuevo(); assert.equal(obj.form.sucursal_id, '');
    console.log('OK: sucursal propia, varios productos, precio manual, pago mixto y limpieza entre operaciones.');
})().catch(e => { console.error(e); process.exitCode = 1; });

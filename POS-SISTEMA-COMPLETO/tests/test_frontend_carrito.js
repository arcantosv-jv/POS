const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const calls = [];
const sandbox = {
    Vue: {}, console, window: { location: { origin: '' } },
    axios: { async post(url, data) {
        calls.push({ url, data: JSON.parse(JSON.stringify(data)) });
        return { data: { venta: { id: 'venta', numero_venta: 'V001' } } };
    } }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/components.js'), 'utf8') + '\nthis.view = VentasView;', sandbox);
function instance() {
    const obj = { ...sandbox.view.data(), userRole: 'empleado', token: 'test', $refs: {} };
    for (const [key, fn] of Object.entries(sandbox.view.methods)) obj[key] = fn.bind(obj);
    for (const [key, fn] of Object.entries(sandbox.view.computed)) Object.defineProperty(obj, key, { get: fn.bind(obj) });
    return obj;
}
const recarga = { id: 'recarga', nombre: 'Recarga', codigo: 'REC', precio: 0, impuesto: 0 };
function agregar(view, precio) {
    view.agregarAlCarrito(recarga);
    assert.equal(view.mostrarModalPrecioFlexible, true);
    view.precioFlexible = precio;
    view.agregarProductoFlexibleAlCarrito();
}
(async () => {
    for (const precios of [[100, 50], [50, 100]]) {
        const view = instance();
        precios.forEach(precio => agregar(view, precio));
        assert.equal(view.carrito.length, 2);
        assert.equal(view.total, 150);
        view.carrito.forEach((item, i) => {
            assert.equal(item.precio, precios[i]);
            assert.equal(item.cantidad, 1);
        });
        await view.registrarVenta();
        assert.equal(view.error, '');
        assert.deepEqual(calls.at(-1).data.detalles, precios.map(precio => ({ producto_id: 'recarga', cantidad: 1, precio })));
    }
    const view = instance();
    agregar(view, 100);
    agregar(view, 50);
    agregar(view, '50.00');
    assert.equal(view.carrito.length, 2);
    assert.equal(view.carrito[1].cantidad, 2);
    assert.equal(view.total, 200);
    await view.incrementarCantidad(0);
    assert.equal(view.total, 300);
    view.decrementarCantidad(1);
    assert.equal(view.total, 250);
    view.removerDelCarrito(0);
    assert.equal(view.total, 50);
    for (const invalid of ['', -1, NaN, Infinity]) {
        agregar(view, invalid);
        assert.ok(view.error);
        assert.equal(view.total, 50);
    }
    const fixed = instance();
    fixed.agregarAlCarrito({ ...recarga, precio: 100 });
    fixed.agregarAlCarrito({ ...recarga, precio: 100 });
    assert.equal(fixed.carrito.length, 1);
    assert.equal(fixed.total, 200);
    agregar(fixed, 50);
    fixed.agregarAlCarrito({ ...recarga, precio: 100 });
    assert.equal(fixed.carrito.length, 2);
    assert.equal(fixed.total, 350);
    console.log('OK: recargas de 100 y 50 suman 150 en ambos órdenes, conservan precios al cobrar y permiten editar cantidades por importe.');
})().catch(err => { console.error(err); process.exitCode = 1; });

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const llamadas = [];
const sandbox = { Vue: {}, console, PermisosUsuario: {}, window: { location: { origin: '' } }, axios: {
    async get(url) {
        llamadas.push(url);
        if (url.includes('sucursales-publico')) return { data: [{ id: 's1', nombre: 'Centro' }, { id: 's2', nombre: 'Norte' }] };
        if (url.includes('/api/productos')) {
            const pagina = Number(new URL(url, 'http://localhost').searchParams.get('page'));
            return { data: { pages: 2, productos: Array.from({ length: 6 }, (_, i) => ({
                id: `p${pagina}-${i}`, nombre: `Mica ${pagina}-${i}`, codigo: null
            })) } };
        }
        return { data: { stocks: [{ producto_id: 'p1', sucursal_id: url.includes('/s2?') ? 's2' : 's1' }] } };
    }
} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../static/components.js'), 'utf8') + '\nthis.component = InventarioView;', sandbox);
(async () => {
    const c = sandbox.component;
    const obj = { ...c.data(), token: 'test', userRole: 'employee', $root: { sucursalPrincipal: 's2', userSucursal: 's1', puede: () => true } };
    for (const [name, fn] of Object.entries(c.methods)) obj[name] = fn.bind(obj);
    await obj.cargarSucursales();
    assert.equal(obj.sucursalSeleccionada, 's2');
    assert.equal(obj.entrada.sucursal_id, 's2');
    obj.cancelarEdicion();
    assert.equal(obj.entrada.sucursal_id, 's2');
    await c.watch.sucursalSeleccionada.call(obj);
    await obj.cargarStock();
    assert.equal(obj.stocks[0].sucursal_id, 's2');
    obj.sucursalSeleccionada = '';
    await obj.cargarStock();
    assert.equal(obj.stocks.length, 2);
    assert.ok(!llamadas.some(url => url.includes('/stock/?')));
    await obj.cargarProductos();
    obj.busquedaProductoEntrada = 'mica';
    assert.equal(c.computed.productosEncontrados.call(obj).length, 12);
    assert.ok(c.computed.productosEncontrados.call(obj).some(p => p.id === 'p2-5'));
    obj.busquedaProductoEntrada = 'inexistente';
    assert.equal(c.computed.productosEncontrados.call(obj).length, 0);
    obj.userRole = 'admin';
    await obj.cargarSucursales();
    assert.equal(obj.entrada.sucursal_id, 's1');
    obj.entrada.sucursal_id = 's2';
    obj.cancelarEdicion();
    assert.equal(obj.entrada.sucursal_id, 's2');
    // Las plantillas HTML del navegador convierten atributos a minúsculas.
    const html = fs.readFileSync(require('node:path').join(__dirname, '../static/index.html'), 'utf8');
    const etiqueta = html.match(/<inventario-view\b[^>]*>/)[0];
    assert.ok(etiqueta.includes(':user-role="userRole"'));
    obj.$root.puede = () => false;
    const antes = llamadas.length;
    await obj.cargarStock();
    assert.equal(llamadas.length, antes);
    assert.equal(obj.stocks.length, 0);
    console.log('OK: sucursal activa, todas las autorizadas y búsqueda con código vacío.');
})().catch(e => { console.error(e); process.exitCode = 1; });

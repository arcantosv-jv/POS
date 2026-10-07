// Pruebas de lógica de los componentes sin abrir navegador ni llamar servicios.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const calls = [];
const sandbox = {
    Vue: {}, console, Intl, Date,
    window: { location: { origin: 'http://test.local' } },
    localStorage: { getItem: key => key === 'user' ? JSON.stringify({ role: 'admin', sucursal_id: 's' }) : 'test' },
    alert() {}, confirm() { return true; },
    axios: {
        async post(url, data) { calls.push({ method: 'post', url, data }); return { data: {} }; },
        async put(url, data) { calls.push({ method: 'put', url, data }); return { data: {} }; }
    }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/components.js'), 'utf8') + '\nthis.views = { CierreCajaView, ReparacionesView, CompatibilidadView, DevolucionesView };', sandbox);
function instance(name) {
    const component = sandbox.views[name];
    const object = { ...component.data(), token: 'test' };
    for (const [name, fn] of Object.entries(component.methods)) object[name] = fn.bind(object);
    return object;
}
(async () => {
    const cash = instance('CierreCajaView');
    cash.cierre = { estado: 'abierto', total_efectivo: 1000, reembolsos_efectivo: 100 };
    cash.formulario.egresos = [{ monto: 200, concepto: 'Sueldo' }, { monto: 50, concepto: 'Transporte' }];
    assert.equal(cash.totalEgresos(cash.formulario), 250);
    assert.equal(sandbox.views.CierreCajaView.computed.efectivoEsperado.call(cash), 650);
    assert.equal(cash.validarEgreso(cash.formulario), true);
    cash.formulario.egresos[0].concepto = ' ';
    assert.equal(cash.validarEgreso(cash.formulario), false);
    const repairs = instance('ReparacionesView');
    repairs.userRoleLocal = 'admin';
    repairs.cargarDatos = () => {};
    repairs.mostrarMensaje = () => {};
    await repairs.editarReparacion({ id: 'r1', nombre_cliente: 'Cliente', telefono_cliente: '5551234567', marca_id: 'm', modelo_nombre: 'Modelo', tipo_reparacion_id: 't', costo: 500, anticipo: 100, sucursal_id: 's', fecha: '2026-10-07', estado: 'diagnostico', tecnico: 'Técnico' });
    await repairs.guardarReparacion();
    assert.equal(calls.at(-1).method, 'put');
    assert.equal(calls.at(-1).url, '/api/reparaciones/r1');
    assert.equal(calls.at(-1).data.anticipo, 100);
    assert.equal(repairs.editandoReparacionId, null);
    // Cancelar una edición y abrir una nueva nunca conserva datos ni el ID.
    const previous = { id: 'anterior', nombre_cliente: 'Anterior', telefono_cliente: '5551111111', marca_id: 'marca-anterior', modelo_nombre: 'Modelo anterior', tipo_reparacion_id: 'tipo-anterior', costo: 900, anticipo: 200, sucursal_id: 's', fecha: '2026-10-01', fecha_prometida: '2026-10-10', estado: 'lista', tecnico: 'Anterior', diagnostico: 'Diagnóstico anterior', historial: [{ usuario: 'admin' }] };
    await repairs.editarReparacion(previous);
    repairs.cerrarFormularioReparacion();
    assert.equal(repairs.mostrarNuevaReparacion, false);
    assert.equal(repairs.editandoReparacionId, null);
    assert.equal(repairs.formularioReparacion.nombre_cliente, '');
    repairs.nuevaReparacion();
    for (const field of ['nombre_cliente', 'telefono_cliente', 'marca_id', 'modelo_nombre', 'tipo_reparacion_id', 'costo', 'sucursal_id', 'fecha_prometida', 'tecnico', 'diagnostico']) {
        assert.equal(repairs.formularioReparacion[field], '', field);
    }
    assert.equal(repairs.historialReparacion.length, 0);
    assert.equal(repairs.formularioReparacion.anticipo, 0);
    assert.equal(repairs.formularioReparacion.estado, 'registrada');
    Object.assign(repairs.formularioReparacion, { nombre_cliente: 'Nueva', telefono_cliente: '5552222222', marca_id: 'm', modelo_nombre: 'Modelo', tipo_reparacion_id: 't', costo: 100, sucursal_id: 's' });
    await repairs.guardarReparacion();
    assert.equal(calls.at(-1).method, 'post');
    assert.equal(calls.at(-1).url, '/api/reparaciones');
    assert.equal(previous.nombre_cliente, 'Anterior');
    const compatibility = instance('CompatibilidadView');
    compatibility.resultados.modelo_solicitado = 'Modelo X';
    compatibility.iniciarVerificacion({ modelo: 'Mica X', marca: 'Marca' });
    assert.equal(compatibility.verificacion.modelo_celular, 'Modelo X');
    assert.equal(compatibility.verificacion.confirmada, false);
    const returns = instance('DevolucionesView');
    returns.obtenerVentasDelDia = () => {};
    returns.mostrarModalDevolucion({ id: 's1', pagos_disponibles: { efectivo: 200, tarjeta: 100 } }, { id: 'd1', precio_unitario: 100 });
    returns.reembolsos = { efectivo: 60, tarjeta: 40, transferencia: 0 };
    returns.registrarDevolucion();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.at(-1).data.reembolsos.efectivo, 60);
    assert.equal(calls.at(-1).data.reembolsos.tarjeta, 40);
    console.log('OK: cálculo y validación de egresos; edición PUT de reparaciones; confirmación de compatibilidad; envío de reembolso mixto.');
})().catch(error => { console.error(error); process.exitCode = 1; });

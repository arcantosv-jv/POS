const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const calls = [];
const sandbox = { Vue: {}, console, Intl, Date, alert() {}, window: { location: { origin: '' } },
    axios: { async post(url, data) { calls.push({ url, data }); return { data: { cierre: { id: 'nuevo', estado: url.endsWith('/nuevo') ? 'abierto' : 'cerrado' } } }; } }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/components.js'), 'utf8') + '\nthis.views = { CierreCajaView, CierresCajaAdminView };', sandbox);
function instance(name) {
    const component = sandbox.views[name];
    const obj = { ...component.data(), token: 'test' };
    for (const [key, fn] of Object.entries(component.methods)) obj[key] = fn.bind(obj);
    for (const [key, fn] of Object.entries(component.computed || {})) Object.defineProperty(obj, key, { get: fn.bind(obj) });
    return obj;
}
(async () => {
    const cash = instance('CierreCajaView');
    cash.cierre = { id: 'anterior', estado: 'cerrado' };
    cash.formulario = { efectivo_reportado: 500, egresos: [{ monto: 50, concepto: 'Antes' }], observaciones: 'Antes' };
    await cash.iniciarOtroCierre();
    assert.equal(cash.cierre.id, 'nuevo');
    assert.equal(cash.formulario.efectivo_reportado, null);
    assert.equal(cash.formulario.egresos.length, 0);
    assert.equal(cash.formulario.observaciones, '');
    cash.formulario.efectivo_reportado = 100;
    cash.guardarCierre(); cash.guardarCierre();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.length, 2); // Un inicio y una confirmación, sin duplicados.
    assert.equal(calls[1].data.cierre_id, 'nuevo');
    assert.equal(cash.guardandoCierre, false);
    cash.cierre = { estado: 'abierto', efectivo_inicial: 800, total_efectivo: 300, reembolsos_efectivo: 50 };
    cash.formulario.egresos = [{ monto: 25, concepto: 'Transporte' }];
    assert.equal(cash.efectivoTurno, 225);
    assert.equal(cash.efectivoEsperado, 1025);
    cash.editandoCierre = true;
    cash.formularioEdicion.egresos = [{ monto: 75, concepto: 'Corrección' }];
    assert.equal(cash.efectivoEsperado, 975);
    assert.match(cash.formatoHora('2026-10-10T05:30:00+00:00'), /11:30|23:30/);
    cash.cierre = { total_ventas: 400.20, cierres_anteriores: [{ total_ventas: 100.10 }, { total_ventas: 200.30 }] };
    assert.equal(cash.totalVentasDia, 700.60);
    cash.cierre = { total_ventas: 50 };
    assert.equal(cash.totalVentasDia, 50);
    const active = cash.cierre;
    const previous = { id: 'previous', puede_corregir: true, efectivo_reportado: 100, egresos: [] };
    cash.abrirEdicionCierre(previous);
    assert.equal(cash.cierre.id, 'previous');
    assert.equal(cash.formularioEdicion.efectivo_reportado, 100);
    cash.cancelarEdicion();
    assert.equal(cash.cierre, active);
    cash.abrirEdicionCierre({ puede_corregir: false });
    assert.equal(cash.editandoCierre, false);
    const admin = instance('CierresCajaAdminView');
    admin.cierres = [
        { id: 'a', fecha: '2026-10-09', total_vendido: 100.10 },
        { id: 'b', fecha: '2026-10-08', total_vendido: 40 },
        { id: 'c', fecha: '2026-10-09', total_vendido: 200.20 }
    ];
    const groups = sandbox.views.CierresCajaAdminView.computed.cierresPorDia.call(admin);
    assert.equal(groups.length, 2);
    assert.equal(groups[0].fecha, '2026-10-09');
    assert.equal(groups[0].total, 300.30);
    assert.equal(groups[0].cierres.length, 2);
    assert.match(admin.formatoFechaGrupo(groups[0].fecha), /Viernes.*09.*octubre.*2026/);
    admin.alternarDetalle('c'); assert.equal(admin.cierreExpandidoId, 'c');
    admin.alternarDetalle('c'); assert.equal(admin.cierreExpandidoId, null);
    console.log('OK: nuevo cierre limpio, confirmación por ID, prevención de doble envío y agrupación por fecha con detalle individual.');
})().catch(err => { console.error(err); process.exitCode = 1; });

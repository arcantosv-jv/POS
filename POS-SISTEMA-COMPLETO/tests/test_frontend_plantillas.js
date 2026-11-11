// Uso: node tests/test_frontend_plantillas.js /ruta/vue.global.prod.js
// Usa el mismo compilador Vue del CDN declarado en static/index.html.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const runtime = process.argv[2] || process.env.VUE_RUNTIME_PATH;
if (!runtime) { console.error('Indica la ruta de vue.global.prod.js como argumento o VUE_RUNTIME_PATH.'); process.exit(1); }
const root = path.join(__dirname, '..');
const context = { console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(runtime, 'utf8'), context);
context.document = { createElement() { return { set innerHTML(v) {
    const decode = s => s.replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
    this.children = [{ getAttribute: () => decode(v.slice(10, -2)) }]; this.textContent = decode(v);
} }; } };
const names = [];
for (const file of ['permisos.js', 'components.js', 'comisiones.js', 'apartados.js']) {
    const source = fs.readFileSync(path.join(root, 'static', file), 'utf8');
    names.push(...[...source.matchAll(/^const (\w+) = \{/gm)].map(m => m[1]));
    vm.runInContext(source, context);
}
let failures = 0;
for (const name of names) {
    const component = vm.runInContext(name, context);
    if (!component.template) continue;
    try {
        assert.equal(typeof context.Vue.compile(component.template), 'function');
        console.log('OK:', name);
    } catch (e) { failures++; console.error('ERROR:', name, e.message); }
}
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
assert.equal(/:[a-z]+[A-Z][a-zA-Z]*=/.test(html), false, 'Los bindings del HTML deben usar kebab-case para conservar rol y sucursal');
const template = html.slice(html.indexOf('<div id="app">'), html.indexOf('<!-- Scripts de componentes -->'));
try { context.Vue.compile(template); console.log('OK: navegación principal'); }
catch (e) { failures++; console.error('ERROR: navegación principal', e.message); }
if (failures) process.exitCode = 1;

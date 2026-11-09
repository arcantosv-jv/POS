const PermisosUsuario = {
    props: ['usuario', 'token', 'sucursales'],
    emits: ['cerrar', 'guardado'],
    template: `
        <section class="card access-editor">
            <div class="card-header"><h3>Accesos de {{ usuario.username }}</h3><button class="btn btn-secondary" @click="$emit('cerrar')">Cerrar</button></div>
            <p>Elige los apartados, acciones y sucursales. Los usuarios, sucursales y características del sistema se administran exclusivamente desde una cuenta admin.</p>
            <p v-if="usuario.role === 'admin'" class="alert alert-info">Este administrador conserva acceso universal.</p>
            <p v-if="error" class="alert alert-danger">{{ error }}</p>
            <p v-if="cargando">Cargando accesos…</p>
            <fieldset :disabled="cargando || guardando || usuario.role === 'admin'" style="border: 0; padding: 0;">
                <h4>Sucursales permitidas</h4>
                <div class="access-options"><label v-for="sucursal in sucursales" :key="sucursal.id"><input type="checkbox" v-model="sucursalesElegidas" :value="sucursal.id" :disabled="sucursal.id === usuario.sucursal_id"> {{ sucursal.nombre }} <span v-if="sucursal.id === usuario.sucursal_id">(principal)</span></label></div>
                <article v-for="apartado in catalogo" :key="apartado.id" class="access-section">
                    <h4>{{ apartado.nombre }}</h4>
                    <div class="access-options"><label v-for="accion in apartado.acciones" :key="accion"><input type="checkbox" :checked="(permisos[apartado.id] || []).includes(accion)" @change="cambiar(apartado.id, accion, $event.target.checked)"> {{ apartado.id === 'inventario' && accion === 'ver' ? 'Acceder a inventario' : (etiquetas[accion] || accion) }}</label></div>
                </article>
                <p class="cash-register-help">Comisiones también requiere que esté habilitado en Características. Registrar entradas no permite consultar existencias. Habilita Consultar stock actual para mostrar la tabla; también es necesario para ajustar, eliminar o exportar inventario. Los catálogos de productos, categorías y reparaciones son compartidos por todas las sucursales.</p>
                <button class="btn btn-primary" @click="guardar">{{ guardando ? 'Guardando…' : 'Guardar accesos' }}</button>
            </fieldset>
        </section>
    `,
    data() { return { catalogo: [], permisos: {}, sucursalesElegidas: [], cargando: true, guardando: false, error: '', etiquetas: { abonar: 'Registrar abonos', ver_stock: 'Consultar stock actual', ver: 'Ver', crear: 'Crear', editar: 'Editar', eliminar: 'Eliminar', entradas: 'Registrar entradas', ajustar: 'Ajustar stock y mínimo', exportar: 'Exportar', importar: 'Importar', cerrar: 'Realizar cierre', corregir: 'Corregir cierre (1 hora)', editar_pagos: 'Modificar pagos', analizar: 'Análisis con IA', buscar: 'Consultar compatibilidad', verificar: 'Verificar compatibilidad', entregar: 'Marcar entregada', catalogo: 'Administrar catálogo', consultar: 'Consultar' } }; },
    methods: {
        async cargar() {
            this.cargando = true; this.error = '';
            try {
                const res = await axios.get('/api/permisos/usuarios/' + this.usuario.id, { headers: { Authorization: `Bearer ${this.token}` } });
                this.catalogo = res.data.catalogo; this.permisos = res.data.permisos; this.sucursalesElegidas = res.data.sucursales_permitidas;
            } catch (err) { this.error = err.response?.data?.error || 'No se pudieron cargar los accesos'; }
            finally { this.cargando = false; }
        },
        cambiar(module, action, enabled) {
            let actions = [...(this.permisos[module] || [])];
            if (enabled) { actions.push(action); if (action !== 'ver' && module !== 'ayuda') actions.push('ver'); }
            else actions = action === 'ver' ? [] : actions.filter(a => a !== action);
            this.permisos = { ...this.permisos, [module]: [...new Set(actions)] };
        },
        async guardar() {
            if (this.guardando || this.cargando) return;
            this.guardando = true; this.error = '';
            try {
                await axios.put('/api/permisos/usuarios/' + this.usuario.id, { permisos: this.permisos, sucursales_permitidas: this.sucursalesElegidas }, { headers: { Authorization: `Bearer ${this.token}` } });
                this.$emit('guardado');
                window.dispatchEvent(new Event('caracteristicas-actualizadas'));
            } catch (err) { this.error = err.response?.data?.error || 'No se pudieron guardar los accesos'; }
            finally { this.guardando = false; }
        }
    },
    mounted() { this.cargar(); }
};

const ComisionesSemanales = {
    props:['token','userRole','sucursales','modo'],emits:['catalogo'],
    data(){return {datos:null,cargando:false,error:'',mensaje:'',form:null,filtro:{sucursal_id:'',desde:'',hasta:''},aplicados:{},pagina:1,dias:['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']};},
    methods:{
        config(){return {headers:{Authorization:'Bearer '+this.token}};},
        moneda(v){return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(v||0);},
        async cargar(){this.cargando=true;this.error='';try{this.datos=(await axios.get('/api/comisiones/semanales',{...this.config(),params:{...this.aplicados,pagina:this.pagina}})).data;this.pagina=this.datos.pagina;}catch(e){this.error=e.response?.data?.error||'No se pudo cargar el resumen semanal.';}finally{this.cargando=false;}},
        filtrar(){this.aplicados={...this.filtro};this.pagina=1;this.cargar();},
        async guardar(){this.cargando=true;this.error='';try{await axios[this.form.id?'put':'post']('/api/comisiones/semanales/empleados'+(this.form.id?'/'+this.form.id:''),this.form,this.config());this.form=null;this.$emit('catalogo');await this.cargar();}catch(e){this.error=e.response?.data?.error||'No se pudo guardar el empleado.';}finally{this.cargando=false;}},
        async pagar(e){if(this.cargando||!confirm('¿Confirmas que entregaste '+this.moneda(e.por_pagar)+' a '+e.nombre+' por '+e.cantidad_pago+' comisiones hasta el '+e.hasta_pagable+'?'))return;this.cargando=true;this.error='';try{await axios.post('/api/comisiones/semanales/empleados/'+e.id+'/pagar',{version:e.version},this.config());this.mensaje='Pago registrado. Las comisiones pagadas quedan protegidas.';this.$emit('catalogo');await this.cargar();}catch(err){this.error=err.response?.data?.error||'No se pudo registrar el pago.';}finally{this.cargando=false;}}
    },
    mounted(){this.cargar();},watch:{modo(){this.form=null;this.mensaje='';this.filtro={sucursal_id:'',desde:'',hasta:''};this.aplicados={};this.pagina=1;this.cargar();},'$root.userSucursal'(){this.datos=null;this.pagina=1;this.cargar();}},
    template:`<section class="card commission-history"><div class="card-header"><h2>{{ modo==='empleados'?'Empleados':modo==='historial'?'Historial de pagos':'Pagos semanales' }}</h2><div class="commission-row-actions"><button v-if="userRole==='admin' && modo==='empleados'" class="btn btn-primary" @click="form={nombre:'',sucursal_id:'',dia_pago:0,activo:true}" :disabled="cargando">Nuevo empleado</button><button class="btn btn-secondary" @click="cargar" :disabled="cargando">Actualizar</button></div></div>
    <p v-if="modo==='pagos'">Semana según el día de pago de cada empleado y fecha de venta. El corte incluye el día de pago. Solo se entregan comisiones aprobadas al registrar el pago; las demás pasan a la siguiente semana.</p>
    <p v-if="error" class="alert alert-danger">{{ error }}</p><p v-if="mensaje" class="alert alert-success">{{ mensaje }}</p>
    <div v-if="form&&userRole==='admin'" class="modal-overlay" @click.self="!cargando&&(form=null)"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="com-empleado-titulo" style="max-width:720px;width:95%;max-height:90vh;overflow-y:auto"><div class="card-header"><h3 id="com-empleado-titulo">{{ form.id?'Editar empleado':'Nuevo empleado' }}</h3><button class="modal-close" aria-label="Cerrar" :disabled="cargando" @click="form=null">✕</button></div><p v-if="error" class="alert alert-danger">{{ error }}</p><form class="commission-query" @submit.prevent="guardar"><label>Nombre<input v-model="form.nombre" maxlength="150" required></label><label>Sucursal<select v-model="form.sucursal_id" required :disabled="!!form.id"><option value="">Selecciona</option><option v-for="s in sucursales" :value="s.id" :key="s.id">{{ s.nombre }}</option></select></label><label>Día de pago<select v-model.number="form.dia_pago"><option v-for="(dia,i) in dias" :value="i">{{ dia }}</option></select></label><label>Estado<select v-model="form.activo"><option :value="true">Activo</option><option :value="false">Inactivo</option></select></label><button class="btn btn-success" :disabled="cargando">Guardar empleado</button><button type="button" class="btn btn-secondary" @click="form=null" :disabled="cargando">Cancelar</button></form></section></div>
    <form class="commission-query" @submit.prevent="filtrar"><label v-if="userRole==='admin'">Sucursal<select v-model="filtro.sucursal_id"><option value="">Todas</option><option v-for="s in sucursales" :value="s.id" :key="s.id">{{ s.nombre }}</option></select></label><label v-if="modo==='historial'||userRole!=='admin'">Pagos entregados desde<input type="date" v-model="filtro.desde"></label><label v-if="modo==='historial'||userRole!=='admin'">Hasta<input type="date" v-model="filtro.hasta"></label><button class="btn btn-primary" :disabled="cargando">Consultar</button></form>
    <template v-if="datos"><p v-if="datos.sin_asignar && modo!=='historial'" class="alert alert-warning">{{ datos.sin_asignar }} comisiones sin empleado del catálogo. Admin debe asignarlas en la tabla de comisiones para incluirlas en pagos semanales.</p>
    <div v-if="modo==='pagos'" class="commission-table-scroll"><table class="commission-table"><thead><tr><th>Empleado / sucursal</th><th>Semana / pago programado</th><th>Acumulado sin pagar de la semana</th><th>Comisiones aprobadas por pagar</th><th>Acciones</th></tr></thead><tbody><tr v-for="e in datos.empleados" :key="e.id"><td><strong>{{ e.nombre }}</strong><small>{{ e.sucursal_nombre }} · {{ e.activo?'Activo':'Inactivo' }}</small></td><td>{{ e.desde }} al {{ e.hasta }}<small>{{ dias[e.dia_pago] }} · {{ e.dia_programado }}</small></td><td>{{ moneda(e.acumulado) }}<small>{{ e.sin_monto }} sin monto · {{ e.pendientes_aprobacion }} sin aprobación en total</small></td><td><dl class="commission-payment-breakdown"><div><dt>Pendientes aprobadas de semanas anteriores:</dt><dd>{{ moneda(e.aprobado_anterior) }}</dd></div><div><dt>Aprobadas esta semana:</dt><dd>{{ moneda(e.aprobado_semana) }}</dd></div><div class="commission-payment-total"><dt>Total:</dt><dd>{{ moneda(e.total_proximo_pago) }}</dd></div></dl><details class="commission-approved-detail"><summary>Ver detalle</summary><div class="commission-table-scroll"><table class="commission-table"><thead><tr><th>Producto</th><th>Fecha</th><th>Comisión</th></tr></thead><tbody><tr v-for="c in e.detalle_aprobadas" :key="c.id"><td>{{ c.producto }}<small>{{ c.anterior?'Semana anterior':'Esta semana' }}</small></td><td>{{ c.fecha }}<small v-if="c.fecha_registro">Fecha de registro (histórico sin fecha de venta)</small></td><td>{{ moneda(c.comision) }}</td></tr><tr v-if="!e.detalle_aprobadas?.length"><td colspan="3">No hay comisiones aprobadas pendientes de pago.</td></tr></tbody><tfoot><tr><th colspan="2">Total</th><td><strong>{{ moneda(e.total_proximo_pago) }}</strong></td></tr></tfoot></table></div></details></td><td><div v-if="userRole==='admin'" class="commission-row-actions"><button class="btn btn-success" @click="pagar(e)" :disabled="cargando||!e.cantidad_pago">Registrar pago entregado</button><small v-if="e.cantidad_pago">Total a entregar: {{ moneda(e.por_pagar) }} · Corte al {{ e.hasta_pagable }}</small><small v-else>Sin comisiones disponibles para este corte; las posteriores a un pago pasan al siguiente.</small></div></td></tr></tbody></table></div>
    <div v-if="modo==='empleados' && userRole==='admin'" class="commission-table-scroll"><table class="commission-table"><thead><tr><th>Empleado</th><th>Sucursal</th><th>Día de pago</th><th>Estado</th><th>Acciones</th></tr></thead><tbody><tr v-for="e in datos.empleados" :key="e.id"><td>{{ e.nombre }}</td><td>{{ e.sucursal_nombre }}</td><td>{{ dias[e.dia_pago] }}</td><td>{{ e.activo?'Activo':'Inactivo' }}</td><td><button class="btn btn-secondary" @click="form={...e}" :disabled="cargando">Editar empleado</button></td></tr></tbody></table></div>
    <p v-if="!datos.empleados.length && modo!=='historial'" class="commission-empty">No hay empleados registrados para esta sucursal.</p>
    <template v-if="modo==='historial'||(modo==='pagos'&&userRole!=='admin')"><div class="commission-totals"><strong>Entregado en las fechas consultadas: {{ moneda(datos.total_entregado) }}</strong><span>{{ datos.total_pagos }} pagos · Fechas de CDMX</span></div>
    <h3>Historial de pagos</h3><p>Estos importes corresponden a entregas registradas, no a aprobaciones. El historial conserva su período aunque cambie el día de pago del empleado.</p><details v-for="p in datos.pagos" :key="p.id"><summary>{{ p.empleado }} · {{ moneda(p.monto) }} · {{ new Date(p.fecha_pago).toLocaleString('es-MX',{timeZone:'America/Mexico_City'}) }}</summary><p>Período: {{ p.desde }} al {{ p.hasta }} · Registrado por {{ p.usuario }}</p><p v-for="c in p.comisiones" :key="c.id">{{ c.fecha_venta }} · {{ c.producto }} · {{ moneda(c.monto) }}</p></details><nav class="commission-pagination"><button class="btn btn-secondary" :disabled="cargando||pagina<=1" @click="pagina--;cargar()">Anterior</button><span>{{ pagina }} / {{ datos.paginas }}</span><button class="btn btn-secondary" :disabled="cargando||pagina>=datos.paginas" @click="pagina++;cargar()">Siguiente</button></nav>
    </template></template></section>`
};

const ComisionesView = {
    components:{ComisionesSemanales},
    props: ['token', 'userRole', 'userId'],
    template: `
        <section class="commissions-page">
            <header class="commissions-heading"><h1>Comisiones</h1><p>{{ userRole === 'admin' ? 'Consulta y aprueba las comisiones de todas las sucursales.' : 'Registra tu comisión a partir de una venta realizada.' }}</p></header>
            <p v-if="error" class="alert alert-danger" role="alert">{{ error }}</p>
            <p v-if="mensaje" class="alert alert-success" role="status">{{ mensaje }}</p>
            <div class="commission-tabs" role="tablist" aria-label="Secciones de comisiones"><button v-for="(t,i) in tabs" :key="t.id" :id="'com-tab-'+t.id" role="tab" :aria-selected="tabActiva===t.id" :aria-controls="'com-panel-'+t.id" :tabindex="tabActiva===t.id?0:-1" :class="{active:tabActiva===t.id}" @click="seleccionTab=t.id" @keydown="moverTab($event,i)">{{ t.nombre }}</button></div>
            <section role="tabpanel" :id="'com-panel-'+tabActiva" :aria-labelledby="'com-tab-'+tabActiva">
            <comisiones-semanales v-show="['pagos','historial','empleados'].includes(tabActiva)" :modo="tabActiva" ref="semanales" :token="token" :user-role="userRole" :sucursales="sucursales" @catalogo="cargarEmpleados();cargar()" />
            <form v-show="tabActiva==='registrar'" v-if="userRole !== 'admin' && ($root.puede('comisiones', 'crear') || (editandoId && $root.puede('comisiones', 'editar')))" @submit.prevent="guardar" class="card commission-capture">
                <div class="card-header"><h2>{{ editandoId ? 'Editar registro' : 'Registrar comisión' }}</h2></div>
                <fieldset :disabled="guardando || cargando" class="commission-layout" :class="{ 'commission-editing': editandoId }">
                    <div v-if="!editandoId" class="commission-picker">
                        <h3>Selecciona una venta</h3>
                        <div class="commission-search"><div class="form-group"><label for="com-fecha">Fecha de venta</label><input id="com-fecha" type="date" v-model="fechaVenta" min="2026-11-18" @change="buscarVentas" required></div><button class="btn btn-primary" type="button" @click="buscarVentas" :disabled="buscandoVentas">{{ buscandoVentas ? 'Buscando…' : 'Buscar' }}</button></div>
                        <p v-if="errorVentas" class="alert alert-danger" role="alert">{{ errorVentas }}</p>
                        <p class="commission-caption" role="status">{{ buscandoVentas ? 'Consultando ventas…' : busquedaRealizada ? pendientes.length + ' unidades disponibles' : 'Selecciona una fecha para consultar las ventas.' }}</p>
                        <div class="commission-units" role="group" aria-label="Unidades vendidas disponibles" :aria-busy="buscandoVentas">
                            <label v-for="u in pendientes" :key="claveUnidad(u)" class="commission-unit" :class="{ selected: unidadSeleccionada === claveUnidad(u) }">
                                <input type="radio" name="com-unidad" v-model="unidadSeleccionada" :value="claveUnidad(u)" :disabled="buscandoVentas" required @change="mensaje = ''">
                                <span class="commission-device" aria-hidden="true">▯</span>
                                <span class="commission-unit-name"><strong>{{ u.producto_nombre }}</strong><small>{{ u.numero_venta }} · Unidad {{ u.unidad }}</small></span>
                                <span class="commission-unit-price"><strong>{{ moneda(u.costo) }}</strong><small>{{ pagos[u.metodo_pago] || u.metodo_pago }}</small></span>
                            </label>
                            <p v-if="busquedaRealizada && !buscandoVentas && !pendientes.length" class="commission-empty">No hay celulares o tablets pendientes para esta fecha.</p>
                        </div>
                        <p class="commission-caption commission-note">Ventas desde el 18/11/2026. Los apartados cuentan por su fecha de entrega y venta.</p>
                    </div>
                    <div class="commission-summary">
                        <h3>Datos de la comisión</h3>
                        <p class="commission-caption">{{ editandoId ? 'Puedes corregir el nombre mientras el registro no esté aprobado.' : 'Los datos de la venta se llenan automáticamente.' }}</p>
                        <dl v-if="seleccionada && !editandoId"><dt>Producto</dt><dd>{{ seleccionada.producto_nombre }}</dd><dt>Precio de venta</dt><dd>{{ moneda(seleccionada.costo) }}</dd><dt>Método de pago</dt><dd>{{ pagos[seleccionada.metodo_pago] || seleccionada.metodo_pago }}</dd></dl>
                        <p v-else-if="!editandoId" class="commission-empty">Selecciona una unidad para ver sus datos.</p>
                        <div class="commission-name form-group"><label for="com-nombre">Empleado</label><select id="com-nombre" v-model="formulario.empleado_comision_id" required><option value="">Selecciona empleado</option><option v-for="e in empleados.filter(e=>e.activo)" :value="e.id" :key="e.id">{{ e.nombre }}</option></select><p v-if="!empleados.some(e=>e.activo)" class="commission-caption">Admin debe registrar los empleados de esta sucursal.</p></div>
                        <button class="btn btn-primary commission-submit" type="submit" :disabled="!editandoId && (!seleccionada || buscandoVentas)">{{ guardando ? 'Guardando…' : editandoId ? 'Guardar cambios' : 'Registrar comisión' }}</button>
                        <button v-if="editandoId" class="btn btn-secondary" type="button" @click="limpiar">Cancelar</button>
                    </div>
                </fieldset>
            </form>
            <section v-show="tabActiva==='comisiones'" class="card commission-history">
                <div class="card-header"><h2>{{ userRole === 'admin' ? 'Comisiones registradas' : 'Comisiones de la sucursal' }}</h2><button class="btn btn-secondary" @click="actualizar" :disabled="cargando || guardando">Actualizar</button></div>
                <form class="commission-query" @submit.prevent="filtrar">
                    <label v-if="userRole === 'admin'">Sucursal<select v-model="consulta.sucursal_id"><option value="">Todas las sucursales</option><option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option></select></label>
                    <label>Fecha a consultar<select v-model="consulta.tipo_fecha"><option value="registro">Registro de comisión</option><option value="venta">Venta del producto</option></select></label>
                    <label>Desde<input type="date" v-model="consulta.desde"></label><label>Hasta<input type="date" v-model="consulta.hasta"></label>
                    <label>Empleado<input v-model="consulta.empleado" placeholder="Nombre o parte del nombre" maxlength="150"></label>
                    <label>Dispositivo<select v-model="consulta.dispositivo"><option value="">Todos</option><option>Celular</option><option>Tablet</option></select></label>
                    <div class="commission-row-actions"><button class="btn btn-primary" :disabled="cargando||guardando">Filtrar</button><button type="button" class="btn btn-secondary" @click="limpiarFiltros" :disabled="cargando||guardando">Limpiar</button></div>
                </form>
                <div v-if="!cargando" class="commission-totals"><strong>{{ total }} comisiones</strong><span>{{ resumen.aprobadas }} aprobadas · {{ resumen.pendientes }} no aprobadas</span><strong>Total aprobado: {{ moneda(resumen.monto_aprobado) }}</strong><small>Totales de todos los resultados filtrados, no solo de esta página. Consulta lo entregado por fecha de pago en Pagos semanales.</small></div>
                <div class="commission-filters" role="group" aria-label="Filtrar por aprobación"><button v-for="f in filtros" :key="f.valor" type="button" :class="{ active: filtroEstado === f.valor }" :aria-pressed="filtroEstado === f.valor" @click="cambiarEstado(f.valor)" :disabled="cargando||guardando">{{ f.nombre }}</button></div>
                <p v-if="cargando" class="commission-empty" role="status">Cargando comisiones…</p>
                <p v-else-if="!registrosFiltrados.length" class="commission-empty">No hay comisiones{{ filtroEstado === 'todas' ? ' registradas' : ' con este estado' }}.</p>
                <div v-else class="commission-table-scroll">
                    <table class="commission-table"><thead><tr><th>Producto / venta</th><th>Empleado / sucursal</th><th>Fechas</th><th>Comisión</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
                        <tr v-for="registro in registrosFiltrados" :key="registro.id">
                            <td><strong>{{ registro.producto_nombre || registro.dispositivo }}</strong><small v-if="registro.detalle_venta_id">{{ registro.numero_venta }} · Unidad {{ registro.unidad }}</small><small v-else>Registro histórico sin vínculo a venta</small><small>{{ moneda(registro.costo) }} · {{ pagos[registro.metodo_pago] || registro.metodo_pago }}</small></td>
                            <td><strong>{{ registro.nombre_empleado }}</strong><small>{{ registro.sucursal_nombre }}</small><label v-if="userRole==='admin'&&!registro.pagada" class="commission-caption commission-employee-label">Empleado del catálogo<select class="commission-employee-select" v-model="asignaciones[registro.id]"><option value="">Sin asignar</option><option v-for="e in empleados.filter(e=>e.sucursal_id===registro.sucursal_id)" :key="e.id" :value="e.id">{{ e.nombre }}</option></select></label></td>
                            <td><small v-if="registro.fecha_venta"><strong>Venta:</strong> {{ fecha(registro.fecha_venta) }}</small><small><strong>Registro:</strong> {{ fecha(registro.created_at) }}</small></td>
                            <td><template v-if="userRole === 'admin'"><label class="commission-caption" :for="'monto-' + registro.id">Monto de comisión</label><input class="commission-amount" :id="'monto-' + registro.id" v-model="montos[registro.id]" type="number" min="0" step="0.01" placeholder="0.00" :disabled="guardando||registro.pagada"></template><strong v-else>{{ registro.monto_comision === null ? 'Pendiente' : moneda(registro.monto_comision) }}</strong></td>
                            <td><span class="commission-badge" :class="registro.aprobada ? 'approved' : 'pending'">{{ registro.pagada ? 'Pagada' : registro.aprobada ? 'Aprobada · Por pagar' : 'No aprobada' }}</span></td>
                            <td><div v-if="userRole === 'admin' && !registro.pagada" class="commission-row-actions"><button class="btn btn-primary btn-sm" @click="revisar(registro, registro.aprobada)" :disabled="guardando">Guardar monto</button><button v-if="!registro.aprobada" class="btn btn-success btn-sm" @click="revisar(registro, true)" :disabled="guardando">Aprobar</button><button v-else class="btn btn-secondary btn-sm" @click="revisar(registro, false)" :disabled="guardando">Quitar aprobación</button></div><div v-else-if="!registro.aprobada && registro.creado_por_id === userId" class="commission-row-actions"><button v-if="$root.puede('comisiones', 'editar')" class="btn btn-secondary btn-sm" @click="editar(registro)" :disabled="guardando">Editar</button><button v-if="$root.puede('comisiones', 'eliminar')" class="btn btn-danger btn-sm" @click="eliminar(registro)" :disabled="guardando">Eliminar</button></div><span v-else class="commission-caption">—</span></td>
                        </tr>
                    </tbody></table>
                </div>
                <nav class="commission-pagination" aria-label="Paginación de comisiones"><label>Por página<select v-model.number="porPagina" @change="filtrar" :disabled="cargando||guardando"><option :value="10">10</option><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option></select></label><button class="btn btn-secondary" @click="irPagina(pagina-1)" :disabled="pagina<=1||cargando||guardando">Anterior</button><span>Página {{ pagina }} de {{ paginas }}</span><button class="btn btn-secondary" @click="irPagina(pagina+1)" :disabled="pagina>=paginas||cargando||guardando">Siguiente</button></nav>
            </section>
            </section>
        </section>
    `,
    data() { return { seleccionTab:'', consulta:{sucursal_id:'',tipo_fecha:'registro',desde:'',hasta:'',empleado:'',dispositivo:''}, filtrosAplicados:{}, sucursales:[], empleados:[], asignaciones:{}, pagina:1, paginas:1, total:0, porPagina:25, solicitudLista:0, resumen:{aprobadas:0,pendientes:0,monto_aprobado:0}, filtroEstado: 'todas', filtros: [{ valor: 'todas', nombre: 'Todas' }, { valor: 'pendientes', nombre: 'No aprobadas' }, { valor: 'aprobadas', nombre: 'Aprobadas' }], registros: [], montos: {}, formulario: { nombre_empleado: '', empleado_comision_id: '' }, pendientes: [], unidadSeleccionada: '', fechaVenta: '', buscandoVentas: false, errorVentas: '', busquedaRealizada: false, solicitudVentas: 0, editandoId: null, cargando: false, guardando: false, error: '', mensaje: '', pagos: { efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia', mixto: 'Mixto' } }; },
    watch: {
        '$root.userSucursal'() {
            this.limpiar(); this.registros = []; this.pagina=1; this.actualizar();this.cargarEmpleados();
        }
    },
    computed: {
        tabs(){if(this.userRole==='admin')return [{id:'pagos',nombre:'Pagos semanales'},{id:'comisiones',nombre:'Comisiones'},{id:'historial',nombre:'Historial de pagos'},{id:'empleados',nombre:'Empleados'}];const tabs=[];if(this.$root.puede('comisiones','crear')||(this.editandoId&&this.$root.puede('comisiones','editar')))tabs.push({id:'registrar',nombre:this.editandoId?'Editar comisión':'Registrar comisión'});if(this.$root.puede('comisiones','ver'))tabs.push({id:'comisiones',nombre:'Comisiones de la sucursal'},{id:'pagos',nombre:'Pagos semanales'});return tabs;},
        tabActiva(){return this.tabs.some(t=>t.id===this.seleccionTab)?this.seleccionTab:(this.tabs[0]?.id||'');},
        registrosFiltrados() { return this.registros; },
        seleccionada() { return this.pendientes.find(u => this.claveUnidad(u) === this.unidadSeleccionada) || null; }
    },
    methods: {
        moverTab(event,i){if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const n=this.tabs.length;const j=event.key==='Home'?0:event.key==='End'?n-1:(i+(event.key==='ArrowRight'?1:-1)+n)%n;this.seleccionTab=this.tabs[j].id;this.$nextTick(()=>this.$el.querySelector('#com-tab-'+this.seleccionTab)?.focus());},
        async cargarEmpleados(){try{this.empleados=(await axios.get('/api/comisiones/semanales/empleados',this.opciones())).data;}catch(e){this.fallo(e);}},
        filtrar(){this.filtrosAplicados={...this.consulta};this.pagina=1;this.cargar();},
        limpiarFiltros(){this.consulta={sucursal_id:'',tipo_fecha:'registro',desde:'',hasta:'',empleado:'',dispositivo:''};this.filtroEstado='todas';this.filtrar();},
        cambiarEstado(estado){this.filtroEstado=estado;this.pagina=1;this.cargar();},
        irPagina(pagina){this.pagina=pagina;this.cargar();},
        async cargarSucursales(){if(this.userRole!=='admin')return;try{const r=await axios.get('/api/admin/sucursales',this.opciones());this.sucursales=r.data.sucursales||r.data;}catch(e){this.fallo(e);}},
        async actualizar() {
            await this.cargar();
            if (this.userRole !== 'admin' && (this.$root.puede('comisiones', 'crear') || this.$root.puede('comisiones', 'editar'))) await this.buscarVentas();
        },
        claveUnidad(u) { return u.detalle_venta_id + ':' + u.unidad; },
        async buscarVentas() {
            const solicitud = ++this.solicitudVentas;
            this.unidadSeleccionada = ''; this.pendientes = []; this.errorVentas = ''; this.busquedaRealizada = false; this.buscandoVentas = false;
            if (!this.fechaVenta || this.fechaVenta < '2026-11-18') { this.errorVentas = 'Selecciona una fecha desde el 18/11/2026.'; return; }
            this.buscandoVentas = true;
            try {
                const r = await axios.get('/api/comisiones/pendientes', { ...this.opciones(), params: { fecha: this.fechaVenta } });
                if (solicitud !== this.solicitudVentas) return;
                this.pendientes = r.data.unidades || []; this.busquedaRealizada = true;
            } catch (e) {
                if (solicitud === this.solicitudVentas) this.errorVentas = e.response?.data?.error || 'No se pudieron consultar las ventas pendientes';
            } finally { if (solicitud === this.solicitudVentas) this.buscandoVentas = false; }
        },
        opciones() { return { headers: { Authorization: `Bearer ${this.token}` } }; },
        fallo(err) {
            this.error = err.response?.data?.error || 'No se pudo completar la operación';
            if (err.response?.status === 403 && this.userRole !== 'admin') {
                this.registros = []; this.limpiar();
                window.dispatchEvent(new Event('caracteristicas-actualizadas'));
            }
        },
        async cargar() {
            const solicitud=++this.solicitudLista;
            this.cargando = true; this.error = '';
            try {
                const res = await axios.get('/api/comisiones', {...this.opciones(),params:{...this.filtrosAplicados,estado:this.filtroEstado,pagina:this.pagina,por_pagina:this.porPagina}});
                if(solicitud!==this.solicitudLista)return;
                this.total=res.data.total??res.data.comisiones.length;this.pagina=res.data.pagina||1;this.paginas=res.data.paginas||1;this.resumen=res.data.resumen||{aprobadas:0,pendientes:0,monto_aprobado:0};
                this.registros = res.data.comisiones;
                this.asignaciones=Object.fromEntries(this.registros.map(r=>[r.id,r.empleado_comision_id||'']));
                this.montos = Object.fromEntries(this.registros.map(r => [r.id, r.monto_comision ?? '']));
            } catch (err) { if(solicitud===this.solicitudLista){this.registros=[];this.total=0;this.resumen={aprobadas:0,pendientes:0,monto_aprobado:0};this.fallo(err);} }
            finally { if(solicitud===this.solicitudLista)this.cargando = false; }
        },
        limpiar() { this.editandoId = null; this.formulario = { nombre_empleado: '', empleado_comision_id: '' }; this.unidadSeleccionada = ''; },
        editar(registro) {
            if (registro.aprobada || this.userRole === 'admin') return;
            this.editandoId = registro.id;this.seleccionTab='registrar';
            this.formulario = { nombre_empleado: registro.nombre_empleado, empleado_comision_id:registro.empleado_comision_id||'' };
            this.mensaje = ''; this.error = '';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        async guardar() {
            if (this.guardando) return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                if (this.editandoId) await axios.put('/api/comisiones/' + this.editandoId, {empleado_comision_id:this.formulario.empleado_comision_id}, this.opciones());
                else {
                    if (!this.seleccionada) { this.error = 'Selecciona una unidad vendida.'; return; }
                    await axios.post('/api/comisiones', { empleado_comision_id: this.formulario.empleado_comision_id,
                        detalle_venta_id: this.seleccionada.detalle_venta_id, unidad: this.seleccionada.unidad }, this.opciones());
                }
                this.limpiar(); await this.cargar(); await this.buscarVentas(); this.$refs?.semanales?.cargar();this.mensaje = 'Registro guardado.';this.seleccionTab='comisiones';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        async revisar(registro, aprobada) {
            if (this.guardando || this.userRole !== 'admin') return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                await axios.put('/api/comisiones/' + registro.id, { monto_comision: this.montos[registro.id], aprobada, ...(this.asignaciones[registro.id]?{empleado_comision_id:this.asignaciones[registro.id]}:{}) }, this.opciones());
                await this.cargar();this.$refs.semanales.cargar(); this.mensaje = 'Comisión actualizada.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        async eliminar(registro) {
            if (this.guardando || registro.aprobada || !confirm('¿Eliminar este registro de comisión?')) return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                await axios.delete('/api/comisiones/' + registro.id, this.opciones());
                if (this.editandoId === registro.id) this.limpiar();
                await this.cargar(); await this.buscarVentas(); this.mensaje = 'Registro eliminado.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        moneda(valor) { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(valor); },
        fecha(valor) { return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Mexico_City' }).format(new Date(valor)); }
    },
    mounted() {
        const partes = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
        const valores = Object.fromEntries(partes.map(p => [p.type, p.value]));
        this.fechaVenta = [valores.year, valores.month, valores.day].join('-');
        this.cargar();this.cargarSucursales();this.cargarEmpleados();
        if (this.userRole !== 'admin' && (this.$root.puede('comisiones', 'crear') || this.$root.puede('comisiones', 'editar'))) this.buscarVentas();
    }
};

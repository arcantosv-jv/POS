const PronosticosView = {
    props: ['token'],
    template: `
    <section class="forecast-page">
        <header class="forecast-heading"><h1>Pronósticos de ventas</h1><p>Explora el importe y las unidades que podrías vender, con base en tu historial.</p></header>
        <p v-if="error" class="alert alert-danger" role="alert">{{ error }}</p><p v-if="mensaje" class="alert alert-success" role="status">{{ mensaje }}</p>
        <div class="forecast-tabs" role="group" aria-label="Secciones de pronósticos"><button v-for="t in tabs" :key="t.id" :class="{ active: tab === t.id }" @click="tab = t.id" :aria-pressed="tab === t.id">{{ t.nombre }}</button></div>
        <section v-if="tab === 'proyeccion'">
            <form v-if="$root.puede('pronosticos', 'generar')" class="card" @submit.prevent="generar">
                <div class="card-header"><h2>Generar pronóstico</h2></div>
                <fieldset :disabled="ocupado" class="forecast-fields">
                    <div><label for="forecast-branch">Sucursal</label><select id="forecast-branch" v-model="sucursal"><option value="">{{ $root.userRole === 'admin' ? 'Todas las sucursales' : 'Mis sucursales autorizadas' }}</option><option v-for="s in sucursales" :value="s.id" :key="s.id">{{ s.nombre }}</option></select></div>
                    <div><label for="forecast-period">Periodo</label><select id="forecast-period" v-model="periodo"><option value="dias">Próximos días</option><option value="meses">Próximos meses</option><option value="rango">Fechas personalizadas</option></select></div>
                    <div v-if="periodo !== 'rango'"><label for="forecast-quantity">{{ periodo === 'dias' ? 'Número de días' : 'Número de meses' }}</label><input id="forecast-quantity" type="number" min="1" :max="periodo === 'dias' ? 732 : 24" v-model.number="cantidad" required></div>
                    <template v-else><div><label for="forecast-from">Desde</label><input id="forecast-from" type="date" v-model="inicio" :min="manana" required></div><div><label for="forecast-to">Hasta</label><input id="forecast-to" type="date" v-model="fin" :min="inicio || manana" required></div></template>
                    <button class="btn btn-primary" type="submit">{{ ocupado ? 'Generando…' : 'Generar pronóstico' }}</button>
                </fieldset><p class="forecast-help">Se proyectan días completos desde mañana, con fecha de CDMX. Máximo 24 meses. Cada generación guarda una nueva versión.</p>
            </form>
            <section v-if="actual" class="card">
                <div class="card-header"><div><h2>Tu proyección</h2><p class="forecast-help">{{ fecha(actual.inicio) }} — {{ fecha(actual.fin) }} · {{ nombresSucursales(actual) }}</p></div><span class="forecast-tag">Versión guardada</span></div>
                <div class="forecast-fields forecast-controls"><div><label for="forecast-cat">Categoría</label><select id="forecast-cat" v-model="categoria"><option value="total">Todas las categorías</option><option v-for="c in actual.resultado.categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option></select></div><div><label for="forecast-metric">Mostrar</label><select id="forecast-metric" v-model="metrica"><option value="importe">Importe vendido</option><option value="unidades">Unidades vendidas</option></select></div></div>
                <div class="forecast-scenarios"><article v-for="(nombre, i) in escenarios" :key="nombre" :class="{ expected: i === 1 }"><span>{{ nombre }}</span><strong>{{ formato(seleccion.totales[metrica][i]) }}</strong><small>{{ metrica === 'importe' ? 'Ventas netas estimadas' : 'Unidades estimadas' }}</small></article></div>
                <p class="forecast-help">Las unidades se muestran como estimación decimal. Los tres escenarios son orientativos, no intervalos de confianza.</p>
                <div class="forecast-chart"><svg viewBox="0 0 1000 300" role="img" :aria-label="'Historial y proyección de ' + seleccion.nombre"><title>Ventas históricas y escenarios futuros</title><line x1="65" y1="250" x2="980" y2="250" stroke="#cbd5e1"/><line x1="65" y1="30" x2="65" y2="250" stroke="#cbd5e1"/><text x="5" y="24" fill="#64748b" font-size="13">{{ formato(grafica.max) }}</text><text x="40" y="250" fill="#64748b" font-size="13">0</text><polyline v-for="linea in grafica.lineas" :key="linea.nombre" :points="linea.puntos" fill="none" :stroke="linea.color" stroke-width="3" :stroke-dasharray="linea.dash"><title>{{ linea.nombre }}</title></polyline><text x="65" y="280" fill="#64748b" font-size="13">{{ fecha(grafica.desde) }}</text><text x="980" y="280" text-anchor="end" fill="#64748b" font-size="13">{{ fecha(actual.fin) }}</text></svg></div>
                <div class="forecast-legend"><span>● Histórico (incluye reemplazos manuales)</span><span style="color:#2563eb">● Esperado</span><span style="color:#d97706">● Conservador</span><span style="color:#059669">● Optimista</span></div>
                <details class="forecast-details"><summary>Detalle diario proyectado</summary><div class="forecast-scroll"><table><thead><tr><th>Fecha</th><th>Conservador</th><th>Esperado</th><th>Optimista</th></tr></thead><tbody><tr v-for="d in seleccion.dias" :key="d.fecha"><td>{{ fecha(d.fecha) }}</td><td v-for="(v,i) in d[metrica]" :key="i">{{ formato(v) }}</td></tr></tbody></table></div></details>
                <details class="forecast-details"><summary>Historial mensual utilizado</summary><div class="forecast-scroll"><table><thead><tr><th>Mes</th><th>Importe neto</th><th>Unidades netas</th></tr></thead><tbody><tr v-for="m in seleccion.meses" :key="m.mes"><td>{{ m.mes }}</td><td>{{ moneda(m.importe) }}</td><td>{{ numero(m.unidades) }}</td></tr></tbody></table></div><p class="forecast-help">Historial desde {{ fecha(actual.resultado.historial_desde) }} hasta {{ fecha(actual.resultado.corte) }}. El último mes puede estar incompleto. {{ actual.resultado.manuales.length }} meses/sucursal con reemplazo manual.</p></details>
                <div class="forecast-info"><strong>Cómo interpretar el resultado</strong><ul><li v-for="a in actual.resultado.advertencias" :key="a">{{ a }}</li></ul><p>Modelo: promedio por día de la semana, con mayor peso a los datos recientes y tendencia limitada. Usa todo el historial disponible hasta ayer.</p></div>
                <section class="forecast-ai"><h3>Explicación con Gemini</h3><p v-if="actual.explicacion" class="forecast-ai-text">{{ actual.explicacion }}</p><p v-else>{{ explicando ? 'Preparando explicación…' : 'La proyección estadística ya está guardada.' }}</p><p v-if="errorIA" class="forecast-help" role="status">{{ errorIA }}</p><button v-if="!actual.explicacion && $root.puede('pronosticos', 'generar')" class="btn btn-secondary" @click="explicar" :disabled="explicando">{{ explicando ? 'Consultando…' : 'Obtener explicación' }}</button></section>
                <section class="forecast-comparison"><div class="card-header"><h3>Comparación con ventas reales</h3><button class="btn btn-secondary" @click="abrir(actual.id)" :disabled="ocupado">Actualizar comparación</button></div><p v-if="!actual.comparacion" class="forecast-help">Disponible cuando haya transcurrido al menos un día completo del periodo proyectado.</p><template v-else><p>{{ actual.comparacion.completo ? 'Periodo completo' : 'Comparación parcial' }} hasta {{ fecha(actual.comparacion.hasta) }}. Solo ventas reales, sin reemplazos manuales.</p><div v-if="comparacion" class="forecast-scenarios"><article><span>Proyectado al corte</span><strong>{{ formato(comparacion.esperado[indiceMetrica]) }}</strong></article><article><span>Venta real al corte</span><strong>{{ formato(comparacion.real[indiceMetrica]) }}</strong></article><article><span>Error absoluto porcentual</span><strong>{{ comparacion.error_porcentual[indiceMetrica] === null ? 'No aplica (real = 0)' : numero(comparacion.error_porcentual[indiceMetrica]) + '%' }}</strong></article></div></template></section>
            </section><p v-else class="forecast-empty">Genera una proyección o abre una del historial para consultar sus resultados.</p>
        </section>
        <section v-if="tab === 'historial'" class="card"><div class="card-header"><h2>Pronósticos guardados</h2><button class="btn btn-secondary" @click="cargar" :disabled="ocupado">Actualizar</button></div><p class="forecast-help">Las cifras originales se conservan. Abre una versión para compararla con las ventas reales.</p><div class="forecast-scroll"><table><thead><tr><th>Generado</th><th>Sucursales</th><th>Periodo</th><th>Importe esperado</th><th>Unidades esperadas</th><th></th></tr></thead><tbody><tr v-for="r in registros" :key="r.id"><td>{{ fecha(r.created_at) }}</td><td>{{ nombresSucursales(r) }}</td><td>{{ fecha(r.inicio) }} — {{ fecha(r.fin) }}</td><td>{{ moneda(r.totales.importe[1]) }}</td><td>{{ numero(r.totales.unidades[1]) }}</td><td><button class="btn btn-secondary" @click="abrir(r.id)" :disabled="ocupado">Ver</button></td></tr></tbody></table></div><p v-if="!registros.length" class="forecast-empty">Aún no hay pronósticos guardados.</p></section>
        <section v-if="tab === 'datos'">
            <form v-if="$root.puede('pronosticos', 'historico')" class="card" @submit.prevent="guardarManual"><div class="card-header"><h2>Historial mensual manual</h2></div><p class="alert alert-info">Este mes reemplazará los datos del sistema para la sucursal seleccionada, solo en futuros pronósticos. Incluye todas las categorías vendidas; las omitidas contarán como cero. Captura importes y unidades netos, descontando devoluciones.</p><fieldset :disabled="ocupado" class="forecast-manual"><div class="forecast-fields"><div><label for="manual-branch">Sucursal</label><select id="manual-branch" v-model="manual.sucursal_id" required><option value="">Selecciona una sucursal</option><option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option></select></div><div><label for="manual-month">Mes completo</label><input id="manual-month" type="month" min="2000-01" :max="mesAnterior" v-model="manual.mes" required></div></div>
                <div v-for="(r, i) in manual.categorias" :key="i" class="forecast-fields forecast-manual-row"><div><label :for="'manual-cat-'+i">Categoría</label><select :id="'manual-cat-'+i" v-model="r.categoria_id"><option value="">Sin categoría</option><option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option></select></div><div><label :for="'manual-amount-'+i">Importe neto</label><input :id="'manual-amount-'+i" type="number" min="0" max="99999999.99" step="0.01" v-model="r.importe" required></div><div><label :for="'manual-units-'+i">Unidades netas</label><input :id="'manual-units-'+i" type="number" min="0" max="10000000" step="1" v-model.number="r.unidades" required></div><button type="button" class="btn btn-secondary" @click="manual.categorias.splice(i,1)" :disabled="manual.categorias.length === 1">Quitar</button></div><button type="button" class="btn btn-secondary" @click="manual.categorias.push({categoria_id:'',importe:'',unidades:0})">Agregar categoría</button><p class="forecast-manual-total">Total del mes: <strong>{{ moneda(totalManual.importe) }}</strong> · {{ numero(totalManual.unidades) }} unidades</p><div><label for="manual-reason">Motivo o fuente de los datos</label><input id="manual-reason" v-model="manual.motivo" maxlength="500" required placeholder="Ej.: reporte mensual anterior al sistema"></div><label class="forecast-confirm"><input type="checkbox" v-model="confirmar" required> Confirmo que el mes está completo y reemplazará todas sus categorías para esta sucursal.</label><button type="submit" class="btn btn-primary">{{ ocupado ? 'Guardando…' : 'Guardar histórico mensual' }}</button></fieldset></form>
            <section class="card"><div class="card-header"><h2>Meses con reemplazo manual</h2></div><div class="forecast-scroll"><table><thead><tr><th>Mes</th><th>Sucursal</th><th>Importe</th><th>Unidades</th><th></th></tr></thead><tbody><tr v-for="h in historicos" :key="h.sucursal_id+h.mes"><td>{{ h.mes }}</td><td>{{ nombreSucursal(h.sucursal_id) }}</td><td>{{ moneda(h.categorias.reduce((s,c)=>s+Number(c.importe),0)) }}</td><td>{{ numero(h.categorias.reduce((s,c)=>s+c.unidades,0)) }}</td><td><button v-if="$root.puede('pronosticos', 'historico')" class="btn btn-secondary" @click="editarManual(h)" :disabled="ocupado">Editar</button></td></tr></tbody></table></div><p v-if="!historicos.length" class="forecast-empty">Se utiliza únicamente el historial de ventas del sistema.</p></section>
        </section>
    </section>`,
    data() { return { tab:'proyeccion', tabs:[{id:'proyeccion',nombre:'Pronóstico'},{id:'historial',nombre:'Historial y resultados'},{id:'datos',nombre:'Datos históricos'}], sucursales:[], categorias:[], hoy:'', sucursal:'', periodo:'dias', cantidad:30, inicio:'', fin:'', registros:[], historicos:[], actual:null, categoria:'total', metrica:'importe', escenarios:['Conservador','Esperado','Optimista'], ocupado:false, explicando:false, error:'', errorIA:'', mensaje:'', confirmar:false, manual:{sucursal_id:'',mes:'',categorias:[{categoria_id:'',importe:'',unidades:0}],motivo:''}, solicitud:0 }; },
    computed: {
        manana() { return this.sumarDias(this.hoy,1); },
        mesAnterior() { if (!this.hoy) return ''; const d = new Date(this.hoy+'T12:00:00Z'); d.setUTCDate(0); return d.toISOString().slice(0,7); },
        seleccion() { return this.categoria === 'total' ? this.actual.resultado.total : this.actual.resultado.categorias.find(c=>c.id===this.categoria) || this.actual.resultado.total; },
        indiceMetrica() { return this.metrica === 'importe' ? 0 : 1; },
        comparacion() { return this.actual?.comparacion?.categorias.find(c=>c.id===this.categoria); },
        totalManual() { return this.manual.categorias.reduce((s,c)=>({importe:s.importe+(Number(c.importe)||0),unidades:s.unidades+(Number(c.unidades)||0)}),{importe:0,unidades:0}); },
        grafica() {
            const c=this.seleccion, hist=c.historico.slice(-30), metric=this.metrica;
            const desde=hist[0]?.fecha || this.actual.inicio, start=Date.parse(desde), end=Date.parse(this.actual.fin);
            const max=Math.max(1,...hist.map(d=>d[metric]),...c.dias.map(d=>d[metric][2]));
            const punto=(d,v)=>[65+(Date.parse(d)-start)/Math.max(86400000,end-start)*915,250-v/max*220].join(',');
            return {max,desde,lineas:[{nombre:'Histórico',color:'#64748b',dash:'',puntos:hist.map(d=>punto(d.fecha,d[metric])).join(' ')},...[{nombre:'Conservador',color:'#d97706',i:0},{nombre:'Esperado',color:'#2563eb',i:1},{nombre:'Optimista',color:'#059669',i:2}].map(l=>({...l,dash:'6 4',puntos:c.dias.map(d=>punto(d.fecha,d[metric][l.i])).join(' ')}))]};
        }
    },
    methods: {
        opciones() { return {headers:{Authorization:'Bearer '+this.token}}; },
        sumarDias(day,n) { if(!day) return ''; const d=new Date(day+'T12:00:00Z'); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10); },
        rango() {
            if(this.periodo==='rango') return {inicio:this.inicio,fin:this.fin};
            if(!Number.isInteger(this.cantidad)||this.cantidad<1||this.cantidad>(this.periodo==='dias'?732:24)) throw new Error('Indica una cantidad válida para el periodo.');
            const inicio=this.manana;
            if(this.periodo==='dias') return {inicio,fin:this.sumarDias(inicio,this.cantidad-1)};
            const d=new Date(inicio+'T12:00:00Z'), day=d.getUTCDate(); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth()+this.cantidad);
            const last=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate(); d.setUTCDate(Math.min(day,last));
            return {inicio,fin:this.sumarDias(d.toISOString().slice(0,10),-1)};
        },
        async cargar() {
            try { const [o,r,h]=await Promise.all([axios.get('/api/pronosticos/opciones',this.opciones()),axios.get('/api/pronosticos',this.opciones()),axios.get('/api/pronosticos/historicos',this.opciones())]); this.sucursales=o.data.sucursales;this.categorias=o.data.categorias;this.hoy=o.data.hoy;this.registros=r.data.pronosticos;this.historicos=h.data.historicos; }
            catch(e){this.error=e.response?.data?.error||'No se pudo cargar el módulo.';}
        },
        async generar() {
            if(this.ocupado)return;this.ocupado=true;this.error='';this.errorIA='';this.solicitud++;this.explicando=false;
            try{const r=await axios.post('/api/pronosticos',{...this.rango(),sucursal_id:this.sucursal||null},this.opciones());this.actual=r.data;this.categoria='total';await this.cargar();this.explicar();}
            catch(e){this.error=e.response?.data?.error||e.message||'No se pudo generar el pronóstico.';}finally{this.ocupado=false;}
        },
        async abrir(id) {
            if(this.ocupado)return;this.ocupado=true;this.error='';this.errorIA='';this.solicitud++;this.explicando=false;
            try{const r=await axios.get('/api/pronosticos/'+id,this.opciones());this.actual=r.data;this.categoria='total';this.tab='proyeccion';}
            catch(e){this.error=e.response?.data?.error||'No se pudo abrir el pronóstico.';}finally{this.ocupado=false;}
        },
        async explicar() {
            if(this.explicando||!this.actual)return;this.explicando=true;this.errorIA='';const id=this.actual.id,version=++this.solicitud;
            try{const r=await axios.post('/api/pronosticos/'+id+'/explicar',{},this.opciones());if(this.actual?.id===id&&version===this.solicitud)this.actual.explicacion=r.data.explicacion;}
            catch(e){if(this.actual?.id===id&&version===this.solicitud)this.errorIA=e.response?.data?.error||'No se pudo consultar Gemini; las cifras permanecen guardadas.';}
            finally{if(version===this.solicitud)this.explicando=false;}
        },
        editarManual(h){this.manual={sucursal_id:h.sucursal_id,mes:h.mes,categorias:h.categorias.map(c=>({...c})),motivo:''};this.confirmar=false;this.mensaje='';window.scrollTo({top:0,behavior:'smooth'});},
        async guardarManual(){if(this.ocupado||!this.confirmar)return;this.ocupado=true;this.error='';this.mensaje='';try{const r=await axios.put('/api/pronosticos/historicos',this.manual,this.opciones());this.mensaje=r.data.message;this.confirmar=false;await this.cargar();}catch(e){this.error=e.response?.data?.error||'No se pudo guardar el histórico.';}finally{this.ocupado=false;}},
        nombreSucursal(id){return this.sucursales.find(s=>s.id===id)?.nombre||'Sucursal';},
        nombresSucursales(r){return r.sucursales.map(id=>r.resultado?.sucursales_nombres?.[id]||this.nombreSucursal(id)).join(', ');},
        moneda(v){return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:2}).format(v);},
        numero(v){return new Intl.NumberFormat('es-MX',{maximumFractionDigits:2}).format(v);},
        formato(v){return this.metrica==='importe'?this.moneda(v):this.numero(v);},
        fecha(v){return v?new Intl.DateTimeFormat('es-MX',{dateStyle:'medium',timeZone:'America/Mexico_City'}).format(new Date(v.length===10?v+'T12:00:00Z':v)):'';}
    },
    mounted(){this.cargar();},
    beforeUnmount(){this.solicitud++;}
};

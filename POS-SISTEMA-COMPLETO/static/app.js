const { createApp } = Vue;

createApp({
    components: {
        'comisiones-view': ComisionesView,
        'apartados-view': ApartadosView,
        'ventas-view': VentasView,
        'caracteristicas-view': CaracteristicasView,
        'productos-view': ProductosView,
        'inventario-view': InventarioView,
        'reportes-view': ReportesView,
        'centro-reportes-view': CentroReportesView,
        'usuarios-view': UsuariosView,
        'dashboard-view': DashboardView,
        'sucursales-view': SucursalesView,
        'categorias-view': CategoriasView,
        'centro-categorias-view': CentroCategoriasView,
        'administracion-view': AdministracionView,
        'subcategorias-view': SubcategoriasView,
        'ventas-del-dia-view': VentasDelDiaView,
        'cierre-caja-view': CierreCajaView,
        'cierres-caja-admin-view': CierresCajaAdminView,
        'reportes-ventas-view': ReportesVentasView,
        'devoluciones-view': DevolucionesView,
        'compatibilidad-view': CompatibilidadView,
        'reparaciones-view': ReparacionesView,
        'ventas-sin-stock-view': VentasSinStockView,
        'ayuda-view': AyudaView
    },
    data() {
        return {
            // Autenticación
            isAuthenticated: false,
            token: '',
            userName: '',
            userId: '',
            userRole: '',
            userSucursal: '',
            sucursalPrincipal: '',
            
            // Vistas
            currentView: 'dashboard',
            menuAbierto: false,
            apartadosHabilitados: false,
            comisionesHabilitadas: false,
            accesoTimer: null,
            permisos: {},
            sucursalesAcceso: [],
            accesosListos: false,
            accesoVersion: 0,
            
            // Formulario de login
            loginForm: {
                username: '',
                password: ''
            },
            showLoginPassword: false,
            loginError: '',
            loginLoading: false,
            
            // URL API
            apiUrl: window.location.origin
        };
    },
    created() {
        this.verificarAutenticacion();

        // Interceptor para agregar token a todas las peticiones (lee del localStorage siempre)
        axios.interceptors.request.use(config => {
            const token = localStorage.getItem('token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
                if (this.userSucursal) config.headers['X-Sucursal-Id'] = this.userSucursal;
            }
            return config;
        });

        // Interceptor para manejar errores 401
        const self = this;
        axios.interceptors.response.use(
            response => response,
            error => {
                if (error.response?.status === 401) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    self.isAuthenticated = false;
                    self.token = '';
                    alert('Sesión expirada. Por favor inicia sesión nuevamente.');
                }
                return Promise.reject(error);
            }
        );
    },
    mounted() {
        this.cargarAcceso();
        this.accesoTimer = setInterval(this.cargarAcceso, 30000);
        window.addEventListener('caracteristicas-actualizadas', this.cargarAcceso);
        window.addEventListener('focus', this.cargarAcceso);
    },
    beforeUnmount() {
        clearInterval(this.accesoTimer);
        window.removeEventListener('caracteristicas-actualizadas', this.cargarAcceso);
        window.removeEventListener('focus', this.cargarAcceso);
    },
    watch: { token() { this.accesosListos = false; this.permisos = {}; this.comisionesHabilitadas = false; this.cargarAcceso(); } },
    methods: {
        puede(module, action = 'ver') {
            if (this.userRole === 'admin') return true;
            if (!this.accesosListos || (module === 'comisiones' && !this.comisionesHabilitadas) || (module === 'apartados' && !this.apartadosHabilitados)) return false;
            return (this.permisos[module] || []).includes(action);
        },
        puedeVista(view) {
            if (view === 'categorias') return this.puede('categorias') || this.puede('subcategorias');
            if (view === 'cierre-caja') return this.userRole !== 'admin' && this.puede('cierre-caja');
            // Un solo acceso: los usuarios de consulta conservan su vista de lectura.
            if (view === 'cierres-caja') return this.userRole === 'admin' ||
                (this.puede('cierres-caja') && !this.puede('cierre-caja'));
            if (view === 'reportes') return this.puede('reportes') || this.puede('reportes-ventas');
            if (['administracion', 'usuarios', 'sucursales', 'caracteristicas'].includes(view)) return this.userRole === 'admin';
            return this.puede(view, view === 'ayuda' ? 'consultar' : 'ver');
        },
        vistaInicial() {
            const vistas = this.userRole === 'admin' ? ['dashboard'] : ['ventas', ...Object.keys(this.permisos)];
            return vistas.map(view => view === 'reportes-ventas' ? 'reportes' : view === 'subcategorias' ? 'categorias' : view).find(view => this.puedeVista(view)) || 'sin-acceso';
        },
        cambiarSucursal() {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            user.sucursal_id = this.userSucursal;
            localStorage.setItem('user', JSON.stringify(user));
            this.menuAbierto = false;
        },
        async cargarAcceso() {
            const token = this.token;
            const version = ++this.accesoVersion;
            if (!token) return;
            try {
                const [config, acceso] = await Promise.all([
                    axios.get('/api/caracteristicas/acceso', { headers: { Authorization: `Bearer ${token}` } }),
                    axios.get('/api/permisos/mi-acceso', { headers: { Authorization: `Bearer ${token}` } })
                ]);
                if (this.token !== token || version !== this.accesoVersion) return;
                this.comisionesHabilitadas = !!config.data.comisiones_habilitadas;
                this.apartadosHabilitados = !!config.data.apartados_habilitados;
                this.permisos = acceso.data.permisos || {};
                this.userRole = acceso.data.role;
                this.sucursalPrincipal = acceso.data.sucursal_id || "";
                this.sucursalesAcceso = acceso.data.sucursales || [];
                if (!this.sucursalesAcceso.some(s => s.id === this.userSucursal)) this.userSucursal = acceso.data.sucursal_id || this.sucursalesAcceso[0]?.id || '';
                this.accesosListos = true;
            } catch (err) {
                if (this.token !== token || version !== this.accesoVersion) return;
                this.accesosListos = false; this.permisos = {}; this.comisionesHabilitadas = false;
            }
            if (!this.puedeVista(this.currentView)) this.currentView = this.vistaInicial();
        },
        async login() {
            this.loginError = '';
            this.loginLoading = true;
            
            try {
                const response = await axios.post(
                    `${this.apiUrl}/api/auth/login`,
                    this.loginForm
                );
                
                this.token = response.data.access_token;
                const user = response.data.user;
                
                // Guardar en localStorage
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(user));
                
                // Actualizar estado
                this.isAuthenticated = true;
                this.userName = user.username;
                this.userId = user.id;
                this.userRole = user.role;
                this.userSucursal = user.sucursal_id;
                
                // Redirigir a dashboard o ventas según rol
                this.currentView = user.role === 'admin' ? 'dashboard' : 'ventas';
                
                // Limpiar formulario
                this.loginForm = { username: '', password: '' };
                this.showLoginPassword = false;
            } catch (error) {
                this.loginError = error.response?.data?.error || 'Error en autenticación';
                console.error(error);
            } finally {
                this.loginLoading = false;
            }
        },
        
        irAVista(nombreVista) {
            if (nombreVista === 'subcategorias') nombreVista = 'categorias';
            if (nombreVista === 'reportes-ventas') nombreVista = 'reportes';
            if (!this.puedeVista(nombreVista)) return;
            if (this.userRole === 'admin' && ['usuarios', 'sucursales', 'caracteristicas', 'categorias'].includes(nombreVista)) nombreVista = 'administracion';
            this.currentView = nombreVista;
            this.menuAbierto = false; // Cerrar menú automáticamente
            window.scrollTo({ top: 0, behavior: 'instant' });
        },
        
        logout() {
            if (confirm('¿Deseas cerrar sesión?')) {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                this.isAuthenticated = false;
                this.token = '';
                this.userName = '';
                this.userRole = '';
                this.loginForm = { username: '', password: '' };
                this.showLoginPassword = false;
                this.currentView = 'login';
            }
        },
        
        verificarAutenticacion() {
            const token = localStorage.getItem('token');
            const user = localStorage.getItem('user');
            
            console.log('[verificarAutenticacion] token:', token ? 'presente' : 'no', 'user:', user ? 'presente' : 'no');
            
            if (token && user) {
                try {
                    const userData = JSON.parse(user);
                    console.log('[verificarAutenticacion] userData:', userData);
                    this.token = token;
                    this.isAuthenticated = true;
                    this.userName = userData.username;
                    this.userId = userData.id;
                    this.userRole = userData.role;
                    this.userSucursal = userData.sucursal_id;
                    console.log('[verificarAutenticacion] después de asignar userRole:', this.userRole);
                    this.currentView = userData.role === 'admin' ? 'dashboard' : 'ventas';
                } catch (e) {
                    console.error('Error al recuperar datos de sesión:', e);
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                }
            } else {
                console.log('[verificarAutenticacion] No hay token o user en localStorage');
            }
        }
    }
}).mount('#app');

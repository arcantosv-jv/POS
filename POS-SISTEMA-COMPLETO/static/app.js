const { createApp } = Vue;

createApp({
    components: {
        'ventas-view': VentasView,
        'productos-view': ProductosView,
        'inventario-view': InventarioView,
        'reportes-view': ReportesView,
        'usuarios-view': UsuariosView,
        'dashboard-view': DashboardView,
        'sucursales-view': SucursalesView,
        'categorias-view': CategoriasView,
        'subcategorias-view': SubcategoriasView,
        'ventas-del-dia-view': VentasDelDiaView,
        'cierre-caja-view': CierreCajaView,
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
            
            // Vistas
            currentView: 'dashboard',
            menuAbierto: false,
            
            // Formulario de login
            loginForm: {
                username: '',
                password: ''
            },
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
    methods: {
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
            } catch (error) {
                this.loginError = error.response?.data?.error || 'Error en autenticación';
                console.error(error);
            } finally {
                this.loginLoading = false;
            }
        },
        
        irAVista(nombreVista) {
            this.currentView = nombreVista;
            this.menuAbierto = false; // Cerrar menú automáticamente
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

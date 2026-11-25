import unittest
from unittest.mock import patch
from datetime import datetime, date
from decimal import Decimal
import test_operacion_seguimiento as fixtures
from models import db, Comision, ConfiguracionSistema, EmpleadoComision, PagoComision, Sucursal
from routes_comisiones import comisiones_bp
from comisiones_semanales import semanales_bp, corte
from config import CDMX_TZ

class SemanalesTest(unittest.TestCase):
    request=fixtures.OperacionTest.request
    tearDown=fixtures.OperacionTest.tearDown
    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(comisiones_bp)
        self.client.application.register_blueprint(semanales_bp)
        db.session.add(ConfiguracionSistema(id=1,comisiones_habilitadas=True))
        self.employee.permisos={'comisiones':['ver','crear','editar']}
        self.e=EmpleadoComision(nombre='Jazmín',sucursal_id=self.branch.id,dia_pago=0,activo=True)
        db.session.add(self.e);db.session.commit()
        self.clock=patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,23,12)))
        self.clock.start();self.addCleanup(self.clock.stop)
    def commission(self,day=22,approved=True,cost=50):
        c=Comision(sucursal_id=self.branch.id,creado_por_id=self.employee.id,empleado_comision_id=self.e.id,
            nombre_empleado=self.e.nombre,dispositivo='Tablet',costo=500,metodo_pago='efectivo',monto_comision=cost,aprobada=approved,
            fecha_venta=CDMX_TZ.localize(datetime(2026,11,day,23,59)),created_at=CDMX_TZ.localize(datetime(2026,11,23,12)))
        db.session.add(c);db.session.commit();return c
    def summary(self,role='admin',query=''):
        r=self.request('/api/comisiones/semanales'+query,role=role,method='get');self.assertEqual(r.status_code,200,r.json);return r.json
    def pay(self,version,role='admin'):
        return self.request('/api/comisiones/semanales/empleados/'+self.e.id+'/pagar',{'version':version},role=role)
    def test_cycles(self):
        for weekday,expected in [(0,('2026-11-17','2026-11-23','2026-11-23')),(4,('2026-11-21','2026-11-27','2026-11-27')),(5,('2026-11-22','2026-11-28','2026-11-28'))]:
            self.e.dia_pago=weekday
            self.assertEqual(tuple(d.isoformat() for d in corte(self.e,date(2026,11,23))),expected)
    def test_paid_snapshot_arrears_and_late_approval(self):
        old=self.commission(10,cost=25);current=self.commission();pending=self.commission(20,False,30);future=self.commission(24,cost=99)
        summary=self.summary()['empleados'][0]
        self.assertEqual(summary['por_pagar'],75)
        r=self.pay(summary['version']);self.assertEqual(r.status_code,201,r.json)
        self.assertEqual(r.json['monto'],75);self.assertEqual(r.json['desde'],'2026-11-10')
        self.assertEqual(self.pay(summary['version']).status_code,409)
        self.assertEqual(PagoComision.query.count(),1)
        self.assertEqual(self.request('/api/comisiones/'+current.id,{'monto_comision':999,'aprobada':False},method='put').status_code,409)
        pending.aprobada=True;db.session.commit()
        self.assertEqual(self.summary()['empleados'][0]['por_pagar'],0)
        self.e.dia_pago=5;self.e.nombre='Nuevo nombre';db.session.commit()
        self.assertEqual(PagoComision.query.one().empleado_nombre,'Jazmín')
        self.assertEqual(self.summary(query='?desde=2026-11-23&hasta=2026-11-23')['total_entregado'],75)
        self.assertEqual(self.summary(query='?hasta=2026-11-22')['total_entregado'],0)
        self.assertIsNone(future.pago_comision_id)
    def test_late_payment_and_preview_conflict(self):
        self.commission(15)
        preview=self.summary()['empleados'][0]
        c=self.commission(20,True,10)
        self.assertEqual(self.pay(preview['version']).status_code,409)
        with patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,25,12))):
            p=self.summary()['empleados'][0]
            self.assertEqual(p['hasta_pagable'],'2026-11-30')
            self.assertEqual(self.pay(p['version']).status_code,201)
    def test_scope_and_assignment(self):
        self.commission()
        self.assertEqual(len(self.summary(role='employee')['empleados']),1)
        self.assertEqual(self.pay('x',role='employee').status_code,403)
        other=Sucursal(nombre='Otra',direccion='Otra');db.session.add(other);db.session.flush()
        db.session.add(EmpleadoComision(nombre='Otra persona',sucursal_id=other.id,dia_pago=4));db.session.commit()
        self.assertEqual(len(self.summary(role='employee')['empleados']),1)
        c=self.commission();c.empleado_comision_id=None;db.session.commit()
        self.assertEqual(self.summary()['sin_asignar'],1)
        r=self.request('/api/comisiones/'+c.id,dict(monto_comision=50,aprobada=True,empleado_comision_id=self.e.id),method='put')
        self.assertEqual(r.status_code,200,r.json);self.assertEqual(self.summary()['sin_asignar'],0)

    def test_payday_included_and_later_approval_waits_next_week(self):
        approved=self.commission(23,True,70)
        pending=self.commission(23,False,30)
        p=self.summary()['empleados'][0]
        self.assertEqual(p['por_pagar'],70)
        self.assertEqual(p['hasta_pagable'],'2026-11-23')
        self.assertEqual(self.pay(p['version']).status_code,201)
        pending.aprobada=True;db.session.commit()
        self.assertEqual(self.summary()['empleados'][0]['por_pagar'],0)
        with patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,30,12))):
            p=self.summary()['empleados'][0]
            self.assertEqual(p['por_pagar'],30)
            self.assertEqual(self.pay(p['version']).status_code,201)
        self.assertEqual(PagoComision.query.count(),2)

    def test_upcoming_approved_separate_from_arrears_and_payable(self):
        self.e.dia_pago=3;db.session.commit()
        self.commission(25,True,100)
        self.commission(18,True,20)
        self.commission(18,False,30)
        self.commission(24,False,40)
        with patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,25,12))):
            p=self.summary()['empleados'][0]
            self.assertEqual(p['dia_programado'],'2026-11-26')
            self.assertEqual(p['aprobado_semana'],100)
            self.assertEqual(p['aprobado_anterior'],20)
            self.assertEqual(p['total_proximo_pago'],120)
            self.assertEqual(len(p['detalle_aprobadas']),2)
            self.assertEqual(sum(c['comision'] for c in p['detalle_aprobadas']),120)
            self.assertEqual([c['fecha'] for c in p['detalle_aprobadas']],['2026-11-18','2026-11-25'])
            self.assertEqual([c['anterior'] for c in p['detalle_aprobadas']],[True,False])
            self.assertEqual(p['anteriores_sin_aprobar'],1)
            self.assertEqual(p['por_pagar'],120)
        with patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,26,12))):
            p=self.summary()['empleados'][0]
            self.assertEqual(p['por_pagar'],120)
            self.assertEqual(self.pay(p['version']).status_code,201)
            p=self.summary()['empleados'][0]
            self.assertEqual(p['dia_programado'],'2026-12-03')
            self.assertEqual(p['total_proximo_pago'],0)

    def test_early_payment_matches_displayed_250(self):
        self.e.dia_pago=3;db.session.commit()
        old=self.commission(18,True,150)
        current=self.commission(25,True,100)
        pending=self.commission(25,False,80)
        with patch('comisiones_semanales.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,25,12))):
            p=self.summary()['empleados'][0]
            self.assertEqual(p['total_proximo_pago'],250)
            self.assertEqual(p['por_pagar'],250)
            self.assertEqual(p['cantidad_pago'],2)
            self.assertEqual(p['hasta_pagable'],'2026-11-26')
            result=self.pay(p['version'])
            self.assertEqual(result.status_code,201,result.json)
            self.assertEqual(result.json['monto'],250)
            self.assertEqual({c['id'] for c in result.json['comisiones']},{old.id,current.id})
            self.assertIsNone(pending.pago_comision_id)
            self.assertEqual(self.pay(p['version']).status_code,409)

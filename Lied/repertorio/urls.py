from django.urls import path
from . import views

urlpatterns = [
    # Rutas básicas
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('privacidad/', views.privacidad, name='privacidad'),
    path('terminos/', views.terminos, name='terminos'),
    path('contacto/', views.contacto, name='contacto'),
    path('features/', views.features, name='features'),

    # Gestión de partituras
    path('scores/', views.lista_piezas, name='lista_piezas'),
    path('scores/añadir/', views.añadir_pieza, name='añadir_pieza'),
    path('scores/editar/<int:pieza_id>/', views.editar_pieza, name='editar_pieza'),
    path('scores/eliminar/<int:pieza_id>/', views.eliminar_pieza, name='eliminar_pieza'),

    # Análisis y ejercicios
    path('analisis/<int:pieza_id>/', views.detalle_analisis, name='detalle_analisis'),
    path('ejercicios/<int:pieza_id>/', views.generar_ejercicios, name='generar_ejercicios'),
    path('ejercicios/dashboard/', views.dashboard_ejercicios, name='dashboard_ejercicios'),

    # Anotaciones y notas técnicas
    path('notas/', views.lista_notas, name='lista_notas'),
    path('notas/nueva/', views.crear_nota, name='crear_nota'),
    path('notas/editar/<int:nota_id>/', views.editar_nota, name='editar_nota'),
    path('notas/eliminar/<int:nota_id>/', views.eliminar_nota, name='eliminar_nota'),

    # Planes de práctica
    path('practica/', views.formulario_rutina, name='formulario_rutina'),
    path('practica/generar/', views.generar_rutina, name='generar_rutina'),
    
    # Nuevas rutas para el sistema de dominio y grabaciones
    path('dominio/mapa/', views.mapa_dominio, name='mapa_dominio'),
    path('dominio/subir-grabacion/<int:pieza_id>/', views.subir_grabacion, name='subir_grabacion'),
    path('dominio/comparar/<int:pieza_id>/', views.comparar_grabaciones, name='comparar_grabaciones'),
    path('dominio/actualizar/<int:pieza_id>/', views.actualizar_dominio, name='actualizar_dominio'),
]
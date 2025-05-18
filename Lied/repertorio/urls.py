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
    path('analisis/<int:pieza_id>/', views.detalle_analisis, name='detalle_analisis')
]
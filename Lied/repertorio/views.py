from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from music21 import stream
import tempfile
import subprocess
import os
import logging
from datetime import datetime
from .models import PiezaMusical, Ejercicio
from .forms import PiezaMusicalForm
from .services import analizar_pieza_completa, _extraer_metadatos
from lxml import etree as ET
from music21 import converter

logger = logging.getLogger(__name__)

@never_cache
def home(request):
    return render(request, 'tailwind_theme/home.html')

@never_cache
def login_view(request):
    if request.method == 'POST':
        # Obtener los datos del formulario
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Autenticar al usuario
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Si las credenciales son válidas, iniciar sesión
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}!')
            return redirect('home')
        else:
            # Si las credenciales son incorrectas, mostrar un mensaje de error
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return redirect('login')
    else:
        # Si no es una solicitud POST, mostrar el formulario de inicio de sesión
        return render(request, 'registration/login.html')


@never_cache
def logout_view(request):
    logout(request)  # Cierra la sesión del usuario
    messages.success(request, 'Has cerrado sesión exitosamente.')
    # Limpiar mensajes anteriores
    storage = messages.get_messages(request)
    for message in storage:
        pass  # Esto limpia los mensajes almacenados
    return redirect('login')  # Redirige al usuario a la página de inicio de sesión

@never_cache
def register(request):
    if request.method == 'POST':
        # Obtener los datos del formulario
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validar que las contraseñas coincidan
        if password != confirm_password:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('register')

        # Validar que el nombre de usuario no esté en uso
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('register')

        # Validar que el correo electrónico no esté en uso
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('register')

        # Crear el usuario
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()  # Guardar el usuario en la base de datos
            messages.success(request, 'Cuenta creada exitosamente. Inicia sesión para continuar.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return redirect('register')
    else:
        # Si no es una solicitud POST, mostrar el formulario de registro
        return render(request, 'registration/register.html')

@never_cache
def privacidad(request):
    """
    Vista para mostrar la política de privacidad.
    """
    return render(request, 'tailwind_theme/privacy.html')


@never_cache
def terminos(request):
    """
    Vista para mostrar los términos y condiciones.
    """
    return render(request, 'tailwind_theme/terms.html')

@never_cache
def contacto(request):

    if request.method == 'POST':
        messages.success(request, 'Mensaje enviado')
    return render(request, 'tailwind_theme/contact.html')

@never_cache
def features(request):
    """
    Vista para mostrar las características de la aplicación.
    """
    return render(request, 'tailwind_theme/features.html')

@never_cache
def editar_pieza(request, pieza_id):

    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    if request.method == 'POST':
        form = PiezaMusicalForm(request.POST, request.FILES, instance=pieza)
        if form.is_valid():
            form.save()
            messages.success(request, "Pieza actualizada correctamente")
            return redirect('lista_piezas')
        else:
            messages.error(request, "Error en el formulario")
    else:
        form = PiezaMusicalForm(instance=pieza)
    return render(request, 'scores/edit_piece.html', {'form': form, 'pieza': pieza})

@never_cache
def eliminar_pieza(request, pieza_id):

    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    try:
        pieza.delete()
        messages.success(request, "Pieza eliminada correctamente")
    except Exception as e:
        logger.error(f"Error al eliminar la pieza: {str(e)}")
        messages.error(request, "Error al eliminar la pieza")
    return redirect('lista_piezas')


@never_cache
def lista_piezas(request):
    piezas = PiezaMusical.objects.filter(usuario=request.user)
    return render(request, 'scores/list_repertoire.html', {'piezas': piezas})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
import os
import logging

logger = logging.getLogger(__name__)

@never_cache
def añadir_pieza(request):
    if request.method == 'POST':
        form = PiezaMusicalForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pieza = form.save(commit=False)
                pieza.usuario = request.user
                pieza.save()  # Guardar primero el objeto

                if pieza.partitura_musicxml:
                    try:
                        # Verificar existencia del archivo
                        if not os.path.exists(pieza.partitura_musicxml.path):
                            raise FileNotFoundError("Archivo no subido correctamente")
                            
                        # Parsear el archivo XML y extraer metadatos
                        root = ET.parse(pieza.partitura_musicxml.path).getroot()
                        metadatos = _extraer_metadatos(root)
                    
                        # Actualizar los campos de la pieza con los metadatos extraídos
                        pieza.titulo = metadatos['titulo']
                        pieza.compositor = metadatos['compositor']
                        pieza.save()  # Guardar actualización
                        
                    except Exception as e:
                        logger.error(f"Error en análisis: {str(e)}")
                        messages.warning(request, "Análisis parcial realizado")
                
                return redirect('lista_piezas')
            
            except Exception as e:
                logger.error(f"Error guardando pieza: {str(e)}")
                messages.error(request, "Error crítico al guardar la pieza")
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return render(request, 'scores/add_piece.html', {'form': PiezaMusicalForm()})


@never_cache
def detalle_analisis(request, pieza_id):
    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    
    try:
        if pieza.partitura_musicxml and os.path.exists(pieza.partitura_musicxml.path):
            analisis = analizar_pieza_completa(pieza.partitura_musicxml.path)
            if analisis is None:
                raise ValueError("El análisis devolvió None")
            
            # Procesamiento básico de pedalización
            pedalizacion = analisis.get('tecnicas', {}).get('pedalizacion', {})
            total_compases = pedalizacion.get('total_compases', 0)
            compases_con_pedal = pedalizacion.get('compases_con_pedal', 0)
            if total_compases > 0:
                pedalizacion['porcentaje_uso'] = round((compases_con_pedal / total_compases) * 100, 1)
            else:
                pedalizacion['porcentaje_uso'] = 0

            # Obtener coordinación entre manos (sin modificar estructura)
            coordinacion_manos = analisis.get('tecnicas', {}).get('coordinacion_manos', {})
            
            # Mantener los datos mínimos necesarios
            datos_analisis = {
                'tonalidad_principal': analisis.get('tonalidad', 'No detectada'),
                'compas_principal': analisis.get('metricas', {}).get('compas_principal', '4/4'),
                'cambios_compas': analisis.get('metricas', {}).get('cambios_compas', []),
                'modulaciones': analisis.get('modulaciones', []),
                'pedalizacion': pedalizacion,
                'coordinacion_manos': coordinacion_manos  # Se mantiene igual
            }
            
            pieza.analisis_data = datos_analisis
            pieza.save()
            
        else:
            messages.error(request, "La partitura MusicXML no está disponible")
            
    except Exception as e:
        logger.error(f"Error en análisis de pieza {pieza_id}: {str(e)}", exc_info=True)
        messages.error(request, f"Error al analizar la partitura: {str(e)}")
        datos_analisis = getattr(pieza, 'analisis_data', {})
    
    return render(request, 'scores/detailed_analysis.html', {
        'pieza': pieza,
        'analisis': datos_analisis
    })
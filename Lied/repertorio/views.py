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
from .generate_study import GeneradorEjercicios
import base64
from .models import NotaTecnica, PiezaMusical
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import random
import logging
from repertorio.models import PiezaMusical
from .models import PiezaMusical, DominioPieza  

logger = logging.getLogger(__name__)

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
    
    # Manejar generación directa desde parámetro GET
    tipo_ejercicio = request.GET.get('generar')
    if tipo_ejercicio and piezas.exists():
        return redirect('generar_ejercicios', pieza_id=piezas.first().id)
    
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

@never_cache
def generar_ejercicios(request, pieza_id):
    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    analisis = pieza.analisis_data or {}

    generador = GeneradorEjercicios(analisis, pieza)

    ejercicios_objs = {
        'escalas': {
            'contenido': generador.generar_ejercicio('escala_modal_acelerada'),
            'titulo': 'Escalas Tonales'
        },
        'saltos': {
            'contenido': generador.generar_ejercicio('saltos_irregulares'),
            'titulo': 'Técnica de Saltos'
        },
        'ritmos': {
            'contenido': generador.generar_ejercicio('polirritmia_cruzada'),
            'titulo': 'Coordinación Rítmica'
        },
        'acordes': {
            'contenido': generador.generar_ejercicio('progresion_modulada'),
            'titulo': 'Progresiones Armónicas'
        }
    }

    ejercicios_base64 = {
        clave: {
            'contenido': datos['contenido'].contenido if datos['contenido'] else "",
            'titulo': datos['titulo']
        }
        for clave, datos in ejercicios_objs.items()
    }

    return render(request, 'exercises/exercise_generator.html', {
        'pieza': pieza,
        'ejercicios': ejercicios_base64,
        'analisis': analisis
    })


@never_cache
def dashboard_ejercicios(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    piezas = PiezaMusical.objects.filter(usuario=request.user).order_by('-creado_en')
    ejercicios_recientes = Ejercicio.objects.filter(partitura__usuario=request.user).order_by('-creado_en')[:4]
    
    ejercicios_data = []
    for ejercicio in ejercicios_recientes:
        try:
            contenido = ejercicio.contenido if ejercicio.contenido else ""
            ejercicios_data.append({
                'pieza': ejercicio.partitura,
                'contenido': contenido,
                'tipo': ejercicio.tipo,
                'fecha': ejercicio.creado_en,
                'color': _get_color_for_exercise(ejercicio.tipo),
                'icono': _get_icon_for_exercise(ejercicio.tipo),
                'titulo': ejercicio.get_tipo_display()
            })
        except Exception as e:
            logger.error(f"Error procesando ejercicio {ejercicio.id}: {str(e)}")
            continue
    
    return render(request, 'exercises/dashboard.html', {
        'piezas': piezas,
        'ejercicios_recientes': ejercicios_data,
        'recomendaciones': _get_recommendations(piezas.first() if piezas.exists() else None)
    })

def _get_color_for_exercise(exercise_type):
    colors = {
        'escalas': 'blue',
        'saltos': 'red',
        'ritmos': 'purple',
        'acordes': 'green'
    }
    return colors.get(exercise_type, 'gray')

def _get_icon_for_exercise(exercise_type):
    icons = {
        'escalas': 'sort-amount-up-alt',
        'saltos': 'arrows-alt-v',
        'ritmos': 'drum',
        'acordes': 'wave-square'
    }
    return icons.get(exercise_type, 'dumbbell')

def _get_recommendations(pieza):
    if not pieza or not hasattr(pieza, 'analisis_data'):
        return {
            'duracion': '15-20 minutos por ejercicio',
            'parametros': ['Tempo inicial: 60-80 BPM', 'Metrónomo obligatorio']
        }
    
    recomendaciones = {
        'duracion': '15-20 minutos por ejercicio',
        'parametros': ['Tempo inicial: 60-80 BPM', 'Metrónomo obligatorio']
    }
    
    try:
        if pieza.analisis_data.get('coordinacion_manos', {}).get('ritmo', {}).get('sincopas', {}).get('frecuencia') == 'alta':
            recomendaciones['parametros'].append('Enfócate en las sincopas')
        
        saltos_derecha = pieza.analisis_data.get('tecnica', {}).get('saltos', {}).get('derecha', {})
        if saltos_derecha.get('max_semitonos', 0) > 12:
            recomendaciones['parametros'].append('Calentamiento de manos necesario')

        # Ejemplo: si quieres incluir 'acordes_arpegios' o similares, tradúcelos aquí
        parametros_tecnicos = pieza.analisis_data.get('parametros_tecnicos', [])
        traduccion = {
            'acordes_arpegios': 'Acordes y Arpegios',
            'ritmos_complejos': 'Ritmos Complejos',
            'digitacion': 'Digitación',
            'articulacion': 'Articulación',
        }
        for param in parametros_tecnicos:
            texto = traduccion.get(param, param.replace('_', ' ').capitalize())
            recomendaciones['parametros'].append(texto)

    except AttributeError:
        pass
    
    return recomendaciones



def lista_notas(request):
    notas = NotaTecnica.objects.filter(usuario=request.user)
    return render(request, 'notes/list_notes.html', {'notas': notas})


def crear_nota(request):
    if request.method == 'POST':
        nota = NotaTecnica(
            usuario=request.user,
            titulo=request.POST['titulo'],
            contenido=request.POST['contenido'],
            tipo=request.POST['tipo'],
            pieza_relacionada_id=request.POST['pieza_relacionada'] or None
        )
        nota.save()
        return redirect('lista_notas')
    
    piezas = PiezaMusical.objects.filter(usuario=request.user)
    return render(request, 'notes/create_notes.html', {'piezas': piezas})

def editar_nota(request, nota_id):
    nota = get_object_or_404(NotaTecnica, id=nota_id, usuario=request.user)
    
    if request.method == 'POST':
        nota.titulo = request.POST['titulo']
        nota.contenido = request.POST['contenido']
        nota.tipo = request.POST['tipo']
        nota.pieza_relacionada_id = request.POST['pieza_relacionada'] or None
        nota.save()
        return redirect('lista_notas')
    
    piezas = PiezaMusical.objects.filter(usuario=request.user)
    return render(request, 'notes/edit_notes.html', {'nota': nota, 'piezas': piezas})


def eliminar_nota(request, nota_id):
    nota = get_object_or_404(NotaTecnica, id=nota_id, usuario=request.user)
    nota.delete()
    return redirect('lista_notas')


from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.utils import timezone
import random
import logging
from repertorio.models import PiezaMusical

logger = logging.getLogger(__name__)

@never_cache
@login_required
def formulario_rutina(request):
    """Muestra el formulario para configurar la rutina de práctica"""
    # Verificar si el usuario tiene piezas musicales
    if not PiezaMusical.objects.filter(usuario=request.user).exists():
        messages.warning(request, "Necesitas añadir al menos una pieza musical antes de generar una rutina")
        return redirect('añadir_pieza')
    
    return render(request, 'practice/practice_form.html')

@never_cache
@login_required
def generar_rutina(request):
    """Genera y muestra la rutina de práctica personalizada"""
    if request.method != 'POST':
        return redirect('formulario_rutina')
    
    try:
        # Obtener parámetros del formulario
        dias_semana = int(request.POST.get('dias_semana', 3))
        minutos_sesion = int(request.POST.get('minutos_sesion', 60))
        nivel = request.POST.get('nivel', 'intermedio')
        enfoque = request.POST.get('enfoque', 'repertorio')
        porcentaje_nuevo = int(request.POST.get('porcentaje_nuevo', 30))
        porcentaje_antiguo = int(request.POST.get('porcentaje_antiguo', 30))
        
        # Validar porcentajes
        if porcentaje_nuevo + porcentaje_antiguo > 80:
            porcentaje_nuevo = 30
            porcentaje_antiguo = 30
            messages.warning(request, "Los porcentajes se han ajustado para dejar espacio a ejercicios técnicos")
        
        # Calcular distribución
        porcentaje_ejercicios = 100 - (porcentaje_nuevo + porcentaje_antiguo)
        distribucion = {
            'nuevo': porcentaje_nuevo,
            'antiguo': porcentaje_antiguo,
            'ejercicios': porcentaje_ejercicios
        }
        
        # Obtener piezas del usuario
        piezas_usuario = PiezaMusical.objects.filter(usuario=request.user).order_by('-creado_en')
        piezas_nuevas = piezas_usuario[:3]  # Últimas 3 piezas añadidas
        piezas_antiguas = piezas_usuario[3:6] if len(piezas_usuario) > 3 else []
        
        # Generar planificación semanal con días correctos
        hoy = timezone.now().date()
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        # Rotar los días para que empiece desde el día actual
        dia_actual = hoy.weekday()  # Lunes=0, Domingo=6
        dias_rotados = dias[dia_actual:] + dias[:dia_actual]
        dias_seleccionados = dias_rotados[:dias_semana]
        
        planificacion = {}
        for i, dia in enumerate(dias_seleccionados):
            actividades = []
            
            # Calcular tiempos para cada tipo de actividad
            tiempo_nuevo = round((minutos_sesion * porcentaje_nuevo / 100) / 2)
            tiempo_antiguo = round((minutos_sesion * porcentaje_antiguo / 100) / 2)
            tiempo_ejercicios = round((minutos_sesion * porcentaje_ejercicios / 100))
            
            # Añadir actividades de piezas nuevas (si hay)
            if piezas_nuevas:
                actividades.append({
                    'tipo': 'Estudio de pieza nueva',
                    'duracion': tiempo_nuevo,
                    'piezas': [piezas_nuevas[i % len(piezas_nuevas)]] if piezas_nuevas else []
                })
            
            # Añadir actividades de repaso (si hay)
            if piezas_antiguas:
                actividades.append({
                    'tipo': 'Repaso de repertorio',
                    'duracion': tiempo_antiguo,
                    'piezas': [piezas_antiguas[i % len(piezas_antiguas)]] if piezas_antiguas else []
                })
            
            # Añadir ejercicios técnicos
            tipos_ejercicios = ['Escalas', 'Arpegios', 'Acordes', 'Técnica de dedos']
            ejercicios_dia = random.sample(tipos_ejercicios, 2)
            
            actividades.append({
                'tipo': 'Ejercicios técnicos',
                'duracion': tiempo_ejercicios,
                'ejercicios': ejercicios_dia
            })
            
            planificacion[dia] = actividades
        
        # Generar recomendaciones basadas en nivel y enfoque
        recomendaciones = generar_recomendaciones(nivel, enfoque, minutos_sesion)
        
        # Calcular tiempo total semanal
        tiempo_total = dias_semana * minutos_sesion
        
        context = {
            'parametros': {
                'dias_semana': dias_semana,
                'minutos_sesion': minutos_sesion,
                'nivel': nivel,
                'enfoque': enfoque
            },
            'distribucion': distribucion,
            'planificacion': planificacion,
            'recomendaciones': recomendaciones,
            'tiempo_total': tiempo_total,
            'fecha_generacion': datetime.now()
        }
        
        return render(request, 'practice/practice_plan.html', context)
    
    except Exception as e:
        logger.error(f"Error generando rutina: {str(e)}", exc_info=True)
        messages.error(request, "Error al generar la rutina. Inténtalo de nuevo.")
        return redirect('formulario_rutina')

def generar_recomendaciones(nivel, enfoque, minutos_sesion):
    """Genera recomendaciones personalizadas basadas en los parámetros de forma dinámica"""
    
    # Base de datos de recomendaciones por categoría
    recomendaciones_db = {
        'nivel': {
            'principiante': [
                "Divide tu tiempo de práctica en sesiones cortas de 20-30 minutos",
                "Enfócate en la precisión más que en la velocidad",
                "Practica ejercicios técnicos básicos diariamente",
                "Usa el metrónomo para desarrollar sentido rítmico"
            ],
            'intermedio': [
                "Alterna días de técnica intensiva con días de repertorio",
                "Graba tus sesiones para analizar tu progreso",
                "Trabaja la memorización de piezas clave",
                "Explora diferentes estilos musicales"
            ],
            'avanzado': [
                "Trabaja pasajes difíciles a tempo lento primero",
                "Practica la interpretación musical, no solo las notas",
                "Desarrolla tu propio estilo interpretativo",
                "Profundiza en el análisis armónico de las piezas"
            ],
            'profesional': [
                "Simula condiciones de concierto en algunas sesiones",
                "Analiza grabaciones de referencia para mejorar tu interpretación",
                "Desarrolla programas de concierto completos",
                "Trabaja la resistencia para piezas largas"
            ]
        },
        'enfoque': {
            'tecnica': [
                "Dedica el 70% del tiempo a ejercicios técnicos específicos",
                "Varía los ejercicios cada semana para evitar estancamiento",
                "Identifica y trabaja tus puntos técnicos débiles",
                "Combina técnica mecánica con expresión musical"
            ],
            'repertorio': [
                "Trabaja primero los pasajes más difíciles cuando estés fresco",
                "Divide las piezas en secciones para practicarlas por separado",
                "Analiza la estructura formal de cada pieza",
                "Graba y compara diferentes interpretaciones"
            ],
            'ambos': [
                "Balancea 50% técnica y 50% repertorio",
                "Aplica inmediatamente los ejercicios técnicos al repertorio",
                "Usa el repertorio para identificar necesidades técnicas"
            ],
            'audicion': [
                "Prepara un programa coherente y variado",
                "Simula la situación de audición al menos 2 veces por semana",
                "Practica la entrada y salida del escenario",
                "Prepara versiones abreviadas de tus piezas"
            ]
        },
        'tiempo': {
            'corto': [
                "Enfócate en 1-2 objetivos específicos por sesión",
                "Prioriza calidad sobre cantidad de material",
                "Usa técnicas de práctica concentrada"
            ],
            'medio': [
                "Divide la sesión en bloques de 25-30 minutos",
                "Alterna entre técnica, repertorio y lectura a primera vista",
                "Incluye tiempo para calentamiento y enfriamiento"
            ],
            'largo': [
                "Haz pausas cada 45-50 minutos para mantener la concentración",
                "Planifica diferentes tipos de actividad durante la sesión",
                "Incluye tiempo para experimentación creativa"
            ]
        }
    }

    # Seleccionar recomendaciones basadas en nivel
    recomendaciones = recomendaciones_db['nivel'].get(nivel, [])
    
    # Añadir recomendaciones basadas en enfoque
    recomendaciones.extend(recomendaciones_db['enfoque'].get(enfoque, []))
    
    # Añadir recomendaciones basadas en tiempo
    if minutos_sesion < 45:
        tiempo_key = 'corto'
    elif minutos_sesion < 90:
        tiempo_key = 'medio'
    else:
        tiempo_key = 'largo'
    recomendaciones.extend(recomendaciones_db['tiempo'].get(tiempo_key, []))
    
    # Mezclar las recomendaciones para variedad
    random.shuffle(recomendaciones)
    
    # Limitar a 4-6 recomendaciones para no saturar al usuario
    max_recomendaciones = random.randint(4, 6)
    return recomendaciones[:max_recomendaciones]


@never_cache
@login_required
def subir_grabacion(request, pieza_id):
    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    
    if request.method == 'POST':
        dominio, created = DominioPieza.objects.get_or_create(pieza=pieza)
        
        # Procesar grabación original
        if 'grabacion_original' in request.FILES:
            original_file = request.FILES['grabacion_original']
            ext = os.path.splitext(original_file.name)[1]
            filename = f"original_{pieza.id}{ext}"
            dominio.grabacion_original.save(filename, original_file, save=True)
        
        # Procesar grabación de ejecución
        if 'grabacion_ejecucion' in request.FILES:
            ejecucion_file = request.FILES['grabacion_ejecucion']
            ext = os.path.splitext(ejecucion_file.name)[1]
            filename = f"ejecucion_{pieza.id}{ext}"
            dominio.grabacion_ejecucion.save(filename, ejecucion_file, save=True)
        
        messages.success(request, "Grabaciones subidas correctamente")
        return redirect('mapa_dominio')
    
    return render(request, 'dominio/subir_grabacion.html', {'pieza': pieza})

@never_cache
@login_required
def comparar_grabaciones(request, pieza_id):
    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    dominio = get_object_or_404(DominioPieza, pieza=pieza)
    
    # Verificar existencia de archivos
    file_errors = []
    
    if dominio.grabacion_original:
        try:
            if not os.path.exists(dominio.grabacion_original.path):
                file_errors.append("original")
                dominio.grabacion_original = None
        except ValueError:
            file_errors.append("original")
            dominio.grabacion_original = None
    
    if dominio.grabacion_ejecucion:
        try:
            if not os.path.exists(dominio.grabacion_ejecucion.path):
                file_errors.append("ejecución")
                dominio.grabacion_ejecucion = None
        except ValueError:
            file_errors.append("ejecución")
            dominio.grabacion_ejecucion = None
    
    if file_errors:
        messages.warning(request, f"No se encontraron archivos de: {', '.join(file_errors)}")
        dominio.save()  # Actualiza el modelo si hubo archivos faltantes
    
    return render(request, 'dominio/comparar_grabaciones.html', {
        'pieza': pieza,
        'dominio': dominio
    })


@never_cache
@login_required
def mapa_dominio(request):
    # Obtener piezas con su dominio relacionado
    piezas = PiezaMusical.objects.filter(usuario=request.user).prefetch_related('dominio')
    
    # Verificar y limpiar grabaciones que no existen físicamente
    for pieza in piezas:
        if hasattr(pieza, 'dominio'):
            dominio = pieza.dominio
            # Verificar grabación original
            if dominio.grabacion_original:
                if not os.path.exists(dominio.grabacion_original.path):
                    dominio.grabacion_original = None
                    dominio.save()
            
            # Verificar grabación de ejecución
            if dominio.grabacion_ejecucion:
                if not os.path.exists(dominio.grabacion_ejecucion.path):
                    dominio.grabacion_ejecucion = None
                    dominio.save()
    
    return render(request, 'dominio/mapa_dominio.html', {
        'piezas': piezas,
        'current_time': timezone.now()  # Puede ser útil para el template
    })


@never_cache
@login_required
def actualizar_dominio(request, pieza_id):
    pieza = get_object_or_404(PiezaMusical, id=pieza_id, usuario=request.user)
    
    if request.method == 'POST':
        dominio, created = DominioPieza.objects.get_or_create(pieza=pieza)
        
        # Validación y limpieza de datos
        nivel = request.POST.get('nivel', 'PR').upper()[:2]  # Asegura 2 caracteres mayúsculas
        if nivel not in dict(DominioPieza.NIVEL_CHOICES).keys():
            nivel = 'PR'  # Valor por defecto si no es válido
            
        ultima_practica = request.POST.get('ultima_practica')
        try:
            # Validar formato de fecha
            if ultima_practica:
                from datetime import datetime
                datetime.strptime(ultima_practica, '%Y-%m-%d')  # Valida formato
        except ValueError:
            ultima_practica = None
        
        # Actualizar campos
        dominio.nivel = nivel
        dominio.ultima_practica = ultima_practica
        
        # Recalcular progreso si hay grabaciones
        if dominio.grabacion_original and dominio.grabacion_ejecucion:
            # Aquí puedes añadir tu lógica para calcular progreso
            # Ejemplo simple (deberías adaptarlo a tus necesidades):
            dominio.progreso = min(dominio.progreso + 10, 100) if dominio.progreso < 100 else 100
        
        dominio.save()
        messages.success(request, "Evaluación actualizada correctamente")
        return redirect('mapa_dominio')
    
    # Para GET requests, preparar datos iniciales
    dominio = DominioPieza.objects.filter(pieza=pieza).first()
    context = {
        'pieza': pieza,
        'dominio': dominio,
        'nivel_choices': DominioPieza.NIVEL_CHOICES  # Para usar en el template
    }
    return render(request, 'dominio/actualizar_dominio.html', context)
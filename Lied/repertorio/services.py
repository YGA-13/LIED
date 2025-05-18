from music21 import converter, interval
from music21 import note, chord, stream
import logging
from collections import defaultdict
from lxml import etree as ET
from collections import Counter
import math
from music21 import scale, chord, interval, note
from math import gcd

logger = logging.getLogger(__name__)
namespaces = {'ns': 'http://www.musicxml.org/ns/score-partwise'}

def analizar_pieza_completa(ruta_archivo):
    try:
        partitura = converter.parse(ruta_archivo)
        root = ET.parse(ruta_archivo).getroot()

        print(f"Analizando: {_analizar_coordinacion_manos(partitura, root)}")
        
        return {
            'metadatos': _extraer_metadatos(root),
            'tonalidad': _analizar_tonalidad(partitura, root),
            'modulaciones': _detectar_modulaciones(partitura),
            'metricas': {
                'compas_principal': _obtener_compas_principal(root),
                'cambios_compas': _obtener_cambios_compas(root)
            },
            'tecnicas': {
                'pedalizacion': _analizar_pedalizacion(root),
                'coordinacion_manos': _analizar_coordinacion_manos(partitura, root)
            }
        }
    except ET.ParseError as e:
        logger.error(f"Error al parsear XML: {str(e)}", exc_info=True)
        raise ValueError("El archivo MusicXML está mal formado")
    except Exception as e:
        logger.error(f"Error en análisis completo: {str(e)}", exc_info=True)

def _extraer_metadatos(root):
    metadatos = {'titulo': 'Título no disponible', 'compositor': 'Desconocido', 'fecha': ''}
    
    try:
        work_title = root.find(".//work/work-title")
        if work_title is not None and work_title.text:
            metadatos['titulo'] = work_title.text.strip()

        composer = root.find(".//identification/creator[@type='composer']")
        if composer is not None and composer.text:
            texto = composer.text.replace('–', '-').replace('—', '-').strip()
            metadatos['compositor'] = texto.split('(')[0].strip()
            if '(' in composer.text:
                metadatos['fecha'] = composer.text.split('(')[-1].replace(')', '').replace('–', '-').strip()

        credit_titles = root.findall(".//credit/credit-words")
        if metadatos['titulo'] == 'Título no disponible':
            for credit in credit_titles:
                if credit.text and len(credit.text.split()) > 1:
                    metadatos['titulo'] = credit.text.strip()
                    break

        if metadatos['compositor'] == 'Desconocido':
            for credit in credit_titles:
                if credit.text and any(word in credit.text.lower() for word in ["chopin", "bach", "mozart", "beethoven"]):
                    metadatos['compositor'] = credit.text.strip()
                    break

    except Exception as e:
        logger.error("Error extrayendo metadatos: %s", e)
    
    return metadatos

def _analizar_tonalidad(partitura, root):
    try:
        # Primero intentamos con el análisis de Music21 (krumhansl)
        key_analysis = partitura.analyze('key.krumhansl')
        if key_analysis.correlationCoefficient > 0.7:
            tonalidad = key_analysis.tonic.name
            modo = key_analysis.mode.capitalize()
        else:
            # Luego intentar directamente extraer la tonalidad desde el XML
            key_elements = root.findall(".//key")
            if key_elements:
                fifths = int(key_elements[0].findtext("fifths", default="0"))
                modo = key_elements[0].findtext("mode", default="major").capitalize()

                tonalidades = {
                    -7: 'Cb', -6: 'Gb', -5: 'Db', -4: 'Ab', -3: 'Eb', -2: 'Bb', -1: 'F',
                    0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#',
                    -8: 'Fb', -9: 'E', 8: 'G#', 9: 'D#'
                }
                tonalidad = tonalidades.get(fifths, 'Desconocida')
            else:
                tonalidad = "No definida"
                modo = "major"

        # Formatear correctamente los símbolos musicales
        # Reemplazar 'b' con '♭'
        tonalidad = tonalidad.replace('b', '♭')
        # Reemplazar '#' con '♯'
        tonalidad = tonalidad.replace('#', '♯')
        # Reemplazar '-' con '♭' (en caso de que aparezca)
        tonalidad = tonalidad.replace('-', '♭')

        # Reemplazar casos específicos para asegurar la corrección
        replacements = {
            'Eb': 'E♭',
            'Bb': 'B♭',
            'Fb': 'F♭',
            'Cb': 'C♭',
            'F#': 'F♯',
            'C#': 'C♯',
            'G#': 'G♯',
            'D#': 'D♯',
            'A#': 'A♯',
            'E#': 'E♯',
            'B#': 'B♯'
        }
        for original, replacement in replacements.items():
            tonalidad = tonalidad.replace(original, replacement)

        return f"{tonalidad} {modo}"
    except Exception as e:
        logger.warning("Error en análisis de tonalidad: %s", e)
        return "No detectada"

def _obtener_compas_principal(root):
    try:
        time_elements = root.findall(".//time")
        if not time_elements:
            return "4/4"
        
        first_time = time_elements[0]
        beats = first_time.findtext("beats", default="4")
        beat_type = first_time.findtext("beat-type", default="4")
        return f"{beats}/{beat_type}"
    except:
        return "4/4"
    
def _obtener_cambios_compas(root):
    try:
        time_elements = root.findall(".//time")
        if not time_elements:
            return []

        compases = []
        prev_compas = None
        
        for time_element in time_elements:
            beats = time_element.findtext("beats", default="4")
            beat_type = time_element.findtext("beat-type", default="4")
            compas_actual = f"{beats}/{beat_type}"
            
            if prev_compas is not None and compas_actual != prev_compas:
                if compas_actual not in compases:  # Evitar duplicados
                    compases.append(compas_actual)
            elif prev_compas is None:
                # Solo agregar el primer compás si hay más de uno
                if len(time_elements) > 1:
                    compases.append(compas_actual)
            
            prev_compas = compas_actual

        # Si solo hay un compás en toda la obra, no hay cambios
        if len(compases) == 1 and len(time_elements) == 1:
            return []
            
        # Agregar el compás inicial si hay cambios
        if len(compases) > 0 and compases[0] != prev_compas:
            compases.insert(0, prev_compas)

        return sorted(list(set(compases)))  # Lista ordenada y sin duplicados

    except Exception as e:
        logger.error(f"Error al obtener cambios de compás: {str(e)}")
        return []

def _detectar_modulaciones(partitura, sample_every=4):
    modulaciones = []
    ultima_tonalidad = None
    ultima_tonica = None
    
    # Diccionario corregido con distancias exactas
    INTERVALOS_CORRECTOS = {
        # Intervalos justos/mayores/menores
        'Unísono': {'semitono': 0, 'tono': 0},
        'Unísono disminuido': {'semitono': -1, 'tono': -0.5},  # Teórico
        'Segunda disminuida': {'semitono': 0, 'tono': 0},      # = Unísono
        'Segunda menor': {'semitono': 1, 'tono': 0.5},
        'Segunda mayor': {'semitono': 2, 'tono': 1},
        'Segunda aumentada': {'semitono': 3, 'tono': 1.5},     # = Tercera menor
        'Tercera disminuida': {'semitono': 2, 'tono': 1},      # = Segunda mayor
        'Tercera menor': {'semitono': 3, 'tono': 1.5},
        'Tercera mayor': {'semitono': 4, 'tono': 2},
        'Tercera aumentada': {'semitono': 5, 'tono': 2.5},     # = Cuarta justa
        'Cuarta disminuida': {'semitono': 4, 'tono': 2},       # = Tercera mayor
        'Cuarta justa': {'semitono': 5, 'tono': 2.5},
        'Cuarta aumentada': {'semitono': 6, 'tono': 3},        # = Quinta disminuida
        'Quinta disminuida': {'semitono': 6, 'tono': 3},
        'Quinta justa': {'semitono': 7, 'tono': 3.5},
        'Quinta aumentada': {'semitono': 8, 'tono': 4},        # = Sexta menor
        'Sexta disminuida': {'semitono': 7, 'tono': 3.5},      # = Quinta justa
        'Sexta menor': {'semitono': 8, 'tono': 4},
        'Sexta mayor': {'semitono': 9, 'tono': 4.5},
        'Sexta aumentada': {'semitono': 10, 'tono': 5},        # = Séptima menor
        'Séptima disminuida': {'semitono': 9, 'tono': 4.5},    # = Sexta mayor
        'Séptima menor': {'semitono': 10, 'tono': 5},
        'Séptima mayor': {'semitono': 11, 'tono': 5.5},
        'Séptima aumentada': {'semitono': 12, 'tono': 6},      # = Octava
        'Octava disminuida': {'semitono': 11, 'tono': 5.5},    # = Séptima mayor
        'Octava': {'semitono': 12, 'tono': 6}
    }

    for i in range(1, len(partitura.parts[0].getElementsByClass('Measure')) + 1, sample_every):
        try:
            segmento = partitura.measures(i, min(i+3, len(partitura.parts[0].getElementsByClass('Measure')))).chordify()
            analisis = segmento.analyze('key.aarden')
            
            if analisis.correlationCoefficient > 0.65:
                modo = 'Mayor' if analisis.mode == 'major' else 'Menor'
                tonalidad_actual = f"{analisis.tonic.name.replace('-','♭').replace('#','♯')} {modo}"
                tonica_actual = analisis.tonic
                
                if ultima_tonalidad and tonalidad_actual != ultima_tonalidad:
                    try:
                        intervalo = interval.Interval(ultima_tonica, tonica_actual)
                        nombre_español = {
                        # Traducciones completas
                        'Perfect Unison': 'Unísono',
                        'Diminished Unison': 'Unísono disminuido',
                        'Augmented Unison': 'Unísono aumentado',
                        
                        'Minor Second': 'Segunda menor',
                        'Major Second': 'Segunda mayor',
                        'Diminished Second': 'Segunda disminuida',
                        'Augmented Second': 'Segunda aumentada',
                        
                        'Minor Third': 'Tercera menor',
                        'Major Third': 'Tercera mayor',
                        'Diminished Third': 'Tercera disminuida',
                        'Augmented Third': 'Tercera aumentada',
                        
                        'Perfect Fourth': 'Cuarta justa',
                        'Diminished Fourth': 'Cuarta disminuida',
                        'Augmented Fourth': 'Cuarta aumentada',
                        
                        'Perfect Fifth': 'Quinta justa',
                        'Diminished Fifth': 'Quinta disminuida',
                        'Augmented Fifth': 'Quinta aumentada',
                        
                        'Minor Sixth': 'Sexta menor',
                        'Major Sixth': 'Sexta mayor',
                        'Diminished Sixth': 'Sexta disminuida',
                        'Augmented Sixth': 'Sexta aumentada',
                        
                        'Minor Seventh': 'Séptima menor',
                        'Major Seventh': 'Séptima mayor',
                        'Diminished Seventh': 'Séptima disminuida',
                        'Augmented Seventh': 'Séptima aumentada',
                        
                        'Perfect Octave': 'Octava',
                        'Diminished Octave': 'Octava disminuida',
                        'Augmented Octave': 'Octava aumentada'
                        }.get(intervalo.niceName, intervalo.niceName)
                        
                        # Obtener valores corregidos del diccionario
                        datos_intervalo = INTERVALOS_CORRECTOS.get(nombre_español, {'semitono': abs(intervalo.semitones), 'tono': abs(intervalo.semitones)/2})
                        
                        firma_transicion = {
                            'nombre': nombre_español,
                            'semitono': datos_intervalo['semitono'],
                            'tono': datos_intervalo['tono'],
                            'direccion': "↑" if intervalo.semitones > 0 else "↓" if intervalo.semitones < 0 else ""
                        }
                    except Exception as e:
                        print(f"Error en intervalo: {e}")
                        firma_transicion = None
                    
                    modulaciones.append({
                        'compas_inicio': i,
                        'tonalidad_anterior': ultima_tonalidad,
                        'nueva_tonalidad': tonalidad_actual,
                        'transicion': firma_transicion
                    })
                
                ultima_tonalidad = tonalidad_actual
                ultima_tonica = tonica_actual
        except Exception as e:
            print(f"Error en compás {i}: {e}")
            continue
    
    return modulaciones[:10]

def _analizar_pedalizacion(root):
    ns = {'mx': 'http://www.musicxml.org/ns/musicxml/3.1'}
    
    # Contar compases REALES
    total_compases = len(root.findall('.//mx:measure', ns) or 
                   root.findall('.//measure'))
    
    # Buscar pedales (start/change/stop)
    pedales = (root.findall('.//mx:pedal', ns) or 
               root.findall('.//pedal') or 
               root.findall('.//*[local-name()="pedal"]'))
    
    # Filtrar solo pedales de inicio (evitar duplicar count)
    pedales_inicio = [p for p in pedales if p.get('type') in (None, 'start', 'sustain', 'sostenuto')]
    
    # Compases únicos con pedal
    compases_pedal = set()
    for pedal in pedales:
        parent = pedal
        while parent is not None:
            if 'measure' in parent.tag.lower():
                compases_pedal.add(parent.get('number'))
                break
            parent = parent.getparent()
    
    porcentaje_uso = round((len(compases_pedal) / total_compases) * 100, 1) if total_compases > 0 else 0
    
    return {
        'frecuencia': 'muy frecuente' if len(compases_pedal)/total_compases > 0.75 
                    else 'frecuente' if len(compases_pedal)/total_compases > 0.5
                    else 'moderada' if len(compases_pedal)/total_compases > 0.25
                    else 'poco frecuente',
        
        'tipo': 'sostenuto' if any(p.get('type') == 'sostenuto' for p in pedales) 
              else 'sustain (damper)',
        
        'total_eventos': len(pedales_inicio),
        'compases_con_pedal': len(compases_pedal),
        'total_compases': total_compases,
        'porcentaje_uso': porcentaje_uso,
        
        'cambios_frecuentes': 'muy frecuentes' if len(pedales_inicio) > total_compases * 0.75
                            else 'frecuentes' if len(pedales_inicio) > total_compases * 0.5
                            else 'moderados' if len(pedales_inicio) > total_compases * 0.25
                            else 'pocos cambios',
        
        'sostenuto_presente': any(p.get('type') == 'sostenuto' for p in pedales),
        
        'estilo_uso': 'legato' if len(pedales_inicio) > total_compases * 1.5
                    else 'resonancia' if len(compases_pedal)/total_compases > 0.6
                    else 'articulado' if len(pedales_inicio) > total_compases * 0.8
                    else 'estándar'
    }


def _analizar_coordinacion_manos(partitura, xml_root):
    # Diccionario de explicaciones para polirritmos comunes
    EXPLICACIONES_POLIRRITMOS = {
        '2:3': "Dos notas contra tres pulsos (tresillo)",
        '2:4': "Dos notas contra cuatro pulsos (subdivisión simple)",
        '3:8': "Tres notas contra ocho pulsos (subdivisión compleja con fuerte asimetría)",
        '3:2': "Tres notas contra dos pulsos (agrupación simple, como el tresillo contra el binario)",
        '5:1': "Cinco notas contra pulso unitario (grupo quintillo)",
        '5:2': "Cinco notas por cada dos pulsos",
        '5:3': "Agrupación asimétrica común en música balcánica",
        '5:4': "Agrupación irregular (complejidad rítmica media)",
        '5:6': "Cinco contra seis (subdivisión compleja)",
        '5:7': "Agrupación heptagonal contra quintillo",
        '5:8': "Cinco notas contra ocho (subdivisión asimétrica)",

        '7:2': "Siete notas contra dos pulsos (patrón de subdivisión irregular)",
        '7:3': "Agrupación septillo contra tresillo",
        '7:4': "Siete contra cuatro (ritmo africano complejo)",
        '7:5': "Heptillo contra quintillo (ritmo asimétrico avanzado)",
        '7:6': "Siete contra seis (superposición métrica compleja)",
        '7:8': "Agrupación heptagonal (común en música contemporánea)",
        '7:9': "Siete contra nueve (ritmo de alta complejidad)",

        '8:3': "Ocho contra tres (subdivisión en grupos irregulares)",
        '8:5': "Ocho contra cinco (ritmo cruzado complejo)",
        '8:7': "Ocho contra siete (superposición métrica avanzada)",
        '8:9': "Ocho contra nueve (patrón rítmico de alta densidad)",

        '9:2': "Nueve contra dos (grupos extendidos)",
        '9:4': "Nueve contra cuatro (subdivisión en grupos de 3+3+3)",
        '9:5': "Nueve contra cinco (ritmo asimétrico complejo)",
        '9:6': "Tres grupos de tres contra dos grupos de tres (9:6 simplificado a 3:2)",
        '9:7': "Nueve contra siete (superposición métrica irregular)",
        '9:8': "Tres grupos de tres contra dos grupos de cuatro (complejidad rítmica alta)",
        '9:10': "Nueve contra diez (ritmo de densidad extrema)",

        '10:3': "Diez contra tres (grupos extendidos irregulares)",
        '10:7': "Diez contra siete (ritmo africano avanzado)",
        '10:9': "Diez contra nueve (superposición métrica compleja)",

        '11:4': "Once contra cuatro (ritmo de alta complejidad)",
        '11:6': "Once contra seis (subdivisión irregular avanzada)",
        '11:8': "Once contra ocho (patrón rítmico contemporáneo)",
        '11:12': "Once contra doce (superposición métrica extrema)",

        '12:5': "Doce contra cinco (cuatro grupos de tres contra quintillo)",
        '12:7': "Doce contra siete (ritmo de densidad compleja)",
        '12:11': "Doce contra once (superposición métrica avanzada)",

        '13:8': "Trece contra ocho (ritmo de alta complejidad métrica)",
        '13:12': "Trece contra doce (superposición métrica extrema)",
        '15:8': "Quince contra ocho (cinco grupos de tres contra ocho)",
        '16:9': "Dieciséis contra nueve (patrón rítmico de alta densidad)",

        '4:5:7': "Tres capas rítmicas simultáneas (complejidad polimétrica)",
        '3:5:7': "Agrupación polirrítmica en tres niveles",
        '2:3:5': "Superposición de hemiola, tresillo y quintillo",
        '5:9': "Cinco notas contra nueve pulsos (ritmo complejo de gran densidad)",
        '6:5': "Seis contra cinco (superposición irregular)",
        '6:7': "Seis contra siete (subdivisión compleja y asimétrica)",
        '6:8': "Seis contra ocho (subdivisión rítmica en desigualdad)",
        '7:10': "Siete contra diez (ritmo de gran asimetría)",
        '8:6': "Ocho contra seis (superposición de subdivisiones irregulares)",
        '9:12': "Nueve contra doce (subdivisión compleja, tipo hemiola expandida)",
    }


    analisis = {
        'ritmo': {
            'figuras_primarias': {'derecha': [], 'izquierda': []},
            'grupos_ritmicos': {'derecha': [], 'izquierda': []},
            'polirritmos': [],
            'polirritmos_detalle': {
                'relaciones': [],
                'explicaciones': {},
                'ejemplos': {}
            },
            'sincopas': {
                'total': 0,
                'frecuencia': 'baja',
                'ubicacion': []
            }
        },
        'tecnica': {
            'saltos': {
                'derecha': {
                    'max_semitonos': 0,
                    'frecuencia': 0,
                    'intervalo': ''
                },
                'izquierda': {
                    'max_semitonos': 0,
                    'frecuencia': 0,
                    'intervalo': ''
                }
            },
            'articulaciones': {
                'legato': {
                    'total': 0,
                    'porcentaje': 0
                },
                'staccato': {
                    'total': 0,
                    'porcentaje': 0
                }
            }
        },
        'estructura': {
            'densidad': {
                'maxima': {'compas': 0, 'notas': 0},
                'promedio': 0,
                'variacion': []
            },
            'proporcion': {
                'derecha': 0,
                'izquierda': 0,
                'relacion': '1:1',
                'balance': 'equilibrado',
                'explicacion': ''
            }
        },
        'observaciones': []
    }

    try:
        if len(partitura.parts) < 2:
            analisis['observaciones'].append("Partitura para una sola mano")
            return analisis

        md, mi = partitura.parts[0], partitura.parts[1]
        compases = list(zip(md.getElementsByClass('Measure'), mi.getElementsByClass('Measure')))
        total_compases = len(compases)
        total_notas_global = 0

        # Configuración
        duracion_orden = {
            '32nd': 0, '16th': 1, 'eighth': 2, 
            'quarter': 3, 'half': 4, 'whole': 5
        }

        trad_figuras = {
            'eighth': 'corchea', '16th': 'semicorchea', '32nd': 'fusa',
            'quarter': 'negra', 'half': 'blanca', 'whole': 'redonda'
        }

        trad_intervalos = {
            'Perfect Unison': 'Unísono perfecto',
            'Minor Second': 'Segunda menor',
            'Major Second': 'Segunda mayor',
            'Minor Third': 'Tercera menor',
            'Major Third': 'Tercera mayor',
            'Perfect Fourth': 'Cuarta justa',
            'Augmented Fourth': 'Cuarta aumentada',
            'Diminished Fifth': 'Quinta disminuida',
            'Perfect Fifth': 'Quinta justa',
            'Augmented Fifth': 'Quinta aumentada',
            'Minor Sixth': 'Sexta menor',
            'Major Sixth': 'Sexta mayor',
            'Augmented Sixth': 'Sexta aumentada',
            'Diminished Seventh': 'Séptima disminuida',
            'Minor Seventh': 'Séptima menor',
            'Major Seventh': 'Séptima mayor',
            'Augmented Seventh': 'Séptima aumentada',
            'Perfect Octave': 'Octava justa',
            'Perfect Double-octave': 'Doble octava justa',
            'Diminished Ninth': 'Novena disminuida',
            'Minor Ninth': 'Novena menor',
            'Major Ninth': 'Novena mayor',
            'Augmented Ninth': 'Novena aumentada',
            'Perfect Tenth': 'Décima justa',
            'Major Tenth': 'Décima mayor',
            'Minor Tenth': 'Décima menor',
            'Perfect Eleventh': 'Undécima justa',
            'Augmented Eleventh': 'Undécima aumentada',
            'Diminished Twelfth': 'Duodécima disminuida',
            'Perfect Twelfth': 'Duodécima justa',
            'Minor Thirteenth': 'Decimotercera menor',
            'Major Thirteenth': 'Decimotercera mayor',
            'Perfect Fourteenth': 'Decimocuarta perfecta',
            'Augmented Fourteenth': 'Decimocuarta aumentada',
            'Perfect Fifteenth': 'Decimoquinta perfecta',
            'Major Sixteenth': 'Decimosexta mayor',
            'Minor Sixteenth': 'Decimosexta menor',
            'Perfect Seventeenth': 'Decimoséptima perfecta',
            'Minor Eighteenth': 'Decimoctava menor',
            'Perfect Nineteenth': 'Decimonovena perfecta',
            'Augmented Nineteenth': 'Decimonovena aumentada',
            'Minor Twentieth': 'Vigésima menor',
            'Perfect Twentieth': 'Vigésima perfecta',
        }


        # Variables temporales
        figuras = {'derecha': set(), 'izquierda': set()}
        grupos_ritmicos = {'derecha': {}, 'izquierda': {}}
        sincopas_compases = set()
        saltos_detalle = {'derecha': [], 'izquierda': []}
        articulaciones_detalle = {'legato': 0, 'staccato': 0}
        total_notas_manos = {'derecha': 0, 'izquierda': 0}
        densidad_por_compas = []
        ejemplos_polirritmos = {}

        for i, (compas_d, compas_i) in enumerate(compases):
            notas_compas = 0
            
            # Análisis por mano
            for mano, compas in [('derecha', compas_d), ('izquierda', compas_i)]:
                figuras_compas = []
                notas_mano = [n for n in compas.notes if not n.isRest]
                total_notas_manos[mano] += len(notas_mano)
                
                for n in notas_mano:
                    # Figuras rítmicas
                    tipo_figura = n.duration.type
                    figuras[mano].add(tipo_figura)
                    figuras_compas.append(tipo_figura)
                    
                    # Sincopas
                    if n.tie and n.tie.type == 'start':
                        analisis['ritmo']['sincopas']['total'] += 1
                        sincopas_compases.add(i+1)
                    
                    # Articulaciones
                    for art in getattr(n, 'articulations', []):
                        art_type = art.name.lower()
                        if 'staccato' in art_type:
                            articulaciones_detalle['staccato'] += 1
                        if 'tenuto' in art_type or 'legato' in art_type:
                            articulaciones_detalle['legato'] += 1
                
                # Grupos rítmicos
                if len(figuras_compas) >= 2:
                    for j in range(len(figuras_compas)-1):
                        grupo = (figuras_compas[j], figuras_compas[j+1])
                        grupos_ritmicos[mano][grupo] = grupos_ritmicos[mano].get(grupo, 0) + 1
                
                # Saltos melódicos
                for j in range(1, len(notas_mano)):
                    try:
                        prev = notas_mano[j-1].pitches[-1] if notas_mano[j-1].isChord else notas_mano[j-1].pitch
                        curr = notas_mano[j].pitches[-1] if notas_mano[j].isChord else notas_mano[j].pitch
                        intervalo = interval.Interval(prev, curr)
                        semitonos = abs(intervalo.semitones)
                        
                        if semitonos > 8:
                            nombre_intervalo = trad_intervalos.get(intervalo.niceName, intervalo.niceName)
                            saltos_detalle[mano].append({
                                'compas': i+1,
                                'semitonos': semitonos,
                                'intervalo': nombre_intervalo
                            })
                            
                            if semitonos > analisis['tecnica']['saltos'][mano]['max_semitonos']:
                                analisis['tecnica']['saltos'][mano]['max_semitonos'] = semitonos
                                analisis['tecnica']['saltos'][mano]['intervalo'] = nombre_intervalo
                    except:
                        continue
            
            # Polirritmos
            notas_d = len([n for n in compas_d.notes if not n.isRest])
            notas_i = len([n for n in compas_i.notes if not n.isRest])
            notas_compas += notas_d + notas_i
            densidad_por_compas.append(notas_compas)
            
            if notas_d and notas_i and notas_d != notas_i:
                mcd_val = gcd(notas_d, notas_i)
                relacion = f"{notas_d//mcd_val}:{notas_i//mcd_val}"
                if relacion not in analisis['ritmo']['polirritmos']:
                    analisis['ritmo']['polirritmos'].append(relacion)
                
                # Registrar ejemplo del compás
                if relacion not in ejemplos_polirritmos:
                    ejemplos_polirritmos[relacion] = []
                ejemplos_polirritmos[relacion].append(i+1)
        
        # Procesamiento final
        # 1. Figuras rítmicas
        for mano in ['derecha', 'izquierda']:
            analisis['ritmo']['figuras_primarias'][mano] = [
                trad_figuras.get(f, f) 
                for f in sorted(figuras[mano], key=lambda x: duracion_orden.get(x, 10))
            ]
            
            # Grupos rítmicos más frecuentes
            grupos_ordenados = sorted(
                grupos_ritmicos[mano].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            analisis['ritmo']['grupos_ritmicos'][mano] = [
                {
                    'patron': [trad_figuras.get(f, f) for f in grupo],
                    'frecuencia': freq
                }
                for grupo, freq in grupos_ordenados
            ]
        
        # 2. Sincopas
        analisis['ritmo']['sincopas']['ubicacion'] = sorted(sincopas_compases)
        if analisis['ritmo']['sincopas']['total'] > total_compases * 0.3:
            analisis['ritmo']['sincopas']['frecuencia'] = 'alta'
        elif analisis['ritmo']['sincopas']['total'] > total_compases * 0.1:
            analisis['ritmo']['sincopas']['frecuencia'] = 'media'
        
        # 3. Polirritmos
        analisis['ritmo']['polirritmos'].sort(key=lambda x: int(x.split(':')[0]))
        
        # Añadir explicaciones de polirritmos
        analisis['ritmo']['polirritmos_detalle'] = {
            'relaciones': analisis['ritmo']['polirritmos'],
            'explicaciones': {
                rel: EXPLICACIONES_POLIRRITMOS.get(
                    rel, 
                    f"Relación rítmica compleja: {rel} notas entre manos"
                )
                for rel in analisis['ritmo']['polirritmos']
            },
            'ejemplos': {
                rel: ejemplos_polirritmos.get(rel, [])
                for rel in analisis['ritmo']['polirritmos']
            }
        }
        
        # 4. Técnica - Saltos
        for mano in ['derecha', 'izquierda']:
            analisis['tecnica']['saltos'][mano]['frecuencia'] = len([
                s for s in saltos_detalle[mano] if s['semitonos'] > 8
            ])
        
        # 5. Técnica - Articulaciones
        total_notas_global = sum(total_notas_manos.values())
        if total_notas_global > 0:
            analisis['tecnica']['articulaciones']['legato']['total'] = articulaciones_detalle['legato']
            analisis['tecnica']['articulaciones']['staccato']['total'] = articulaciones_detalle['staccato']
            analisis['tecnica']['articulaciones']['legato']['porcentaje'] = round(
                (articulaciones_detalle['legato'] / total_notas_global) * 100, 1
            )
            analisis['tecnica']['articulaciones']['staccato']['porcentaje'] = round(
                (articulaciones_detalle['staccato'] / total_notas_global) * 100, 1
            )
        
        # 6. Estructura - Densidad
        if densidad_por_compas:
            analisis['estructura']['densidad']['maxima'] = {
                'compas': densidad_por_compas.index(max(densidad_por_compas)) + 1,
                'notas': max(densidad_por_compas)
            }
            analisis['estructura']['densidad']['promedio'] = round(sum(densidad_por_compas) / len(densidad_por_compas), 1)
            analisis['estructura']['densidad']['variacion'] = densidad_por_compas
        
        # 7. Proporción
        total_d = total_notas_manos['derecha']
        total_i = total_notas_manos['izquierda']
        analisis['estructura']['proporcion']['derecha'] = total_d
        analisis['estructura']['proporcion']['izquierda'] = total_i
        
        if total_d == 0 and total_i == 0:
            relacion_str = "0:0"
            balance = "sin actividad"
            explicacion = "Ambas manos sin notas"
        elif total_i == 0:
            relacion_str = f"{total_d}:0"
            balance = "solo derecha"
            explicacion = f"Todas las notas ({total_d}) en la mano derecha"
        elif total_d == 0:
            relacion_str = f"0:{total_i}"
            balance = "solo izquierda"
            explicacion = f"Todas las notas ({total_i}) en la mano izquierda"
        else:
            gcd_val = gcd(total_d, total_i)
            relacion_str = f"{total_d//gcd_val}:{total_i//gcd_val}"
            
            ratio = total_d / total_i
            diferencia = abs(total_d - total_i)
            porcentaje_diferencia = (diferencia / min(total_d, total_i)) * 100
            
            if ratio > 2:
                balance = "derecha dominante"
                explicacion = f"La mano derecha tiene {total_d} notas ({porcentaje_diferencia:.1f}% más que la izquierda)"
            elif ratio > 1.2:
                balance = "ligero predominio derecho"
                explicacion = f"La mano derecha tiene {total_d} notas ({porcentaje_diferencia:.1f}% más que la izquierda)"
            elif ratio > 0.8:
                balance = "equilibrado"
                explicacion = f"Distribución equilibrada: {total_d} notas derecha vs {total_i} izquierda"
            elif ratio > 0.5:
                balance = "ligero predominio izquierdo"
                explicacion = f"La mano izquierda tiene {total_i} notas ({porcentaje_diferencia:.1f}% más que la derecha)"
            else:
                balance = "izquierda dominante"
                explicacion = f"La mano izquierda tiene {total_i} notas ({porcentaje_diferencia:.1f}% más que la derecha)"
        
        analisis['estructura']['proporcion']['relacion'] = relacion_str
        analisis['estructura']['proporcion']['balance'] = balance
        analisis['estructura']['proporcion']['explicacion'] = explicacion
        
        # 8. Observaciones técnicas
        if analisis['ritmo']['polirritmos']:
            analisis['observaciones'].append(
                "Patrones polirrítmicos detectados: " +
                "; ".join(
                    f"{rel} ({analisis['ritmo']['polirritmos_detalle']['explicaciones'][rel]})"
                    for rel in analisis['ritmo']['polirritmos']
                )
            )
        
        if analisis['ritmo']['sincopas']['frecuencia'] == 'alta':
            analisis['observaciones'].append(
                f"Sincopas frecuentes ({analisis['ritmo']['sincopas']['total']} casos)"
            )
        
        for mano in ['derecha', 'izquierda']:
            if analisis['tecnica']['saltos'][mano]['max_semitonos'] > 12:
                analisis['observaciones'].append(
                    f"Salto significativo en mano {mano}: {analisis['tecnica']['saltos'][mano]['max_semitonos']} semitonos "
                    f"({analisis['tecnica']['saltos'][mano]['intervalo']})"
                )
        
        if analisis['estructura']['proporcion']['balance'] != "equilibrado":
            analisis['observaciones'].append(
                f"Distribución desigual: {analisis['estructura']['proporcion']['explicacion']}"
            )
        
        return analisis

    except Exception as e:
        logger.error(f"Error en análisis técnico: {str(e)}")
        return {'error': 'Error en el procesamiento técnico'}
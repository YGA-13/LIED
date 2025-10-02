from music21 import stream, scale, note, tempo, meter, key, chord, roman
import random
import tempfile
import base64
from django.core.files import File
from django.utils import timezone
from .models import Ejercicio

class GeneradorEjercicios:
    def __init__(self, analisis, pieza_instance):
        self.analisis = analisis
        self.pieza_instance = pieza_instance
        self.config_base = {'compases': 12, 'tempo': 90, 'octavas': 1}

    def _configurar_entorno(self):
        # Tonalidad: extraer con prioridad del análisis
        tonalidad_str = self.analisis.get('tonalidad', 'C Mayor').split()
        try:
            tonalidad = key.Key(tonalidad_str[0], tonalidad_str[1].lower())
        except Exception:
            tonalidad = key.Key('C')

        compas_principal = self.analisis.get('metricas', {}).get('compas_principal', '4/4')
        tempo_val = self.analisis.get('tempo', self.config_base['tempo'])

        compases = self.analisis.get('compases', self.config_base['compases'])
        
        # Calcular velocidad basada en figuras rítmicas del análisis
        velocidad = 1
        try:
            coord_manos = self.analisis['tecnicas']['coordinacion_manos']
            figuras_d = coord_manos['ritmo']['figuras_primarias']['derecha']
            figuras_i = coord_manos['ritmo']['figuras_primarias']['izquierda']
            todas_figuras = figuras_d + figuras_i
            
            duraciones = {
                'fusa': 0.125, 'semicorchea': 0.25, 'corchea': 0.5,
                'negra': 1.0, 'blanca': 2.0, 'redonda': 4.0
            }
            
            if todas_figuras:
                fig_rapidas = [f for f in todas_figuras if f in ['fusa', 'semicorchea']]
                velocidad = max(1, len(fig_rapidas) * 1.5)
        except KeyError:
            pass
        
        return {
            'time_signature': meter.TimeSignature(compas_principal),
            'tonalidad': tonalidad,
            'tempo': tempo.MetronomeMark(number=tempo_val),
            'compases': compases,
            'octavas': self.config_base['octavas'],
            'velocidad': min(4, velocidad)  # Cap a 4x
        }

    def generar_ejercicio(self, tipo):
        config = self._configurar_entorno()
        score = stream.Score()
        derecha = stream.Part()
        izquierda = stream.Part()

        for parte in [derecha, izquierda]:
            parte.insert(0, config['time_signature'])
            parte.insert(0, config['tempo'])

        if tipo == 'escala_modal_acelerada':
            self._escala_modal_acelerada(config, derecha, izquierda)
        elif tipo == 'saltos_irregulares':
            self._saltos_irregulares(config, derecha, izquierda)
        elif tipo == 'polirritmia_cruzada':
            self._polirritmia_cruzada(config, derecha, izquierda)
        elif tipo == 'progresion_modulada':
            self._progresion_modulada(config, derecha, izquierda)
        else:
            raise ValueError(f"Tipo de ejercicio desconocido: {tipo}")

        derecha.partName = 'Derecha'
        izquierda.partName = 'Izquierda'
        score.append([derecha, izquierda])
        score.makeMeasures(inPlace=True)
        score.makeNotation(inPlace=True)

        with tempfile.NamedTemporaryFile(suffix='.musicxml') as tmp:
            score.write('musicxml', fp=tmp.name)
            tmp.seek(0)
            ejercicio = Ejercicio(
                partitura=self.pieza_instance,
                tipo=tipo,
                parametros={
                    'tonalidad': str(config['tonalidad']),
                    'compas': str(config['time_signature']),
                    'tempo': config['tempo'].number,
                    'compases': config['compases']
                },
                contenido=base64.b64encode(tmp.read()).decode('utf-8')
            )
            ejercicio.archivo_musicxml.save(f"{tipo}_{timezone.now().timestamp()}.musicxml", File(tmp))
            return ejercicio

    def _escala_modal_acelerada(self, config, derecha, izquierda):
        modos_map = {
            'dorian': scale.DorianScale,
            'phrygian': scale.PhrygianScale,
            'lydian': scale.LydianScale,
            'mixolydian': scale.MixolydianScale,
            'ionian': scale.MajorScale,
            'aeolian': scale.MinorScale,
        }
        
        # Usar modo del análisis o modo más complejo si hay modulaciones
        modo_nombre = self.analisis.get('modo', None)
        if not modo_nombre and self.analisis.get('modulaciones'):
            modo_nombre = random.choice(['dorian', 'phrygian', 'lydian'])
        
        modo_clase = modos_map.get(modo_nombre.lower() if modo_nombre else '', 
                                 random.choice(list(modos_map.values())))
        modo = modo_clase(config['tonalidad'].tonic)

        oct_d = 4
        oct_i = 3

        # Velocidad basada en análisis + desafío adicional
        duracion_base = max(0.125 / config['velocidad'], 0.03125) * 0.8  # 20% más rápido

        # Patrón rítmico complejo si hay polirritmos
        patron_ritmico = [duracion_base] * 8
        if self.analisis.get('tecnicas', {}).get('coordinacion_manos', {}).get('ritmo', {}).get('polirritmos'):
            patron_ritmico = [duracion_base * 0.5, duracion_base * 1.5] * 4

        for i in range(config['compases']):
            for j in range(8):
                p = modo.pitches[j % len(modo.pitches)]
                nota_d = note.Note(p.nameWithOctave[:-1] + str(oct_d), 
                                  quarterLength=patron_ritmico[j % len(patron_ritmico)])
                nota_i = note.Note(p.nameWithOctave[:-1] + str(oct_i), 
                                  quarterLength=patron_ritmico[(j+2) % len(patron_ritmico)])
                derecha.append(nota_d)
                izquierda.append(nota_i)

    def _saltos_irregulares(self, config, derecha, izquierda):
        # Saltos basados en análisis técnico
        try:
            saltos = self.analisis['tecnicas']['coordinacion_manos']['tecnica']['saltos']
            salto_d = saltos['derecha']['max_semitonos'] * 1.5  # 50% más amplios
            salto_i = saltos['izquierda']['max_semitonos'] * 1.5
        except KeyError:
            salto_d = 18  # Octava y media por defecto
            salto_i = 18

        max_saltos_d = min(24, max(8, salto_d))  # Limitar entre 8-24 semitonos
        max_saltos_i = min(24, max(8, salto_i))

        base_pitch_d = 'C4'
        base_pitch_i = 'C3'

        # Velocidad aumentada
        duracion = 0.5 / max(1, config['velocidad'] * 1.2)

        for _ in range(config['compases']):
            for _ in range(4):
                # Salto derecho con desafío adicional
                base_d = note.Note(base_pitch_d)
                salto_semitonos_d = random.randint(-max_saltos_d, max_saltos_d)
                trans_d = note.Note(base_d.pitch.transpose(salto_semitonos_d))
                
                # Salto izquierdo con dirección opuesta para coordinación
                base_i = note.Note(base_pitch_i)
                salto_semitonos_i = random.randint(-max_saltos_i, max_saltos_i)
                if salto_semitonos_d > 0:
                    salto_semitonos_i = max(-max_saltos_i, salto_semitonos_i - 5)
                else:
                    salto_semitonos_i = min(max_saltos_i, salto_semitonos_i + 5)
                trans_i = note.Note(base_i.pitch.transpose(salto_semitonos_i))

                base_d.quarterLength = duracion
                trans_d.quarterLength = duracion
                base_i.quarterLength = duracion
                trans_i.quarterLength = duracion

                derecha.append(base_d)
                derecha.append(trans_d)
                izquierda.append(base_i)
                izquierda.append(trans_i)

    def _polirritmia_cruzada(self, config, derecha, izquierda):
        # Usar polirritmos detectados o el más complejo disponible
        try:
            polirritmos = self.analisis['tecnicas']['coordinacion_manos']['ritmo']['polirritmos']
            if polirritmos:
                # Seleccionar relación más compleja (mayor suma)
                relacion = max(polirritmos, key=lambda x: sum(map(int, x.split(':'))))
            else:
                relacion = '3:2'
        except KeyError:
            relacion = '3:2'

        try:
            r_d, r_i = map(int, relacion.split(':'))
        except Exception:
            r_d, r_i = 3, 2

        # Aumentar complejidad con múltiplos
        r_d *= 2
        r_i *= 2

        oct_d = 4
        oct_i = 3

        dur_d = config['time_signature'].barDuration.quarterLength / r_d
        dur_i = config['time_signature'].barDuration.quarterLength / r_i

        # Patrón melódico alternante
        notas_d = ['C', 'E', 'G', 'B']
        notas_i = ['G', 'B', 'D', 'F']

        for _ in range(config['compases']):
            for i in range(r_d):
                idx = i % len(notas_d)
                derecha.append(note.Note(notas_d[idx] + str(oct_d), quarterLength=dur_d))
            for i in range(r_i):
                idx = i % len(notas_i)
                izquierda.append(note.Note(notas_i[idx] + str(oct_i), quarterLength=dur_i))

    def _progresion_modulada(self, config, derecha, izquierda):
        tonalidad_base = config['tonalidad']
        compas_len = config['time_signature'].barDuration.quarterLength

        # Usar progresiones reales de la pieza o desafío aumentado
        progresiones_analisis = self.analisis.get('progresiones', None)
        if progresiones_analisis:
            progresiones = progresiones_analisis
        else:
            progresiones = [
                ['I', 'IV', 'V', 'I'],
                ['ii', 'V', 'I'],
                ['vi', 'ii', 'V', 'I'],
                ['I', 'V/vi', 'vi', 'IV', 'V', 'I']  # Progresión con dominante secundaria
            ]

        oct_d = 4
        oct_i = 3

        # Secuencia de modulaciones reales o basadas en análisis
        modulaciones = self.analisis.get('modulaciones', [])
        tonalidades = [tonalidad_base]
        for mod in modulaciones[:config['compases']//2]:
            try:
                tonica, modo = mod['nueva_tonalidad'].split()
                tonalidades.append(key.Key(tonica, modo.lower()))
            except:
                pass

        for i in range(config['compases']):
            # Modulación basada en análisis o cíclica
            tonalidad_actual = tonalidades[i % len(tonalidades)]
            
            # Selección de progresión con tensión aumentada
            progresion = progresiones[i % len(progresiones)]
            grado = progresion[i % len(progresion)] if isinstance(progresion, list) else progresion
            
            rn = roman.RomanNumeral(grado, tonalidad_actual)
            
            # Añadir 7ma y 9na siempre para mayor desafío
            acordes_pitches = list(rn.pitches)
            if len(rn.pitches) > 1:
                acordes_pitches.append(rn.pitches[-1].transpose(3))  # 7ma
                acordes_pitches.append(rn.pitches[-1].transpose(6))  # 9na

            acorde_d = chord.Chord([p.transpose(12 * (oct_d - rn.root().octave)) for p in acordes_pitches])
            acorde_i = chord.Chord([p.transpose(12 * (oct_i - rn.root().octave)) for p in acordes_pitches])
            acorde_d.quarterLength = compas_len
            acorde_i.quarterLength = compas_len

            derecha.append(acorde_d)
            izquierda.append(acorde_i)
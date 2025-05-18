# ejercicios.py
from music21 import stream, scale, note, tempo, meter, articulations, key, chord
import random
import logging

logger = logging.getLogger(__name__)

class GeneradorEjercicios:
    def __init__(self, analisis):
        self.analisis = analisis
        self.niveles_dificultad = {
            1: {'octavas': 1, 'tempo': 80, 'duraciones': [0.5, 0.25]},
            2: {'octavas': 2, 'tempo': 100, 'duraciones': [0.25, 0.125]},
            3: {'octavas': 3, 'tempo': 120, 'duraciones': [0.125, 0.0625]}
        }
    
    def _configurar_entorno(self, nivel, tipo_ejercicio):
        config = self.niveles_dificultad.get(nivel, self.niveles_dificultad[2])
        return {
            'time_signature': meter.TimeSignature(self.analisis.get('compas_principal', '4/4')),
            'tonalidad': key.Key(self.analisis.get('tonalidad_principal', 'C')),
            'tempo': tempo.MetronomeMark(number=config['tempo']),
            'duraciones': config['duraciones'],
            'octavas': config['octavas'],
            'mano': tipo_ejercicio.split('_')[-1] if '_' in tipo_ejercicio else 'ambas'
        }

    def generar_ejercicio(self, tipo_ejercicio, nivel=2):
        try:
            config = self._configurar_entorno(nivel, tipo_ejercicio)
            
            if tipo_ejercicio == 'escalas_tonales':
                return self._generar_escalas(config)
            elif tipo_ejercicio == 'saltos_manos':
                return self._generar_saltos(config)
            elif tipo_ejercicio == 'ritmos_complejos':
                return self._generar_ritmos(config)
            elif tipo_ejercicio == 'acordes_arpegios':
                return self._generar_acordes(config)
            
            raise ValueError("Tipo de ejercicio no válido")
        except Exception as e:
            logger.error(f"Error generando ejercicio: {str(e)}")
            return stream.Score()

    def _generar_escalas(self, config):
        parte = stream.Part()
        escala = config['tonalidad'].getScale('major' if config['tonalidad'].mode == 'major' else 'harmonic minor')
        
        for octava in range(3, 3 + config['octavas']):
            notas = escala.getPitches(f'{escala.tonic.name}{octava}', 
                                    f'{escala.tonic.name}{octava + 1}')
            
            for n in notas:
                nota_obj = note.Note(n, quarterLength=random.choice(config['duraciones']))
                if random.random() < 0.3:
                    nota_obj.articulations.append(articulations.Staccato())
                parte.append(nota_obj)
        
        parte.insert(0, config['time_signature'])
        parte.insert(0, config['tempo'])
        return parte

    def _generar_saltos(self, config):
        parte = stream.Part()
        saltos = self.analisis.get('saltos_manos', {})
        mano = config['mano']
        
        intervalo_max = saltos.get(mano, {}).get('max_salto', 8) if mano != 'ambas' else 12
        intervalo_min = max(3, int(intervalo_max * 0.3))
        
        for _ in range(16):
            salto = random.randint(intervalo_min, intervalo_max)
            nota_base = random.choice(['C', 'D', 'E', 'F', 'G', 'A', 'B']) + str(4 if mano == 'derecha' else 3)
            
            n1 = note.Note(nota_base, quarterLength=0.5)
            n2 = n1.transpose(salto)
            parte.append([n1, n2])
        
        parte.insert(0, config['time_signature'])
        parte.insert(0, tempo.MetronomeMark(number=config['tempo'] + 20))
        return parte

    def _generar_ritmos(self, config):
        parte = stream.Part()
        compas = config['time_signature']
        duraciones_complejas = [
            [1.5, 0.5], [0.75, 0.25, 0.5], [0.25, 0.25, 0.25, 0.25, 0.5],
            [1.0, 0.333, 0.333, 0.334], [0.5, 0.25, 0.125, 0.125]
        ]
        
        for _ in range(8):
            m = stream.Measure()
            current_duration = 0
            while current_duration < compas.barDuration.quarterLength:
                dur = random.choice(duraciones_complejas)
                for d in dur:
                    if current_duration + d > compas.barDuration.quarterLength:
                        d = compas.barDuration.quarterLength - current_duration
                    n = note.Note('C4', quarterLength=d)
                    m.append(n)
                    current_duration += d
                    if current_duration >= compas.barDuration.quarterLength:
                        break
            parte.append(m)
        
        parte.insert(0, tempo.MetronomeMark(number=config['tempo'] - 20))
        return parte

    def _generar_acordes(self, config):
        parte = stream.Part()
        acordes = {
            'major': ['I', 'IV', 'V'],
            'minor': ['i', 'iv', 'V']
        }[config['tonalidad'].mode]
        
        for _ in range(8):
            grado = random.choice(acordes)
            acorde = config['tonalidad'].chordFromRoman(grado)
            for n in acorde:
                chord_obj = chord.Chord(acorde, quarterLength=1.0)
                chord_obj.addLyric(grado)
                parte.append(chord_obj)
        
        parte.insert(0, config['time_signature'])
        parte.insert(0, config['tempo'])
        return parte
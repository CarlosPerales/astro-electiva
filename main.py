"""
═══════════════════════════════════════════════════════════════════════════════
API ASTROLOGÍA ELECTIVA EMPRESARIAL v1.0
═══════════════════════════════════════════════════════════════════════════════

AUTOR: Carlos [Tu Apellido]
METODOLOGÍA: Vivian E. Robson - "Electional Astrology" (1937)
MOTOR: Swiss Ephemeris (precisión astronómica)

DESCRIPCIÓN:
    Esta API calcula las mejores fechas para lanzar proyectos empresariales
    basándose en las reglas clásicas de la astrología electiva.

REGLAS PRINCIPALES (traducidas del libro de Robson):

    CAPÍTULO 3 - LA LUNA:
    - "Los asuntos progresan más rápido y exitosamente cuando la Luna 
       está creciendo en luz" (pág. 13)
    - "La peor posición zodiacal para la Luna es la Via Combusta, 
       que se extiende desde 15° Libra hasta 15° Escorpio" (pág. 15)
    - "Cuando está vacía de curso... no forma aspectos antes de cambiar 
       de signo" (pág. 15)

    CAPÍTULO 4 - ASPECTOS LUNARES:
    - "Es preferible que la Luna no tenga ningún aspecto con los maléficos"
    - "Evitar aplicación lunar a planetas retrógrados" (pág. 15)
    
    CAPÍTULO 8 - COMERCIO Y FINANZAS:
    - "Mantener Luna y Mercurio libres de conjunción o aspecto con Marte"
    - "Luna en Tauro, Cáncer, Virgo, Capricornio o Piscis es favorable"

ESTRUCTURA DEL CÓDIGO:
    1. Constantes astrológicas
    2. Modelos de datos (Pydantic)
    3. Funciones de cálculo astronómico
    4. Sistema de puntuación (scoring)
    5. Endpoints de la API

MANTENIMIENTO:
    - Los pesos del scoring están en la función calcular_puntaje_fecha()
    - Las reglas de Robson están documentadas con número de página
    - Puedes ajustar los valores según tu experiencia
═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import swisseph as swe
import math

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA APLICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Astrología Electiva API",
    version="1.0.0",
    description="API para calcular fechas óptimas de lanzamiento empresarial"
)

# Permitir conexiones desde cualquier origen (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES ASTROLÓGICAS
# ═══════════════════════════════════════════════════════════════════════════════

# Planetas con sus códigos de Swiss Ephemeris
PLANETAS = {
    swe.SUN: "Sol",
    swe.MOON: "Luna", 
    swe.MERCURY: "Mercurio",
    swe.VENUS: "Venus",
    swe.MARS: "Marte",
    swe.JUPITER: "Júpiter",
    swe.SATURN: "Saturno",
    swe.URANUS: "Urano",
    swe.NEPTUNE: "Neptuno"
}

# Signos zodiacales en orden
SIGNOS = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"
]

# Días de la semana en español
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Meses en español (índice 0 vacío para que enero sea índice 1)
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# ═══════════════════════════════════════════════════════════════════════════════
# HORAS PLANETARIAS (Robson Capítulo 5)
# ═══════════════════════════════════════════════════════════════════════════════
# "El día astrológico comienza en el momento exacto del amanecer local"
# "La primera hora planetaria está regida por el planeta que rige el día"

# Orden caldeo de los planetas (para calcular horas planetarias)
ORDEN_HORAS_PLANETARIAS = ["Saturno", "Júpiter", "Marte", "Sol", "Venus", "Mercurio", "Luna"]

# Regente de cada día de la semana
REGENTES_DIAS = {
    0: "Luna",      # Lunes (Monday = Moon day)
    1: "Marte",     # Martes (Tuesday = Tiw/Mars day)
    2: "Mercurio",  # Miércoles (Wednesday = Woden/Mercury day)
    3: "Júpiter",   # Jueves (Thursday = Thor/Jupiter day)
    4: "Venus",     # Viernes (Friday = Freya/Venus day)
    5: "Saturno",   # Sábado (Saturday = Saturn day)
    6: "Sol"        # Domingo (Sunday = Sun day)
}

# ═══════════════════════════════════════════════════════════════════════════════
# VIA COMBUSTA (Robson pág. 15)
# ═══════════════════════════════════════════════════════════════════════════════
# "La peor posición zodiacal para la Luna es la Via Combusta,
#  que se extiende desde 15° Libra hasta 15° Escorpio.
#  Es desfavorable para todo, especialmente para comprar y vender,
#  viajar, y matrimonio."

VIA_COMBUSTA_INICIO = 195.0   # 15° Libra (180° + 15°)
VIA_COMBUSTA_FIN = 225.0      # 15° Escorpio (210° + 15°)

# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS DE PROYECTO Y SUS SIGNIFICADORES (Robson Cap. 8 y 9)
# ═══════════════════════════════════════════════════════════════════════════════
# Cada tipo de proyecto tiene casas y planetas que lo rigen

TIPOS_PROYECTO = {
    "negocio": {
        "casas": [1, 2, 10, 11],                           # Casas relevantes
        "planetas": [swe.JUPITER, swe.SUN, swe.MERCURY],   # Planetas significadores
        "descripcion": "Negocio / Empresa"
    },
    "tienda": {
        "casas": [2, 7, 10],
        "planetas": [swe.MERCURY, swe.JUPITER, swe.VENUS],
        "descripcion": "Tienda / Comercio"
    },
    "contrato": {
        "casas": [7, 3, 9],
        "planetas": [swe.MERCURY, swe.JUPITER],
        "descripcion": "Contrato / Acuerdo"
    },
    "inversion": {
        "casas": [2, 5, 8, 11],
        "planetas": [swe.JUPITER, swe.VENUS],
        "descripcion": "Inversión"
    },
    "lanzamiento": {
        "casas": [1, 10, 11],
        "planetas": [swe.SUN, swe.JUPITER, swe.MARS],
        "descripcion": "Lanzamiento de Producto"
    },
    "sociedad": {
        "casas": [7, 11],
        "planetas": [swe.JUPITER, swe.VENUS],
        "descripcion": "Sociedad / Partnership"
    },
    "web": {
        "casas": [3, 9, 11],
        "planetas": [swe.MERCURY, swe.URANUS],
        "descripcion": "Sitio Web / App"
    },
    "otro": {
        "casas": [1, 10, 11],
        "planetas": [swe.JUPITER, swe.VENUS],
        "descripcion": "Proyecto General"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# PESOS DEL SISTEMA DE PUNTUACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
# Estos valores determinan cuántos puntos suma o resta cada factor.
# Puedes ajustarlos según tu experiencia.
# El puntaje base es 50 (neutro).

PESOS = {
    # LUNA - Fase (Robson Cap. 3, pág. 13)
    "luna_creciente": +15,          # "Matters progress more speedily"
    "luna_menguante": -10,          # Menos favorable para iniciar
    
    # LUNA - Problemas graves (Robson Cap. 3, pág. 15)
    "luna_vacia_curso": -25,        # "Nothing will come of the matter"
    "via_combusta": -20,            # "Worst zodiacal position"
    
    # MERCURIO (Robson Cap. 4, pág. 15)
    "mercurio_retrogrado": -20,     # "Anything begun will quickly fail"
    "mercurio_directo": +10,        # Favorable para contratos
    
    # ASPECTOS LUNA-BENÉFICOS (Robson Cap. 4, pág. 14)
    "luna_conjuncion_jupiter": +15,
    "luna_trigono_jupiter": +15,
    "luna_sextil_jupiter": +12,
    "luna_conjuncion_venus": +12,
    "luna_trigono_venus": +12,
    "luna_sextil_venus": +10,
    
    # ASPECTOS LUNA-MALÉFICOS (Robson Cap. 4, pág. 14)
    "luna_cuadratura_marte": -15,   # "Afflictions from Mars cause discord"
    "luna_oposicion_marte": -15,
    "luna_conjuncion_marte": -12,
    "luna_cuadratura_saturno": -15, # "Affliction from Saturn causes delay"
    "luna_oposicion_saturno": -15,
    "luna_conjuncion_saturno": -12,
    
    # SIGNO LUNAR (Robson Cap. 8, pág. 34)
    "luna_signo_favorable": +8,     # Tauro, Cáncer, Virgo, Capricornio, Piscis
    
    # SOL-LUNA (Robson Cap. 3, pág. 13)
    "sol_trigono_luna": +10,        # "Good aspect is excellent foundation"
    "sol_sextil_luna": +8,
}

# ═══════════════════════════════════════════════════════════════════════════════
# MODELOS DE DATOS (Pydantic)
# ═══════════════════════════════════════════════════════════════════════════════

class SolicitudElectiva(BaseModel):
    """Datos de entrada para calcular fechas electivas"""
    nombre: str
    fecha_nacimiento: Optional[str] = None   # Formato: YYYY-MM-DD
    hora_nacimiento: Optional[str] = None    # Formato: HH:MM
    ciudad_nacimiento: Optional[str] = None
    tipo_proyecto: str                        # Ver TIPOS_PROYECTO
    fecha_desde: str                          # Formato: YYYY-MM-DD
    fecha_hasta: str                          # Formato: YYYY-MM-DD
    ubicacion: Optional[str] = "Lima, Peru"
    latitud: Optional[float] = -12.0464       # Default: Lima
    longitud: Optional[float] = -77.0428

class ResultadoFecha(BaseModel):
    """Resultado del análisis de una fecha"""
    dia: int
    dia_semana: str
    mes: str
    fecha_completa: str
    puntaje: int
    nivel: str                                # excellent, good, caution, avoid
    factores: List[Dict[str, str]]
    mejores_horas: List[str]

class RespuestaElectiva(BaseModel):
    """Respuesta completa del cálculo"""
    estado: str
    nombre: str
    tipo_proyecto: str
    descripcion_tipo: str
    fechas: List[ResultadoFecha]
    reglas_aplicadas: List[str]

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CÁLCULO ASTRONÓMICO
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_dia_juliano(anio: int, mes: int, dia: int, hora: float = 12.0) -> float:
    """
    Convierte una fecha del calendario gregoriano a día juliano.
    El día juliano es el sistema de fechas usado en astronomía.
    
    Args:
        anio: Año (ej: 2026)
        mes: Mes (1-12)
        dia: Día del mes
        hora: Hora decimal (12.0 = mediodía)
    
    Returns:
        Día juliano como número flotante
    """
    return swe.julday(anio, mes, dia, hora)


def obtener_posicion_planeta(dia_juliano: float, planeta: int) -> Dict[str, Any]:
    """
    Obtiene la posición de un planeta en un momento dado.
    
    Args:
        dia_juliano: Fecha en formato día juliano
        planeta: Código del planeta (swe.SUN, swe.MOON, etc.)
    
    Returns:
        Diccionario con: longitud, signo, grado, velocidad, retrógrado
    """
    try:
        posicion, _ = swe.calc_ut(dia_juliano, planeta)
        longitud = posicion[0]
        
        # Calcular signo y grado dentro del signo
        numero_signo = int(longitud / 30)
        grado = longitud % 30
        
        # La velocidad indica si está retrógrado (negativa = retrógrado)
        velocidad = posicion[3] if len(posicion) > 3 else 0
        
        return {
            "longitud": longitud,
            "signo": SIGNOS[numero_signo],
            "numero_signo": numero_signo,
            "grado": grado,
            "velocidad": velocidad,
            "retrogrado": velocidad < 0
        }
    except Exception as e:
        print(f"Error obteniendo posición de planeta {planeta}: {e}")
        return None


def obtener_fase_lunar(dia_juliano: float) -> Dict[str, Any]:
    """
    Calcula la fase de la Luna.
    
    La fase se determina por el ángulo entre el Sol y la Luna:
    - 0° = Luna Nueva
    - 90° = Cuarto Creciente
    - 180° = Luna Llena
    - 270° = Cuarto Menguante
    
    Returns:
        Diccionario con: fase (nombre), creciente (bool), angulo
    """
    sol = obtener_posicion_planeta(dia_juliano, swe.SUN)
    luna = obtener_posicion_planeta(dia_juliano, swe.MOON)
    
    if not sol or not luna:
        return {"fase": "desconocida", "creciente": False}
    
    # Diferencia angular (siempre positiva, 0-360)
    diferencia = (luna["longitud"] - sol["longitud"]) % 360
    
    # Determinar fase
    if diferencia < 45:
        fase = "Nueva"
        creciente = True
    elif diferencia < 90:
        fase = "Creciente"
        creciente = True
    elif diferencia < 135:
        fase = "Cuarto Creciente"
        creciente = True
    elif diferencia < 180:
        fase = "Gibosa Creciente"
        creciente = True
    elif diferencia < 225:
        fase = "Llena"
        creciente = False
    elif diferencia < 270:
        fase = "Gibosa Menguante"
        creciente = False
    elif diferencia < 315:
        fase = "Cuarto Menguante"
        creciente = False
    else:
        fase = "Menguante"
        creciente = False
    
    return {
        "fase": fase,
        "creciente": creciente,
        "angulo": diferencia
    }


def esta_luna_vacia_de_curso(dia_juliano: float) -> bool:
    """
    Verifica si la Luna está vacía de curso (Void of Course).
    
    Robson (pág. 15): "Cuando está vacía de curso, es decir, cuando no forma
    ningún aspecto antes de entrar en otro signo."
    
    Simplificación: Si la Luna está en los últimos 3° del signo
    y no tiene aspectos aplicativos, está VOC.
    
    Returns:
        True si la Luna está vacía de curso
    """
    luna = obtener_posicion_planeta(dia_juliano, swe.MOON)
    if not luna:
        return False
    
    grado_en_signo = luna["grado"]
    
    # Si está en los últimos 3 grados del signo
    if grado_en_signo > 27:
        # Verificar si hay aspectos aplicativos a otros planetas
        tiene_aspecto_aplicativo = False
        
        for planeta in [swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]:
            pos_planeta = obtener_posicion_planeta(dia_juliano, planeta)
            if pos_planeta:
                diferencia = abs(luna["longitud"] - pos_planeta["longitud"])
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Aspectos mayores con orbe de 3°
                for aspecto in [0, 60, 90, 120, 180]:
                    if abs(diferencia - aspecto) < 3:
                        if luna["velocidad"] > 0:  # Aplicativo
                            tiene_aspecto_aplicativo = True
                            break
        
        return not tiene_aspecto_aplicativo
    
    return False


def esta_en_via_combusta(longitud: float) -> bool:
    """
    Verifica si una posición está en la Via Combusta.
    
    Robson (pág. 15): "La Via Combusta se extiende desde 15° Libra
    hasta 15° Escorpio. Es desfavorable para todo."
    
    Args:
        longitud: Posición en grados eclípticos (0-360)
    
    Returns:
        True si está en Via Combusta
    """
    return VIA_COMBUSTA_INICIO <= longitud <= VIA_COMBUSTA_FIN


def calcular_aspecto(dia_juliano: float, planeta1: int, planeta2: int) -> Optional[Dict[str, Any]]:
    """
    Calcula el aspecto entre dos planetas.
    
    Aspectos mayores:
    - Conjunción: 0° (orbe 8°)
    - Sextil: 60° (orbe 6°)
    - Cuadratura: 90° (orbe 7°)
    - Trígono: 120° (orbe 8°)
    - Oposición: 180° (orbe 8°)
    
    Returns:
        Diccionario con: aspecto, simbolo, angulo, orbe
        None si no hay aspecto
    """
    pos1 = obtener_posicion_planeta(dia_juliano, planeta1)
    pos2 = obtener_posicion_planeta(dia_juliano, planeta2)
    
    if not pos1 or not pos2:
        return None
    
    diferencia = abs(pos1["longitud"] - pos2["longitud"])
    if diferencia > 180:
        diferencia = 360 - diferencia
    
    # Definición de aspectos: ángulo -> (nombre, símbolo, orbe permitido)
    aspectos = {
        0: ("Conjunción", "☌", 8),
        60: ("Sextil", "⚹", 6),
        90: ("Cuadratura", "□", 7),
        120: ("Trígono", "△", 8),
        180: ("Oposición", "☍", 8)
    }
    
    for angulo, (nombre, simbolo, orbe) in aspectos.items():
        if abs(diferencia - angulo) <= orbe:
            return {
                "aspecto": nombre,
                "simbolo": simbolo,
                "angulo": angulo,
                "orbe": abs(diferencia - angulo),
                "exacto": abs(diferencia - angulo) < 1
            }
    
    return None


def obtener_horas_planetarias(fecha: datetime, latitud: float, longitud: float) -> List[Dict[str, Any]]:
    """
    Calcula las horas planetarias del día.
    
    Robson (Cap. 5): "El día astrológico comienza en el momento exacto
    del amanecer local. La primera hora está regida por el planeta
    que rige el día."
    
    Simplificación: Dividimos el día en 12 horas diurnas (6am-6pm)
    y asignamos planetas según el orden caldeo.
    
    Returns:
        Lista de horas con su planeta regente
    """
    dia_semana = fecha.weekday()
    regente_dia = REGENTES_DIAS[dia_semana]
    
    # Encontrar índice del regente en el orden caldeo
    indice_inicio = ORDEN_HORAS_PLANETARIAS.index(regente_dia)
    
    horas = []
    
    # Generar 12 horas diurnas
    for i in range(12):
        indice_planeta = (indice_inicio + i) % 7
        planeta = ORDEN_HORAS_PLANETARIAS[indice_planeta]
        hora_inicio = 6 + i
        
        # Júpiter, Venus y Sol son favorables
        favorable = planeta in ["Júpiter", "Venus", "Sol"]
        
        horas.append({
            "hora_inicio": f"{hora_inicio:02d}:00",
            "hora_fin": f"{hora_inicio+1:02d}:00",
            "planeta": planeta,
            "favorable": favorable,
            "tipo": "diurna"
        })
    
    return horas

# ═══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE PUNTUACIÓN (SCORING)
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_puntaje_fecha(dia_juliano: float, tipo_proyecto: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Calcula el puntaje de una fecha para un tipo de proyecto.
    
    METODOLOGÍA:
    - Puntaje base: 50 (neutro)
    - Se suman/restan puntos según las reglas de Robson
    - Puntaje final: 0-100
    
    NIVELES:
    - 80-100: Excelente
    - 60-79: Buena
    - 40-59: Precaución
    - 0-39: Evitar
    
    Returns:
        Diccionario con: puntaje, nivel, factores
    """
    puntaje = 50  # Puntaje base neutro
    factores = []
    
    # ═══════════════════════════════════════════════════════════════════════
    # Obtener posiciones planetarias
    # ═══════════════════════════════════════════════════════════════════════
    luna = obtener_posicion_planeta(dia_juliano, swe.MOON)
    sol = obtener_posicion_planeta(dia_juliano, swe.SUN)
    mercurio = obtener_posicion_planeta(dia_juliano, swe.MERCURY)
    venus = obtener_posicion_planeta(dia_juliano, swe.VENUS)
    marte = obtener_posicion_planeta(dia_juliano, swe.MARS)
    jupiter = obtener_posicion_planeta(dia_juliano, swe.JUPITER)
    saturno = obtener_posicion_planeta(dia_juliano, swe.SATURN)
    
    fase_lunar = obtener_fase_lunar(dia_juliano)
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 1: FASE LUNAR (Robson Cap. 3, pág. 13)
    # "Los asuntos progresan mucho más rápido y exitosamente si se inician
    #  cuando la Luna está creciendo en luz"
    # ═══════════════════════════════════════════════════════════════════════
    
    if fase_lunar["creciente"]:
        puntaje += PESOS["luna_creciente"]
        factores.append({
            "texto": f"☽ Luna {fase_lunar['fase']}",
            "tipo": "positive"
        })
    else:
        puntaje += PESOS["luna_menguante"]
        factores.append({
            "texto": f"☽ Luna {fase_lunar['fase']}",
            "tipo": "negative"
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 2: LUNA VACÍA DE CURSO (Robson Cap. 3, pág. 15)
    # "Cuando está vacía de curso... no forma aspectos antes de cambiar de signo.
    #  Nada resultará del asunto."
    # ═══════════════════════════════════════════════════════════════════════
    
    if esta_luna_vacia_de_curso(dia_juliano):
        puntaje += PESOS["luna_vacia_curso"]
        factores.append({
            "texto": "☽ Luna Vacía de Curso",
            "tipo": "negative"
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 3: VIA COMBUSTA (Robson Cap. 3, pág. 15)
    # "La peor posición zodiacal para la Luna es la Via Combusta,
    #  que se extiende desde 15° Libra hasta 15° Escorpio"
    # ═══════════════════════════════════════════════════════════════════════
    
    if luna and esta_en_via_combusta(luna["longitud"]):
        puntaje += PESOS["via_combusta"]
        factores.append({
            "texto": f"☽ Via Combusta ({luna['grado']:.0f}° {luna['signo']})",
            "tipo": "negative"
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 4: MERCURIO RETRÓGRADO (Robson Cap. 4, pág. 15)
    # "Es muy importante evitar la aplicación lunar a la conjunción o aspecto
    #  de cualquier planeta retrógrado, porque cualquier cosa iniciada en tal
    #  momento fallará rápidamente"
    # ═══════════════════════════════════════════════════════════════════════
    
    if mercurio and mercurio["retrogrado"]:
        puntaje += PESOS["mercurio_retrogrado"]
        factores.append({
            "texto": "☿ Mercurio Retrógrado ℞",
            "tipo": "negative"
        })
    else:
        puntaje += PESOS["mercurio_directo"]
        factores.append({
            "texto": "☿ Mercurio Directo",
            "tipo": "positive"
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 5: ASPECTOS LUNA-JÚPITER/VENUS (Robson Cap. 4, pág. 14)
    # "Prosperidad y éxito siguen a la Luna en buen aspecto o conjunción
    #  con Júpiter o Venus"
    # ═══════════════════════════════════════════════════════════════════════
    
    aspecto_luna_jupiter = calcular_aspecto(dia_juliano, swe.MOON, swe.JUPITER)
    if aspecto_luna_jupiter:
        if aspecto_luna_jupiter["aspecto"] in ["Conjunción", "Trígono", "Sextil"]:
            peso_key = f"luna_{aspecto_luna_jupiter['aspecto'].lower()}_jupiter"
            puntaje += PESOS.get(peso_key, 12)
            factores.append({
                "texto": f"☽ {aspecto_luna_jupiter['simbolo']} ♃ ({aspecto_luna_jupiter['aspecto']})",
                "tipo": "positive"
            })
        elif aspecto_luna_jupiter["aspecto"] in ["Cuadratura", "Oposición"]:
            puntaje -= 5
            factores.append({
                "texto": f"☽ {aspecto_luna_jupiter['simbolo']} ♃ ({aspecto_luna_jupiter['aspecto']})",
                "tipo": "neutral"
            })
    
    aspecto_luna_venus = calcular_aspecto(dia_juliano, swe.MOON, swe.VENUS)
    if aspecto_luna_venus:
        if aspecto_luna_venus["aspecto"] in ["Conjunción", "Trígono", "Sextil"]:
            puntaje += 10
            factores.append({
                "texto": f"☽ {aspecto_luna_venus['simbolo']} ♀ ({aspecto_luna_venus['aspecto']})",
                "tipo": "positive"
            })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 6: ASPECTOS LUNA-MARTE/SATURNO (Robson Cap. 4, pág. 14)
    # "Es preferible como regla que la Luna no tenga ningún aspecto
    #  con los maléficos"
    # ═══════════════════════════════════════════════════════════════════════
    
    aspecto_luna_marte = calcular_aspecto(dia_juliano, swe.MOON, swe.MARS)
    if aspecto_luna_marte:
        if aspecto_luna_marte["aspecto"] in ["Conjunción", "Cuadratura", "Oposición"]:
            puntaje += PESOS["luna_cuadratura_marte"]
            factores.append({
                "texto": f"☽ {aspecto_luna_marte['simbolo']} ♂ ({aspecto_luna_marte['aspecto']})",
                "tipo": "negative"
            })
    
    aspecto_luna_saturno = calcular_aspecto(dia_juliano, swe.MOON, swe.SATURN)
    if aspecto_luna_saturno:
        if aspecto_luna_saturno["aspecto"] in ["Conjunción", "Cuadratura", "Oposición"]:
            puntaje += PESOS["luna_cuadratura_saturno"]
            factores.append({
                "texto": f"☽ {aspecto_luna_saturno['simbolo']} ♄ ({aspecto_luna_saturno['aspecto']})",
                "tipo": "negative"
            })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 7: SIGNO LUNAR FAVORABLE (Robson Cap. 8, pág. 34)
    # "La Luna en Tauro, Cáncer, Virgo, Capricornio o Piscis es favorable
    #  para comprar y vender"
    # ═══════════════════════════════════════════════════════════════════════
    
    signos_favorables = ["Tauro", "Cáncer", "Virgo", "Capricornio", "Piscis"]
    if luna and luna["signo"] in signos_favorables:
        puntaje += PESOS["luna_signo_favorable"]
        factores.append({
            "texto": f"☽ Luna en {luna['signo']}",
            "tipo": "positive"
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGLA 8: ASPECTO SOL-LUNA (Robson Cap. 3, pág. 13)
    # "Un buen aspecto entre la Luna y el Sol es una excelente base
    #  para el éxito, y mejorará cualquier elección"
    # ═══════════════════════════════════════════════════════════════════════
    
    aspecto_sol_luna = calcular_aspecto(dia_juliano, swe.SUN, swe.MOON)
    if aspecto_sol_luna:
        if aspecto_sol_luna["aspecto"] in ["Trígono", "Sextil"]:
            puntaje += PESOS["sol_trigono_luna"]
            factores.append({
                "texto": f"☉ {aspecto_sol_luna['simbolo']} ☽",
                "tipo": "positive"
            })
    
    # ═══════════════════════════════════════════════════════════════════════
    # Asegurar que el puntaje esté entre 0 y 100
    # ═══════════════════════════════════════════════════════════════════════
    
    puntaje = max(0, min(100, puntaje))
    
    # Determinar nivel según puntaje
    if puntaje >= 80:
        nivel = "excellent"
    elif puntaje >= 60:
        nivel = "good"
    elif puntaje >= 40:
        nivel = "caution"
    else:
        nivel = "avoid"
    
    return {
        "puntaje": puntaje,
        "nivel": nivel,
        "factores": factores
    }


def obtener_mejores_horas(fecha: datetime, lat: float, lon: float) -> List[str]:
    """
    Obtiene las mejores horas del día para iniciar el proyecto.
    
    Las horas de Júpiter, Venus y Sol son las más favorables.
    
    Returns:
        Lista de strings con las mejores horas
    """
    horas = obtener_horas_planetarias(fecha, lat, lon)
    mejores = []
    
    for h in horas:
        if h["favorable"] and h["tipo"] == "diurna":
            mejores.append(f"{h['hora_inicio']} - {h['hora_fin']} (Hora de {h['planeta']})")
    
    return mejores[:3]  # Máximo 3 horas

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE LA API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def raiz():
    """Endpoint raíz con información de la API"""
    return {
        "api": "Astrología Electiva Empresarial",
        "version": "1.0.0",
        "metodologia": "Vivian E. Robson",
        "motor": "Swiss Ephemeris",
        "endpoints": {
            "/calcular": "POST - Calcular mejores fechas",
            "/horas-planetarias/{fecha}": "GET - Horas planetarias del día",
            "/info-luna/{fecha}": "GET - Información lunar del día"
        }
    }


@app.get("/salud")
def verificar_salud():
    """Verificación de salud de la API"""
    return {"estado": "saludable", "version": "1.0.0"}


@app.post("/calcular", response_model=RespuestaElectiva)
def calcular_electiva(solicitud: SolicitudElectiva):
    """
    Calcula las mejores fechas para lanzar un proyecto.
    
    PARÁMETROS:
    - nombre: Nombre del consultante
    - tipo_proyecto: negocio, tienda, contrato, inversion, lanzamiento, sociedad, web, otro
    - fecha_desde: Fecha de inicio del rango (YYYY-MM-DD)
    - fecha_hasta: Fecha de fin del rango (YYYY-MM-DD)
    - ubicacion: Ciudad donde se lanzará (opcional)
    - latitud/longitud: Coordenadas (opcional)
    
    RETORNA:
    - Lista de las 10 mejores fechas ordenadas por puntaje
    - Factores astrológicos de cada fecha
    - Mejores horas para cada día
    """
    try:
        # Parsear fechas
        fecha_desde = datetime.strptime(solicitud.fecha_desde, "%Y-%m-%d")
        fecha_hasta = datetime.strptime(solicitud.fecha_hasta, "%Y-%m-%d")
        
        # Limitar rango a 60 días máximo (por rendimiento)
        if (fecha_hasta - fecha_desde).days > 60:
            fecha_hasta = fecha_desde + timedelta(days=60)
        
        # Obtener información del tipo de proyecto
        info_proyecto = TIPOS_PROYECTO.get(
            solicitud.tipo_proyecto, 
            TIPOS_PROYECTO["otro"]
        )
        
        resultados = []
        fecha_actual = fecha_desde
        
        # Analizar cada día del rango
        while fecha_actual <= fecha_hasta:
            # Calcular día juliano para mediodía
            dia_juliano = obtener_dia_juliano(
                fecha_actual.year,
                fecha_actual.month,
                fecha_actual.day,
                12.0
            )
            
            # Calcular puntaje de la fecha
            analisis = calcular_puntaje_fecha(
                dia_juliano, 
                solicitud.tipo_proyecto,
                solicitud.latitud,
                solicitud.longitud
            )
            
            # Obtener mejores horas
            mejores_horas = obtener_mejores_horas(
                fecha_actual, 
                solicitud.latitud, 
                solicitud.longitud
            )
            
            # Si el nivel es "avoid", no mostrar horas
            if analisis["nivel"] == "avoid":
                mejores_horas = []
            elif analisis["nivel"] == "caution":
                mejores_horas = ["⚠️ Si es urgente, evitar horas de Marte y Saturno"]
            
            resultados.append(ResultadoFecha(
                dia=fecha_actual.day,
                dia_semana=DIAS_SEMANA[fecha_actual.weekday()],
                mes=f"{MESES[fecha_actual.month]} {fecha_actual.year}",
                fecha_completa=fecha_actual.strftime("%Y-%m-%d"),
                puntaje=analisis["puntaje"],
                nivel=analisis["nivel"],
                factores=analisis["factores"],
                mejores_horas=mejores_horas
            ))
            
            fecha_actual += timedelta(days=1)
        
        # Ordenar por puntaje descendente
        resultados.sort(key=lambda x: x.puntaje, reverse=True)
        
        # Tomar las mejores 10 fechas
        mejores_resultados = resultados[:10]
        
        # Reglas aplicadas (para mostrar al usuario)
        reglas = [
            "✅ Luna creciente - Favorece crecimiento y progreso (Robson pág. 13)",
            "✅ Mercurio directo - Comunicación y contratos claros (Robson pág. 15)",
            "✅ Júpiter/Venus en buen aspecto a Luna - Favorece negocios (Robson pág. 14)",
            "✅ Luna en signos favorables: Tauro, Cáncer, Virgo, etc. (Robson pág. 34)",
            "❌ Evitar Luna vacía de curso - Nada prospera (Robson pág. 15)",
            "❌ Evitar Via Combusta: 15° Libra - 15° Escorpio (Robson pág. 15)",
            "❌ Evitar Mercurio retrógrado - Contratos problemáticos (Robson pág. 15)",
            "❌ Evitar aflicciones Marte/Saturno a Luna - Conflictos (Robson pág. 14)"
        ]
        
        return RespuestaElectiva(
            estado="exito",
            nombre=solicitud.nombre,
            tipo_proyecto=solicitud.tipo_proyecto,
            descripcion_tipo=info_proyecto["descripcion"],
            fechas=mejores_resultados,
            reglas_aplicadas=reglas
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/horas-planetarias/{fecha}")
def obtener_horas_dia(fecha: str, lat: float = -12.0464, lon: float = -77.0428):
    """
    Obtiene las horas planetarias de un día específico.
    
    PARÁMETROS:
    - fecha: Fecha en formato YYYY-MM-DD
    - lat: Latitud (default: Lima)
    - lon: Longitud (default: Lima)
    """
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        horas = obtener_horas_planetarias(fecha_dt, lat, lon)
        
        return {
            "fecha": fecha,
            "dia_semana": DIAS_SEMANA[fecha_dt.weekday()],
            "regente_dia": REGENTES_DIAS[fecha_dt.weekday()],
            "horas": horas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/info-luna/{fecha}")
def obtener_info_luna(fecha: str):
    """
    Obtiene información lunar detallada de un día específico.
    
    PARÁMETROS:
    - fecha: Fecha en formato YYYY-MM-DD
    """
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        dia_juliano = obtener_dia_juliano(fecha_dt.year, fecha_dt.month, fecha_dt.day, 12.0)
        
        luna = obtener_posicion_planeta(dia_juliano, swe.MOON)
        fase = obtener_fase_lunar(dia_juliano)
        vacia_curso = esta_luna_vacia_de_curso(dia_juliano)
        via_combusta = esta_en_via_combusta(luna["longitud"]) if luna else False
        
        return {
            "fecha": fecha,
            "posicion_luna": luna,
            "fase": fase,
            "vacia_de_curso": vacia_curso,
            "via_combusta": via_combusta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("ASTROLOGÍA ELECTIVA EMPRESARIAL API v1.0")
    print("Metodología: Vivian E. Robson")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)

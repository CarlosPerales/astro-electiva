# 🔮 Astrología Electiva Empresarial API

Motor de cálculo astrológico para encontrar las mejores fechas de lanzamiento de proyectos empresariales.

## 📚 Metodología

Basado en **"Electional Astrology"** de **Vivian E. Robson** (1937) - el libro clásico de referencia en astrología electiva.

## 🚀 Deploy

**Railway:** https://astro-electiva.up.railway.app (próximamente)

## 📡 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info de la API |
| GET | `/salud` | Health check |
| POST | `/calcular` | Calcular mejores fechas |
| GET | `/horas-planetarias/{fecha}` | Horas planetarias del día |
| GET | `/info-luna/{fecha}` | Información lunar |

## 📊 Ejemplo de Uso

```bash
curl -X POST "https://tu-api.railway.app/calcular" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Carlos",
    "tipo_proyecto": "negocio",
    "fecha_desde": "2026-03-01",
    "fecha_hasta": "2026-03-31"
  }'
```

## 🎯 Tipos de Proyecto

- `negocio` - Negocio / Empresa
- `tienda` - Tienda / Comercio  
- `contrato` - Contrato / Acuerdo
- `inversion` - Inversión
- `lanzamiento` - Lanzamiento de Producto
- `sociedad` - Sociedad / Partnership
- `web` - Sitio Web / App
- `otro` - Proyecto General

## 📈 Sistema de Puntuación

| Puntaje | Nivel | Color |
|---------|-------|-------|
| 80-100 | Excelente | 🟢 |
| 60-79 | Buena | 🟡 |
| 40-59 | Precaución | 🟠 |
| 0-39 | Evitar | 🔴 |

## 🔧 Stack Técnico

- **Backend:** Python + FastAPI
- **Motor:** Swiss Ephemeris (pyswisseph)
- **Deploy:** Railway / Render

## 📖 Referencias

- Robson, V.E. (1937). *Electional Astrology*. Canopus Publications.

## 👤 Autor

Carlos Perales - Data Engineer & Astrólogo UILA

---

**Proyectos relacionados:**
- [astro-api](https://github.com/CarlosPerales/astro-api) - Revolución Solar (Discepolo)

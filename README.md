# 🕵️ Instagram Personality Profiler (Big Five - OCEAN)

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Este sistema es una plataforma avanzada de **Psicometría Digital** diseñada para realizar perfiles psicológicos basados en el modelo de los **Cinco Grandes (OCEAN)**. A través de la extracción de datos públicos de Instagram y el uso de Inteligencia Artificial multimodal, el sistema transforma la actividad digital en métricas de personalidad accionables.

---

## 📊 Alcance de la Extracción

El sistema realiza una recolección profunda de datos para asegurar un análisis psicológico preciso:

*   **Publicaciones (Posts):** Extrae por defecto los últimos **20 posts** del perfil (configurable en `settings.py`).
*   **Comentarios:** Obtiene una muestra de los últimos **10 comentarios** por cada publicación para analizar el engagement y la interacción social.
*   **Información del Perfil:**
    *   Identidad: Nombre completo, nombre de usuario y biografía (Bio).
    *   Estadísticas: Número de **seguidores**, **seguidos** (following) y total de publicaciones.
    *   Estado: Verificación de cuenta, si es cuenta de empresa (business) y si es privada.
    *   Multimedia: URL de la foto de perfil en alta resolución.
*   **Metadatos de Posts:** Timestamps, ubicación geográfica (si está disponible), hashtags, menciones y conteo de likes.

## ⚙️ Arquitectura de Extracción Híbrida

El sistema no depende únicamente de Playwright; utiliza un enfoque híbrido para maximizar la eficiencia y reducir la detección:

1.  **Playwright (Fase de Autenticación):** Se utiliza exclusivamente para abrir un navegador real, inyectar las cookies de sesión y validar el acceso. Su función principal es extraer metadatos técnicos volátiles como el `X-IG-App-ID` y asegurar que la sesión sea válida antes de iniciar la carga masiva.
2.  **Requests (Fase de Extracción Intensiva):** El **Cliente HTTP personalizado** está construido sobre la potente librería **`requests`** de Python. Una vez que Playwright obtiene la sesión, ésta se transfiere a un objeto `requests.Session`.
    *   **¿Por qué?** Es mucho más rápido, consume menos memoria que un navegador completo y permite un control total sobre los encabezados (`headers`) de bajo nivel.
    *   **Simulación Humana:** Utiliza **`fake-useragent`** para rotar identidades de navegador y **`Tenacity`** para manejar reintentos automáticos ante micro-cortes o límites de cuota.

---

## 🤖 Uso Estratégico de Inteligencia Artificial

El sistema está diseñado para ser agnóstico al proveedor, pero su configuración óptima aprovecha lo mejor de dos mundos:

*   **Google Gemini (Visión y Contexto):** Se utiliza principalmente como el "ojo" del sistema. Gracias a su capacidad multimodal nativa, procesa las imágenes de los posts para identificar escenas, objetos, emociones y deducir variables demográficas (edad, ocupación, país) analizando la estética visual del perfil.
*   **Groq - Llama 3.3 (Razonamiento Psicológico):** Se ocupa del procesamiento de lenguaje natural (NLP) pesado. Toma todo el resumen generado (textos de captions + análisis visual de Gemini + comentarios) y realiza la inferencia final del modelo **OCEAN**, actuando como el psicólogo que interpreta los datos consolidados.

---

## 🛠️ Stack Tecnológico Detallado

*   **Core:** Python 3.10+
*   **Web Automation:** Playwright (Gestión de sesión).
*   **HTTP Engine:** Requests + Custom Headers (Extracción de datos).
*   **IA & NLP:** Gemini SDK (Google) & Groq SDK (Llama 3.2/3.3).
*   **Persistencia:** MongoDB Atlas (Nube) y JSON (Local).
*   **Reportes:** FPDF2 (Generación de PDF institucional).
*   **Resiliencia:** Tenacity (Retries) y Logging avanzado.

---

## 💾 Almacenamiento y Salida

El sistema garantiza que la información nunca se pierda:

*   **Local (JSON):** Genera un archivo `instagram_data.json` como backup inmediato con toda la información cruda y analizada.
*   **Nube (MongoDB Atlas):** Persiste los análisis en una base de datos NoSQL, permitiendo mantener un histórico de perfiles consultados.
*   **Generación de Reportes (PDF):**
    *   El sistema utiliza la librería `FPDF2` para diseñar un **informe profesional**.
    *   **¿Qué incluye?** Gráficos de barras para cada rasgo OCEAN, interpretaciones detalladas de la IA, resumen de metadatos y una sección de evidencias técnicas.
    *   **Nombre del archivo:** `Reporte_Personalidad_{username}.pdf`.

---

## 📁 Estructura del Proyecto

```text
.
├── Back/
│   ├── application/      # Orquestadores: Generación de PDF y lógica de análisis
│   ├── domain/           # Modelos de datos (Models.py) y lógica pura OCEAN
│   ├── infrastructure/   # Clientes de IA (Gemini/Groq), DB (Mongo) y Scraping
│   ├── config/           # Gestión de variables de entorno y límites
│   └── sessions/         # Almacenamiento de sesiones persistentes
├── README.md             # Guía de presentación
└── DOCUMENTACION_DETALLADA.txt  # Manual técnico exhaustivo
```

---

## 🚀 Guía Rápida de Inicio

1.  **Entorno:** Crea un venv e instala dependencias: `pip install -r Back/requirements.txt`.
2.  **Configuración:** Define tus credenciales en `Back/.env` (Cookies de Instagram, API Keys de IA y URI de Mongo).
3.  **Ejecución:** Corre `python Back/main.py`.

---

**Desarrollado para la materia de Arquitectura de Software.**  
*Este software tiene fines estrictamente académicos y de investigación.*

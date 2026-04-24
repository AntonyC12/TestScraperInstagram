# 🕵️ Instagram Personality Profiler (Big Five - OCEAN)

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Este proyecto es una plataforma de **Psicometría Digital** diseñada para realizar perfiles psicológicos basados en el modelo de los **Cinco Grandes (OCEAN)** a partir de datos públicos de Instagram. Utiliza Inteligencia Artificial de vanguardia para transformar imágenes y textos en métricas de personalidad con fines académicos.

---

## 🚀 Capacidades del Sistema

### 1. Scraping Multicapa (Robusto)
- **Playwright Engine**: Automatización de navegador para bypass de retos JS y recolección de tokens de sesión.
- **Inyección de Cookies**: Mantiene la persistencia de la sesión y reduce el riesgo de bloqueos (429).
- **Extracción Integral**: Recolecta biografía, estadísticas, metadatos de imágenes, captions y engagement.

### 2. Análisis Multimodal (IA)
- **Visión Artificial**: Utiliza Llama 3.2 Vision y Gemini para "entender" qué publica el usuario (escenas, objetos, emociones).
- **Inferencia Psicológica**: Un motor de IA procesa el resumen de vida digital del usuario para calcular puntuaciones en los 5 rasgos de personalidad.

### 3. Ecosistema de Datos Profesional
- **MongoDB Atlas**: Almacenamiento NoSQL en la nube para persistencia y escalabilidad.
- **Informes PDF Institucionales**: Generación automática de informes con visualización de datos, interpretaciones y evidencias.

---

## 🛠️ Stack Tecnológico & Arquitectura

El proyecto sigue los principios de **Clean Architecture**, asegurando que el código sea testeable, escalable y fácil de mantener.

| Capa | Tecnologías |
| :--- | :--- |
| **Dominio** | Python Dataclasses, Lógica de Negocio Pura |
| **Aplicación** | Report Generator (FPDF2), Inferencia OCEAN |
| **Infraestructura** | Playwright, PyMongo, Groq SDK, Gemini SDK |
| **Configuración** | Dotenv, Pydantic/Settings Patterns |

---

## 📁 Estructura del Repositorio

```text
.
├── Back/
│   ├── application/      # Casos de uso y orquestadores
│   ├── domain/           # Entidades y lógica del modelo OCEAN
│   ├── infrastructure/   # Clientes de IA, DB y Scraping
│   ├── config/           # Gestión de variables de entorno
│   ├── sessions/         # Almacenamiento de cookies persistentes
│   └── reports/          # Salida de informes académicos (PDF)
├── README.md             # Guía de presentación
└── DOCUMENTACION_DETALLADA.txt  # Manual técnico exhaustivo
```

---

## ⚙️ Guía de Instalación y Uso

### Requisitos Previos
- Python 3.10 o superior.
- Una cuenta de MongoDB Atlas (Clúster creado).
- API Keys de Google Gemini o Groq.

### Configuración
1. Clona el repositorio y entra al directorio.
2. Crea un entorno virtual: `python -m venv .venv`.
3. Instala las dependencias: `pip install -r Back/requirements.txt`.
4. Configura el archivo `Back/.env` con tus credenciales:
   ```env
   IG_SESSION_ID=tu_session_id
   AI_PROVIDER=groq
   MONGO_URI=mongodb+srv://...
   ```

### Ejecución
```bash
python Back/main.py
```

---

## 📄 Notas de Uso Académico
Este software ha sido desarrollado con el propósito de entender la **identidad digital**. Se recomienda su uso bajo marcos éticos de investigación, respetando siempre la privacidad de los datos y los términos de uso de las plataformas sociales.

---
**Desarrollado con ❤️ para la investigación en Arquitectura de Software y Psicología Digital.**

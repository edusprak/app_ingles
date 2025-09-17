# Aplicación de Traducción Español-Inglés

Esta es una aplicación web desarrollada con Flask que permite practicar traducciones de español a inglés mediante un diccionario XML.

## Características

- 🎯 **Práctica de traducción**: Muestra palabras aleatorias en español para traducir al inglés
- 🔍 **Validación inteligente**: Ignora mayúsculas, minúsculas y tildes
- 💡 **Sistema de ayuda**: Proporciona definiciones y pronunciación
- 🎨 **Diseño moderno**: Interfaz estilizada con Bootstrap
- 📚 **Múltiples acepciones**: Acepta todas las traducciones válidas de una palabra
- 🚀 **Progresión automática**: Cambia automáticamente a nueva palabra al acertar
- ⚡ **Parsing inteligente**: Maneja paréntesis y prefijos "to" en verbos

## Funcionalidades de validación avanzadas

### 1. Manejo de paréntesis
Para traducciones con explicaciones entre paréntesis, acepta tanto la versión completa como la simplificada:
- **Entrada XML**: `translucent (allowing light to pass through scattering it)`
- **Respuestas válidas**: `translucent` y `translucent (allowing light to pass through scattering it)`

### 2. Manejo de verbos con "to"
Para verbos en infinitivo, acepta tanto la forma con "to" como sin "to":
- **Entrada XML**: `to transliterate`
- **Respuestas válidas**: `transliterate` y `to transliterate`

### 3. Casos combinados
Maneja correctamente combinaciones de ambos casos:
- **Entrada XML**: `to run (move quickly), to jog`
- **Respuestas válidas**: `to run (move quickly)`, `to run`, `run (move quickly)`, `run`, `to jog`, `jog`

## Estructura del proyecto

```
app_ingles/
├── app.py                 # Aplicación Flask principal
├── dict_es_en.xml         # Diccionario XML español-inglés
├── templates/
│   └── index.html         # Template HTML con Bootstrap
└── README.md             # Este archivo
```

## Instalación y ejecución

1. **Instalar dependencias**:
   ```bash
   pip install flask
   ```

2. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

3. **Abrir en el navegador**:
   ```
   http://localhost:5000
   ```

## Formato del diccionario XML

El archivo `dict_es_en.xml` debe seguir este formato:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<dic from="es" to="en">
  <l>
    <w>
      <c>palabra_en_español</c>
      <d>translation, another translation (with explanation)</d>
      <t>{tipo} /pronunciación/ (descripción)</t>
    </w>
    <!-- Más palabras... -->
  </l>
</dic>
```

### Elementos XML:

- `<c>`: Palabra en español
- `<d>`: Traducciones en inglés (separadas por comas)
- `<t>`: Definición con tipo de palabra, pronunciación y descripción

## Cómo Usar

1. Abre la aplicación en tu navegador en `http://localhost:5000`
2. Se te presentará una palabra en español para traducir al inglés
3. Escribe tu traducción en el campo de texto
4. Presiona **Enter** o haz clic en "Verificar" para comprobar tu respuesta
5. **Nuevo:** Presiona la **flecha derecha (→)** para ver la respuesta correcta y pasar automáticamente a la siguiente palabra
6. Si la respuesta es correcta, automáticamente se cargará una nueva palabra
7. Si es incorrecta, podrás intentarlo de nuevo o usar la flecha derecha para ver la respuesta
8. Usa el botón "Nueva Palabra" para saltar a otra palabra en cualquier momento
9. Haz clic en "Ayuda" para ver las instrucciones completas

### Atajos de teclado
- **Enter**: Verificar respuesta
- **Flecha derecha (→)**: Mostrar respuesta correcta y pasar a la siguiente palabra

## Lógica de validación

La aplicación normaliza las respuestas:
- Elimina acentos y tildes
- Convierte a minúsculas
- Elimina espacios en blanco
- Extrae múltiples traducciones del campo `<d>`
- Ignora marcadores de género como `{m}`, `{f}`
- Ignora marcadores geográficos como `[Venezuela]`, `[Mexico]`

## Tecnologías utilizadas

- **Backend**: Python 3.x con Flask
- **Frontend**: HTML5, CSS3, JavaScript ES6
- **Estilo**: Bootstrap 5.3
- **Iconos**: Font Awesome 6.4
- **XML**: ElementTree para parsing

## Ejemplo de uso

1. La aplicación muestra: **"casa"**
2. Usuario escribe: **"house"**
3. Resultado: **"¡Correcto!"** ✅

O también:
1. La aplicación muestra: **"correr"**
2. Usuario escribe: **"run"** (acepta también "to run")
3. Resultado: **"¡Correcto!"** ✅

O con paréntesis:
1. La aplicación muestra: **"translúcido"**
2. Usuario escribe: **"translucent"** (acepta tanto "translucent" como "translucent (allowing light to pass through)")
3. Resultado: **"¡Correcto!"** ✅

## Personalización

Para añadir más palabras, edita el archivo `dict_es_en.xml` siguiendo el formato establecido. La aplicación cargará automáticamente todas las palabras al iniciar.

## Notas técnicas

- La aplicación carga el diccionario en memoria al iniciar
- Usa sesiones de Flask para mantener el estado de la palabra actual
- Las rutas implementadas son: `/`, `/check`, `/help`, `/new_word`
- El servidor ejecuta en modo debug para desarrollo
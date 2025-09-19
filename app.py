from flask import Flask, render_template, request, jsonify, session
import xml.etree.ElementTree as ET
import random
import re
import unicodedata
import os
import glob

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

basedir = os.path.abspath(os.path.dirname(__file__))

# Diccionarios para almacenar palabras y traducciones
# NOTA: En Gunicorn, cada worker tendrá su propia copia de estos diccionarios.
dictionary = {}
available_lessons = {}

def normalize_text(text):
    """Normaliza el texto quitando acentos y convirtiendo a minúsculas."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    return text.lower().strip()

def parse_translations(translations_text):
    """Analiza un texto de traducciones y extrae todas las posibles traducciones."""
    if not translations_text:
        return []
    translations = [t.strip() for t in re.split('[,;]', translations_text)]
    normalized_translations = []
    for translation in translations:
        if not translation:
            continue
        cleaned = re.sub(r'\{[mfn]\}', '', translation).strip()
        cleaned = re.sub(r'\[[^\]]+\]', '', cleaned).strip()
        if '(' in cleaned and ')' in cleaned:
            without_parentheses = re.sub(r'\s*\([^)]*\)', '', cleaned).strip()
            if without_parentheses:
                normalized_translations.append(normalize_text(without_parentheses))
            normalized_translations.append(normalize_text(cleaned))
        else:
            normalized_translations.append(normalize_text(cleaned))
        if cleaned.strip().lower().startswith('to '):
            without_to = cleaned[3:].strip()
            if without_to:
                if '(' in without_to and ')' in without_to:
                    without_parentheses = re.sub(r'\s*\([^)]*\)', '', without_to).strip()
                    if without_parentheses:
                        normalized_translations.append(normalize_text(without_parentheses))
                normalized_translations.append(normalize_text(without_to))
    seen = set()
    result = []
    for translation in normalized_translations:
        if translation and translation not in seen:
            seen.add(translation)
            result.append(translation)
    return result

def discover_lessons():
    """Descubre todos los archivos de lecciones XML."""
    global available_lessons
    available_lessons = {}
    filename = 'dict_es_en.xml'
    available_lessons[filename] = {
        'name': 'Diccionario completo',
        'file': os.path.join(basedir, filename),
        'type': 'main'
    }
    lessons_dir = os.path.join(basedir, 'lessons')
    if os.path.exists(lessons_dir):
        lesson_files = glob.glob(os.path.join(lessons_dir, '*.xml'))
        for lesson_file in lesson_files:
            filename = os.path.basename(lesson_file)
            lesson_name = os.path.splitext(filename)[0]
            display_name = f"Lección {lesson_name}"
            available_lessons[filename] = {
                'name': display_name,
                'file': lesson_file,
                'type': 'lesson'
            }
    return available_lessons

def load_dictionary(dict_key=None):
    """
    Carga el diccionario XML en memoria para este worker.
    """
    global dictionary
    if dict_key is None:
        dict_key = 'dict_es_en.xml'
    if dict_key not in available_lessons:
        dictionary = {}
        return
    file_to_load = available_lessons[dict_key]['file']
    dictionary = {}
    try:
        tree = ET.parse(file_to_load)
        root = tree.getroot()
        for word_elem in root.findall('.//w'):
            spanish_word_elem = word_elem.find('c')
            english_translations_elem = word_elem.find('d')
            definition_elem = word_elem.find('t')
            if spanish_word_elem is None or spanish_word_elem.text is None:
                continue
            spanish_word = spanish_word_elem.text.strip()
            english_translations = english_translations_elem.text if english_translations_elem is not None else ""
            definition = definition_elem.text if definition_elem is not None else ""
            possible_translations = parse_translations(english_translations)
            if possible_translations:
                dictionary[spanish_word] = {
                    'translations': possible_translations,
                    'original_translations': english_translations,
                    'definition': definition
                }
    except Exception as e:
        dictionary = {
            "casa": {
                "translations": ["house", "home"],
                "original_translations": "house, home",
                "definition": "{f} /ˈkasa/ (building for living)"
            }
        }

# --- Esta inicialización se ejecuta en cada worker de Gunicorn ---
discover_lessons()
load_dictionary()

# ---------------------------------------------------------------------

@app.route('/')
def index():
    # Establece la clave de la lección en la sesión si no existe
    if 'current_lesson_key' not in session:
        session['current_lesson_key'] = 'dict_es_en.xml'
    
    current_lesson_key = session.get('current_lesson_key')

    # Carga el diccionario correspondiente a la sesión del usuario
    load_dictionary(current_lesson_key)

    if not dictionary:
        return "Error: Dictionary not loaded"
    
    spanish_word = random.choice(list(dictionary.keys()))
    session['current_word'] = spanish_word
    session['help_shown'] = False
    
    current_lesson_info = available_lessons.get(current_lesson_key)
    
    return render_template('index.html',
                           spanish_word=spanish_word,
                           help_shown=False,
                           available_lessons=available_lessons,
                           current_lesson=current_lesson_info)

@app.route('/check', methods=['POST'])
def check_translation():
    # Recargar el diccionario para este worker antes de usarlo
    current_lesson_key = session.get('current_lesson_key')
    load_dictionary(current_lesson_key)

    user_translation = request.form.get('translation', '').strip()
    current_word = session.get('current_word')
    
    if not current_word or current_word not in dictionary:
        return jsonify({
            'status': 'error',
            'message': 'No word selected'
        })
    
    normalized_input = normalize_text(user_translation)
    possible_translations = dictionary[current_word]['translations']
    is_correct = any(normalized_input == normalized_translation for normalized_translation in possible_translations)
    
    if is_correct:
        new_spanish_word = random.choice(list(dictionary.keys()))
        session['current_word'] = new_spanish_word
        session['help_shown'] = False
        return jsonify({
            'status': 'correct',
            'message': '¡Correcto!',
            'user_answer': user_translation,
            'new_word': new_spanish_word
        })
    else:
        correct_translations = dictionary[current_word]['original_translations']
        return jsonify({
            'status': 'incorrect',
            'message': 'Incorrecto',
            'user_answer': user_translation,
            'correct_translations': correct_translations
        })

@app.route('/get_answer', methods=['POST'])
def get_answer():
    try:
        current_lesson_key = session.get('current_lesson_key')
        load_dictionary(current_lesson_key)
        data = request.get_json()
        word = data.get('word', '').strip()
        if not word or not dictionary:
            return jsonify({'success': False, 'error': 'Invalid word or dictionary not loaded'})
        if word in dictionary:
            translation = dictionary[word]['original_translations']
            if translation:
                return jsonify({'success': True, 'translation': translation})
        for entry_word in dictionary:
            if entry_word.lower() == word.lower():
                translation = dictionary[entry_word]['original_translations']
                if translation:
                    return jsonify({'success': True, 'translation': translation})
        return jsonify({'success': False, 'error': 'Word not found in dictionary'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new_word', methods=['POST'])
def new_word():
    # Recargar el diccionario para este worker antes de usarlo
    current_lesson_key = session.get('current_lesson_key')
    load_dictionary(current_lesson_key)

    if not dictionary:
        return jsonify({
            'status': 'error',
            'message': 'Dictionary not loaded'
        })
    
    new_spanish_word = random.choice(list(dictionary.keys()))
    session['current_word'] = new_spanish_word
    session['help_shown'] = False
    
    return jsonify({
        'status': 'success',
        'new_word': new_spanish_word
    })

@app.route('/switch_lesson', methods=['POST'])
def switch_lesson():
    try:
        data = request.get_json()
        lesson_key = data.get('lesson_key', '').strip()
        
        if not lesson_key or lesson_key not in available_lessons:
            return jsonify({
                'status': 'error',
                'message': 'Lección no válida'
            })
        
        # Actualiza la sesión para que las futuras solicitudes usen la lección correcta
        session['current_lesson_key'] = lesson_key
        
        # Carga el nuevo diccionario en este worker para la primera palabra
        load_dictionary(lesson_key)

        if not dictionary:
            return jsonify({
                'status': 'error',
                'message': 'Error al cargar la lección'
            })
        
        new_spanish_word = random.choice(list(dictionary.keys()))
        session['current_word'] = new_spanish_word
        session['help_shown'] = False
        
        return jsonify({
            'status': 'success',
            'new_word': new_spanish_word,
            'lesson_name': available_lessons[lesson_key]['name'],
            'word_count': len(dictionary)
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/help', methods=['POST'])
def get_help():
    # Recargar el diccionario para este worker antes de usarlo
    current_lesson_key = session.get('current_lesson_key')
    load_dictionary(current_lesson_key)
    
    current_word = session.get('current_word')
    
    if not current_word or current_word not in dictionary:
        return jsonify({
            'status': 'error',
            'message': 'No word selected'
        })
    
    word_data = dictionary[current_word]
    session['help_shown'] = True
    
    return jsonify({
        'status': 'success',
        'word': current_word,
        'definition': word_data['definition'],
        'translations': word_data['original_translations']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
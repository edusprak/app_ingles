from flask import Flask, render_template, request, jsonify, session
import xml.etree.ElementTree as ET
import random
import re
import unicodedata
import os
import glob

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Dictionary to store all words and translations
dictionary = {}

# Available lessons and dictionaries
available_lessons = {}
current_dictionary_file = 'dict_es_en.xml'

def normalize_text(text):
    """
    Normalize text by removing accents and converting to lowercase
    """
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    # Convert to lowercase and strip whitespace
    return text.lower().strip()

def parse_translations(translations_text):
    """
    Parse translations text and extract all possible translations
    
    Handles cases like:
    - "house, home"
    - "to run (move quickly), to jog"
    - "translucent (allowing light to pass through scattering it)"
    """
    if not translations_text:
        return []

    # Split by commas and semicolons to get individual translations
    translations = [t.strip() for t in re.split('[,;]', translations_text)]
    
    normalized_translations = []
    
    for translation in translations:
        if not translation:
            continue
            
        # Clean up the translation
        # Remove gender markers like {m}, {f}, {n}
        cleaned = re.sub(r'\{[mfn]\}', '', translation).strip()
        
        # Remove geographical markers like [Venezuela], [Mexico]
        cleaned = re.sub(r'\[[^\]]+\]', '', cleaned).strip()
        
        # Handle parentheses - extract both with and without
        if '(' in cleaned and ')' in cleaned:
            # Extract text without parentheses
            without_parentheses = re.sub(r'\s*\([^)]*\)', '', cleaned).strip()
            if without_parentheses:
                normalized_translations.append(normalize_text(without_parentheses))
            
            # Keep the full version too
            normalized_translations.append(normalize_text(cleaned))
        else:
            normalized_translations.append(normalize_text(cleaned))
        
        # Handle "to" prefix for verbs
        if cleaned.strip().lower().startswith('to '):
            # Add version without "to"
            without_to = cleaned[3:].strip()  # Remove "to " from beginning
            if without_to:
                # Handle parentheses in the version without "to"
                if '(' in without_to and ')' in without_to:
                    without_parentheses = re.sub(r'\s*\([^)]*\)', '', without_to).strip()
                    if without_parentheses:
                        normalized_translations.append(normalize_text(without_parentheses))
                normalized_translations.append(normalize_text(without_to))
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for translation in normalized_translations:
        if translation and translation not in seen:
            seen.add(translation)
            result.append(translation)
    
    return result

def discover_lessons():
    """
    Discover all XML lesson files in the lessons directory
    """
    global available_lessons
    available_lessons = {}
    
    # Add the main dictionary
    available_lessons['dict_es_en.xml'] = {
        'name': 'Diccionario completo',
        'file': 'dict_es_en.xml',
        'type': 'main'
    }
    
    # Discover lesson files in the lessons directory
    lessons_dir = 'lessons'
    if os.path.exists(lessons_dir):
        lesson_files = glob.glob(os.path.join(lessons_dir, '*.xml'))
        print(f"DEBUG: Found lesson files: {lesson_files}")
        for lesson_file in lesson_files:
            filename = os.path.basename(lesson_file)
            lesson_name = os.path.splitext(filename)[0]
            
            # Create display name
            display_name = f"Lección {lesson_name}"
            
            print(f"DEBUG: Adding lesson - key: '{filename}', name: '{display_name}', file: '{lesson_file}'")
            
            available_lessons[filename] = {
                'name': display_name,
                'file': lesson_file,
                'type': 'lesson'
            }
    
    print(f"Discovered {len(available_lessons)} dictionaries/lessons")
    return available_lessons

def load_dictionary(dict_file=None):
    """
    Load the XML dictionary into memory
    """
    global dictionary, current_dictionary_file
    
    if dict_file is None:
        dict_file = current_dictionary_file
    else:
        current_dictionary_file = dict_file
    
    # Clear the dictionary before loading new content
    dictionary = {}
    
    try:
        tree = ET.parse(dict_file)
        root = tree.getroot()
        
        for word_elem in root.findall('.//w'):
            spanish_word_elem = word_elem.find('c')  # Spanish word
            english_translations_elem = word_elem.find('d')  # English translations
            definition_elem = word_elem.find('t')
            
            # Skip if essential elements are missing
            if spanish_word_elem is None or spanish_word_elem.text is None:
                continue
                
            spanish_word = spanish_word_elem.text.strip()
            english_translations = english_translations_elem.text if english_translations_elem is not None else ""
            definition = definition_elem.text if definition_elem is not None else ""
            
            # Parse all possible translations
            possible_translations = parse_translations(english_translations)
            
            # Only add words that have at least one translation
            if possible_translations:
                dictionary[spanish_word] = {
                    'translations': possible_translations,
                    'original_translations': english_translations,
                    'definition': definition
                }
        
        print(f"Loaded {len(dictionary)} words from {dict_file}")
        
    except Exception as e:
        print(f"Error loading dictionary {dict_file}: {e}")
        # Fallback dictionary for testing
        dictionary = {
            "casa": {
                "translations": ["house", "home"],
                "original_translations": "house, home",
                "definition": "{f} /ˈkasa/ (building for living)"
            }
        }

@app.route('/')
def index():
    """
    Main page - shows a random Spanish word for translation to English
    """
    if not dictionary:
        return "Error: Dictionary not loaded"
    
    # Select a random Spanish word
    spanish_word = random.choice(list(dictionary.keys()))
    
    # Store the current word in session
    session['current_word'] = spanish_word
    session['help_shown'] = False
    
    # Get current lesson info
    current_lesson_info = None
    for lesson_key, lesson_data in available_lessons.items():
        if lesson_data['file'] == current_dictionary_file:
            current_lesson_info = lesson_data
            break
    
    return render_template('index.html', 
                         english_word=spanish_word,  # Keep this name for template compatibility
                         spanish_word=spanish_word,
                         help_shown=False,
                         available_lessons=available_lessons,
                         current_lesson=current_lesson_info)

@app.route('/check', methods=['POST'])
def check_translation():
    """
    Check if the user's translation is correct
    """
    user_translation = request.form.get('translation', '').strip()
    current_word = session.get('current_word')
    
    if not current_word or current_word not in dictionary:
        return jsonify({
            'status': 'error',
            'message': 'No word selected'
        })
    
    # Normalize user input
    normalized_input = normalize_text(user_translation)
    
    # Get all possible translations for the current word
    possible_translations = dictionary[current_word]['translations']
    
    # Check if user translation matches any of the possible translations
    is_correct = any(normalized_input == normalized_translation 
                    for normalized_translation in possible_translations)
    
    if is_correct:
        # If correct, automatically select a new word
        new_spanish_word = random.choice(list(dictionary.keys()))
        
        # Store the new word in session
        session['current_word'] = new_spanish_word
        session['help_shown'] = False
        
        return jsonify({
            'status': 'correct',
            'message': '¡Correcto!',
            'user_answer': user_translation,
            'new_word': new_spanish_word
        })
    else:
        # Get the correct translations to show to the user
        correct_translations = dictionary[current_word]['original_translations']
        return jsonify({
            'status': 'incorrect',
            'message': 'Incorrecto',
            'user_answer': user_translation,
            'correct_translations': correct_translations
        })

@app.route('/get_answer', methods=['POST'])
def get_answer():
    """Get the correct translation for a word"""
    try:
        data = request.get_json()
        word = data.get('word', '').strip()
        
        if not word or not dictionary:
            return jsonify({'success': False, 'error': 'Invalid word or dictionary not loaded'})
        
        # Find the word in dictionary (direct lookup)
        if word in dictionary:
            translation = dictionary[word]['original_translations']
            if translation:  # Make sure translation is not empty
                return jsonify({
                    'success': True, 
                    'translation': translation
                })
        
        # Try case-insensitive search if direct lookup fails
        for entry_word in dictionary:
            if entry_word.lower() == word.lower():
                translation = dictionary[entry_word]['original_translations']
                if translation:  # Make sure translation is not empty
                    return jsonify({
                        'success': True, 
                        'translation': translation
                    })
        
        return jsonify({'success': False, 'error': 'Word not found in dictionary'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new_word', methods=['POST'])
def new_word():
    """
    Get a new random word
    """
    if not dictionary:
        return jsonify({
            'status': 'error',
            'message': 'Dictionary not loaded'
        })
    
    # Select a new random word
    new_spanish_word = random.choice(list(dictionary.keys()))
    
    # Store the new word in session
    session['current_word'] = new_spanish_word
    session['help_shown'] = False
    
    return jsonify({
        'status': 'success',
        'new_word': new_spanish_word
    })

@app.route('/switch_lesson', methods=['POST'])
def switch_lesson():
    """
    Switch to a different lesson/dictionary
    """
    try:
        data = request.get_json()
        lesson_key = data.get('lesson_key', '').strip()
        
        print(f"DEBUG: Requested lesson_key: '{lesson_key}'")
        print(f"DEBUG: Available lessons: {list(available_lessons.keys())}")
        
        if not lesson_key or lesson_key not in available_lessons:
            print(f"DEBUG: Lesson key '{lesson_key}' not found in available lessons")
            return jsonify({
                'status': 'error',
                'message': 'Lección no válida'
            })
        
        lesson_info = available_lessons[lesson_key]
        dict_file = lesson_info['file']
        
        print(f"DEBUG: Loading dictionary file: '{dict_file}'")
        
        # Load the new dictionary
        load_dictionary(dict_file)
        
        if not dictionary:
            return jsonify({
                'status': 'error',
                'message': 'Error al cargar la lección'
            })
        
        # Select a new random word from the new dictionary
        new_spanish_word = random.choice(list(dictionary.keys()))
        
        # Store the new word in session
        session['current_word'] = new_spanish_word
        session['help_shown'] = False
        
        return jsonify({
            'status': 'success',
            'new_word': new_spanish_word,
            'lesson_name': lesson_info['name'],
            'word_count': len(dictionary)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/help', methods=['POST'])
def get_help():
    """
    Get help for the current word
    """
    current_word = session.get('current_word')
    
    if not current_word or current_word not in dictionary:
        return jsonify({
            'status': 'error',
            'message': 'No word selected'
        })
    
    word_data = dictionary[current_word]
    
    # Mark help as shown
    session['help_shown'] = True
    
    return jsonify({
        'status': 'success',
        'word': current_word,
        'definition': word_data['definition'],
        'translations': word_data['original_translations']
    })

if __name__ == '__main__':
    discover_lessons()
    load_dictionary()
    app.run(debug=True, host='0.0.0.0')
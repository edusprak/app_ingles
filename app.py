from flask import Flask, render_template, request, jsonify, session
import xml.etree.ElementTree as ET
import random
import re
import unicodedata

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Dictionary to store all words and translations
dictionary = {}

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

def load_dictionary():
    """
    Load the XML dictionary into memory
    """
    global dictionary
    try:
        tree = ET.parse('dict_es_en.xml')
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
        
        print(f"Loaded {len(dictionary)} words from dictionary")
        
    except Exception as e:
        print(f"Error loading dictionary: {e}")
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
    
    return render_template('index.html', 
                         english_word=spanish_word,  # Keep this name for template compatibility
                         spanish_word=spanish_word,
                         help_shown=False)

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
    load_dictionary()
    app.run(debug=True, host='0.0.0.0')
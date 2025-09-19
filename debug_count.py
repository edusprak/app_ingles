import xml.etree.ElementTree as ET

# Count words in 1.xml
try:
    tree = ET.parse('lessons/1.xml')
    words = tree.getroot().findall('.//w')
    print(f"Words in lessons/1.xml: {len(words)}")
    
    # Show first few words for verification
    print("\nFirst 5 words:")
    for i, word in enumerate(words[:5]):
        spanish = word.find('c')
        english = word.find('d')
        if spanish is not None and english is not None:
            print(f"  {i+1}. {spanish.text} -> {english.text}")
            
except Exception as e:
    print(f"Error: {e}")

# Count words in main dictionary for comparison
try:
    tree = ET.parse('dict_es_en.xml')
    words = tree.getroot().findall('.//w')
    print(f"\nWords in dict_es_en.xml: {len(words)}")
except Exception as e:
    print(f"Error with main dict: {e}")
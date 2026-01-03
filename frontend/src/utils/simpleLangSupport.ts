// Simple language support without Google Translate dependency
// This is a reliable fallback for when Google Translate is blocked or unavailable

export interface TranslationMap {
  [key: string]: {
    en: string;
    si: string;
    ta: string;
  };
}

// Key UI elements translations for demonstration
export const translations: TranslationMap = {
  // Navigation
  'home': { en: 'Home', si: 'මුල් පිටුව', ta: 'முகப்பு' },
  'dashboard': { en: 'Dashboard', si: 'උපකරණ පුවරුව', ta: 'டாஷ்போர்டு' },
  'caseAnalysis': { en: 'Case Analysis', si: 'නඩු විශ්ලේෂණය', ta: 'வழக்கு பகுப்பாய்வு' },
  
  // Dashboard
  'aiLegalSummarizer': { en: 'AI Legal Summarizer', si: 'AI නීති සාරාංශකරණය', ta: 'AI சட்ட சுருக்கம்' },
  'sriLankanLegalDocs': { en: 'Intelligent Analysis of Sri Lankan Legal Documents', si: 'ශ්‍රී ලංකා නීතිමය ලේඛනවල බුද්ධිමත් විශ්ලේෂණය', ta: 'இலங்கை சட்ட ஆவணங்களின் அறிவார்ந்த பகுப்பாய்வு' },
  'analyzeDocument': { en: 'Analyze Document', si: 'ලේඛනය විශ්ලේෂණය කරන්න', ta: 'ஆவணத்தை பகுப்பாய்வு செய்' },
  
  // Features
  'aiSummarization': { en: 'AI Summarization', si: 'AI සාරාංශකරණය', ta: 'AI சுருக்கம்' },
  'entityRecognition': { en: 'Entity Recognition', si: 'ආයතන හඳුනාගැනීම', ta: 'நிறுவன அங்கீகாரம்' },
  'constitutionalAnalysis': { en: 'Constitutional Analysis', si: 'ව්‍යවස්ථාමය විශ්ලේෂණය', ta: 'அரசியலமைப்பு பகுப்பாய்வு' },
  'documentStructure': { en: 'Document Structure', si: 'ලේඛන ව්‍යුහය', ta: 'ஆவண அமைப்பு' },
  
  // Case Analysis Page
  'uploadDocument': { en: 'Upload Legal Document', si: 'නීතිමය ලේඛනය උඩුගත කරන්න', ta: 'சட்ட ஆவணத்தை பதிவேற்றவும்' },
  'dragAndDrop': { en: 'Drag and drop your PDF here', si: 'ඔබගේ PDF මෙතැනට ඇදගෙන එන්න', ta: 'உங்கள் PDF ஐ இங்கே இழுத்து விடுங்கள்' },
  'selectFile': { en: 'Select File', si: 'ගොනුව තෝරන්න', ta: 'கோப்பைத் தேர்ந்தெடுக்கவும்' },
  'analyze': { en: 'Analyze', si: 'විශ්ලේෂණය කරන්න', ta: 'பகுப்பாய்வு செய்' },
  
  // Results
  'legalEntities': { en: 'Legal Entities', si: 'නීතිමය ආයතන', ta: 'சட்ட நிறுவனங்கள்' },
  'summary': { en: 'Summary', si: 'සාරාංශය', ta: 'சுருக்கம்' },
  'keywords': { en: 'Keywords', si: 'ප්‍රධාන වචන', ta: 'முக்கிய வார்த்தைகள்' },
  'caseName': { en: 'Case Name', si: 'නඩුවේ නම', ta: 'வழக்கு பெயர்' },
  'court': { en: 'Court', si: 'අධිකරණය', ta: 'நீதிமன்றம்' },
  'judge': { en: 'Judge', si: 'විනිසුරු', ta: 'நீதிபதி' },
  'statute': { en: 'Statute', si: 'ප්‍ර‍ඥප්තිය', ta: 'சட்டம்' },
  'article': { en: 'Article', si: 'වගන්තිය', ta: 'கட்டுரை' },
  
  // Actions
  'english': { en: 'English', si: 'English', ta: 'English' },
  'sinhala': { en: 'සිංහල', si: 'සිංහල', ta: 'සිංහල' },
  'tamil': { en: 'தமிழ்', si: 'தமிழ்', ta: 'தமிழ்' },
};

// Get translation for a key
export const t = (key: string, lang: 'en' | 'si' | 'ta' = 'en'): string => {
  return translations[key]?.[lang] || key;
};

// Apply translations to the page (simple text replacement)
export const applyTranslations = (lang: 'en' | 'si' | 'ta') => {
  // Store language preference
  localStorage.setItem('preferredLanguage', lang);
  
  // Note: For a full implementation, you would need to:
  // 1. Mark translatable elements with data-i18n attributes
  // 2. Replace their text content based on the language
  // 3. Update dynamically loaded content
  
  console.log(`Language changed to: ${lang}`);
  console.log('Note: Full translation requires Google Translate or a complete i18n implementation');
};

// Check if Google Translate is available
export const isGoogleTranslateAvailable = (): boolean => {
  return !!(window as any).google?.translate;
};

// Fallback language switcher
export const switchLanguageFallback = (lang: 'en' | 'si' | 'ta') => {
  if (isGoogleTranslateAvailable()) {
    // Use Google Translate if available
    const selectElement = document.querySelector<HTMLSelectElement>('.goog-te-combo');
    if (selectElement) {
      const langMap: { [key: string]: string } = { en: '', si: 'si', ta: 'ta' };
      selectElement.value = langMap[lang];
      selectElement.dispatchEvent(new Event('change'));
      return true;
    }
  }
  
  // Fallback: Just save preference
  applyTranslations(lang);
  return false;
};

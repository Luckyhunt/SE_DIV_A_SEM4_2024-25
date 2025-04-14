from flask import Flask, render_template, request, redirect, url_for, session, flash
import random
import mysql.connector
from time import time
import json
import sys
from flask_bcrypt import Bcrypt
from flask_session import Session

sys.stdout.reconfigure(encoding='utf-8')
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configure session
app.secret_key = "supersecretkey"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"  # Store session in a file to persist across requests
Session(app)


# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kb_2006",
        database="user_db"
    )


# Authentication routes (Login & Signup)
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("login-email")
        password = request.form.get("login-password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")

@app.route("/signup", methods=['GET', "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("signup-username")
        email = request.form.get("signup-email")
        password = request.form.get("signup-password")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                           (username, email, hashed_password))
            conn.commit()
            flash("Signup successful! Please log in.", "success")
        except mysql.connector.IntegrityError:
            flash("Email already registered!", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("You must be logged in to view this page.", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("home"))

    return render_template("dashboard.html", user=user)

@app.route("/")
def home():
    return render_template("home.html")

word_list = [
    ["घर", "पानी", "खुशी", "दोस्त", "प्यार"],  
    ["सपना", "शक्ति", "शांति", "समय", "आदमी"],  
    ["महिला", "बच्चा", "रात", "दिन", "सूरज"],  
    ["चाँद", "सपने", "संगीत", "नृत्य", "चित्र"],  
    ["राजा", "रानी", "सैनिक", "देश", "दुनिया"],  
    ["धरती", "आसमान", "पर्वत", "समुद्र", "नदी"],  
    ["पक्षी", "प्रकृति", "उत्सव", "विजय", "सफलता"],  
    ["ज्ञान", "अनुभव", "संस्कार", "स्वास्थ्य", "शुद्ध"],  
    ["शक्ति", "धैर्य", "सौंदर्य", "सत्य", "संतोष"]  
]

TOTAL_LEVELS = len(word_list)
WORDS_PER_LEVEL = 5
REQUIRED_CORRECT = 4  # Player must guess 4 out of 5 correctly to pass

def initialize_level(level):
    """Initialize a new level with words and missing letter indices."""
    words = word_list[level]
    missing_indices = [random.randint(0, len(word) - 1) for word in words]
    return words, missing_indices

@app.route("/word_game", methods=["GET", "POST"])
def play():
    """Main game logic handling each level's words."""
    
    if "level" not in session:
        session["level"] = "level0"  # Store as "level0", "level1", etc.
        session["words"], session["missing_indices"] = initialize_level(0)
        session["correct_answers"] = 0  # Ensure it is always set
        session["current_word_index"] = 0 

    level = int(session["level"].replace("level", ""))  # Extract number

    if level >= TOTAL_LEVELS:
        return redirect(url_for("home"))

    # Ensure session keys exist
    if "correct_answers" not in session:
        session["correct_answers"] = 0  # Initialize if missing
    if "current_word_index" not in session:
        session["current_word_index"] = 0
    if "words" not in session or "missing_indices" not in session:
        session["words"], session["missing_indices"] = initialize_level(level)

    word_index = session["current_word_index"]
    words = session["words"]
    missing_indices = session["missing_indices"]

    if word_index >= WORDS_PER_LEVEL:
        if session["correct_answers"] >= REQUIRED_CORRECT:
            message = f"✅ Well done! You passed Level {level+1}!"
            show_next = True
            show_retry = False
        else:
            message = f"❌ You failed Level {level+1}. Try again!"
            show_next = False
            show_retry = True
        return render_template("word_game.html", level=level+1, word="", message=message, show_next=show_next, show_retry=show_retry)

    word = words[word_index]
    missing_index = missing_indices[word_index]

    # Create a word with a missing letter
    word_with_blank = list(word)
    word_with_blank[missing_index] = "_"
    word_with_blank = ''.join(word_with_blank)

    message = ""

    if request.method == "POST":
        guess = request.form.get("guess")
        if guess and guess == word[missing_index]:
            session["correct_answers"] += 1  # Now it will never cause KeyError
        session["current_word_index"] += 1
        return redirect(url_for("play"))

    return render_template("word_game.html", level=level+1, word=word_with_blank, message=message, show_next=False, show_retry=False)


@app.route("/next_level", methods=["POST"])
def next_level():
    """Move to the next level if passed."""
    if int(session["level"].replace("level", "")) < TOTAL_LEVELS - 1:
        session["level"] = f"level{int(session['level'].replace('level', '')) + 1}"
        session["current_word_index"] = 0
        session["words"], session["missing_indices"] = initialize_level(int(session["level"].replace("level", "")))
        session["correct_answers"] = 0
        return redirect(url_for("play"))
    return redirect(url_for("home"))

@app.route("/retry_level", methods=["POST"])
def retry_level():
    """Retry the current level."""
    session["current_word_index"] = 0
    session["words"], session["missing_indices"] = initialize_level(int(session["level"].replace("level", "")))
    session["correct_answers"] = 0
    return redirect(url_for("play"))



# Quiz Game Routes
quiz_levels = {  # Sample quiz levels
      "level1": [
        {"question": "भारत का राष्ट्रीय फल कौन सा है?", "options": ["सेब", "केला", "आम", "अंगूर"], "answer": "आम"},
        {"question": "भारत का राष्ट्रीय पशु कौन सा है?", "options": ["गाय", "शेर", "बाघ", "हाथी"], "answer": "बाघ"},
        {"question": "भारत का राष्ट्रीय पक्षी कौन सा है?", "options": ["तोता", "मोर", "कबूतर", "बुलबुल"], "answer": "मोर"},
        {"question": "भारत की राजधानी कौन सी है?", "options": ["मुंबई", "दिल्ली", "कोलकाता", "चेन्नई"], "answer": "दिल्ली"},
        {"question": "ताजमहल कहाँ स्थित है?", "options": ["दिल्ली", "आगरा", "जयपुर", "लखनऊ"], "answer": "आगरा"}
    ],
    "level2": [
        {"question": "कौन सा ग्रह सौर मंडल में सबसे बड़ा है?", "options": ["पृथ्वी", "मंगल", "शनि", "बृहस्पति"], "answer": "बृहस्पति"},
        {"question": "भारत के प्रथम प्रधानमंत्री कौन थे?", "options": ["महात्मा गांधी", "सरदार पटेल", "जवाहरलाल नेहरू", "लाल बहादुर शास्त्री"], "answer": "जवाहरलाल नेहरू"},
        {"question": "मोनालिसा चित्रकला किसने बनाई थी?", "options": ["पिकासो", "माइकल एंजेलो", "लियोनार्डो दा विंची", "विन्सेंट वान गॉग"], "answer": "लियोनार्डो दा विंची"},
        {"question": "भारत में स्वतंत्रता दिवस कब मनाया जाता है?", "options": ["15 अगस्त", "26 जनवरी", "2 अक्टूबर", "14 नवम्बर"], "answer": "15 अगस्त"},
        {"question": "ओलंपिक खेल कितने वर्षों में एक बार होते हैं?", "options": ["2", "3", "4", "5"], "answer": "4"}
    ],
    "level3": [
        {"question": "किस धातु को 'तरल धातु' कहा जाता है?", "options": ["सोना", "पारा", "लोहा", "तांबा"], "answer": "पारा"},
        {"question": "किस देश को 'उगते सूरज की भूमि' कहा जाता है?", "options": ["भारत", "चीन", "जापान", "थाईलैंड"], "answer": "जापान"},
        {"question": "पृथ्वी पर सबसे बड़ा महासागर कौन सा है?", "options": ["अटलांटिक महासागर", "हिंद महासागर", "प्रशांत महासागर", "आर्कटिक महासागर"], "answer": "प्रशांत महासागर"},
        {"question": "कौन सा रंग गर्मी को सबसे अधिक अवशोषित करता है?", "options": ["सफेद", "नीला", "काला", "हरा"], "answer": "काला"},
        {"question": "कौन सा विटामिन सूर्य के प्रकाश से प्राप्त होता है?", "options": ["विटामिन A", "विटामिन B", "विटामिन C", "विटामिन D"], "answer": "विटामिन D"}
    ],
    "level4": [
        {"question": "पृथ्वी के सबसे नजदीक कौन सा ग्रह है?", "options": ["शनि", "मंगल", "बुध", "अरुण"], "answer": "बुध"},
        {"question": "कौन सा खेल 'ड्रिब्लिंग' से संबंधित है?", "options": ["हॉकी", "फुटबॉल", "क्रिकेट", "टेबल टेनिस"], "answer": "फुटबॉल"},
        {"question": "भारत में सबसे लंबी नदी कौन सी है?", "options": ["गंगा", "यमुना", "ब्रह्मपुत्र", "नर्मदा"], "answer": "गंगा"},
        {"question": "भारत में लोकसभा चुनाव कितने वर्षों में होते हैं?", "options": ["3", "4", "5", "6"], "answer": "5"},
        {"question": "कंप्यूटर का मस्तिष्क किसे कहा जाता है?", "options": ["मॉनिटर", "RAM", "CPU", "कीबोर्ड"], "answer": "CPU"}
    ],
    "level5": [
        {"question": "भारत का सबसे बड़ा राज्य कौन सा है?", "options": ["उत्तर प्रदेश", "महाराष्ट्र", "राजस्थान", "मध्य प्रदेश"], "answer": "राजस्थान"},
        {"question": "कौन सा तत्व पानी को शुद्ध करने के लिए उपयोग किया जाता है?", "options": ["क्लोरीन", "ऑक्सीजन", "हाइड्रोजन", "सल्फर"], "answer": "क्लोरीन"},
        {"question": "ओजोन परत किस गैस से बनी होती है?", "options": ["ऑक्सीजन", "कार्बन डाइऑक्साइड", "ओजोन", "नाइट्रोजन"], "answer": "ओजोन"},
        {"question": "किस मुगल शासक ने ताजमहल बनवाया था?", "options": ["अकबर", "जहांगीर", "शाहजहां", "औरंगजेब"], "answer": "शाहजहां"},
        {"question": "किस खेल में 'ड्यूस' शब्द का उपयोग किया जाता है?", "options": ["बैडमिंटन", "टेनिस", "क्रिकेट", "हॉकी"], "answer": "टेनिस"}
    ],
    "level6": [
        {"question": "इंसुलिन किस बीमारी के इलाज में उपयोग किया जाता है?", "options": ["कैंसर", "मलेरिया", "डायबिटीज", "डेंगू"], "answer": "डायबिटीज"},
        {"question": "कौन सा ग्रह लाल ग्रह के नाम से जाना जाता है?", "options": ["बुध", "मंगल", "शुक्र", "शनि"], "answer": "मंगल"},
        {"question": "भारत में राष्ट्रपति का कार्यकाल कितने वर्षों का होता है?", "options": ["4", "5", "6", "7"], "answer": "5"},
        {"question": "UNO का मुख्यालय कहाँ स्थित है?", "options": ["वॉशिंगटन डीसी", "लंदन", "पेरिस", "न्यूयॉर्क"], "answer": "न्यूयॉर्क"},
        {"question": "कौन सा धातु चुंबकीय गुण रखता है?", "options": ["तांबा", "लोहा", "एलुमिनियम", "चांदी"], "answer": "लोहा"}
    ],
    "level7": [
        {"question": "पृथ्वी पर सबसे ऊँचा पर्वत कौन सा है?", "options": ["कंचनजंगा", "माउंट एवरेस्ट", "नंगा पर्वत", "धौलागिरी"], "answer": "माउंट एवरेस्ट"},
        {"question": "कौन सा यंत्र भूकंप की तीव्रता मापता है?", "options": ["बैरामीटर", "सिस्मोग्राफ", "हाईग्रोमीटर", "थर्मामीटर"], "answer": "सिस्मोग्राफ"},
        {"question": "कौन सा पदार्थ विद्युत का सबसे अच्छा चालक है?", "options": ["तांबा", "लकड़ी", "रबर", "प्लास्टिक"], "answer": "तांबा"},
        {"question": "भारत के राष्ट्रीय ध्वज में कितने रंग होते हैं?", "options": ["दो", "तीन", "चार", "पाँच"], "answer": "तीन"},
        {"question": "कौन सा ग्रह अपनी धुरी पर सबसे तेज़ घूमता है?", "options": ["बृहस्पति", "शनि", "मंगल", "पृथ्वी"], "answer": "बृहस्पति"}
    ],
    "level8": [
        {"question": "किसका उपयोग रक्तचाप मापने के लिए किया जाता है?", "options": ["बैरोमीटर", "स्पाइग्मोमैनोमीटर", "हाइग्रोमीटर", "थर्मामीटर"], "answer": "स्पाइग्मोमैनोमीटर"},
        {"question": "भारत का पहला उपग्रह कौन सा था?", "options": ["चंद्रयान", "मंगलयान", "आर्यभट्ट", "इन्सट"], "answer": "आर्यभट्ट"},
        {"question": "कौन सा ग्रह सूर्य के सबसे करीब है?", "options": ["मंगल", "शुक्र", "बुध", "पृथ्वी"], "answer": "बुध"},
        {"question": "भारत में सबसे ज्यादा बोली जाने वाली भाषा कौन सी है?", "options": ["तमिल", "हिन्दी", "बंगाली", "मराठी"], "answer": "हिन्दी"},
        {"question": "कौन सा धातु सबसे हल्का है?", "options": ["लोहा", "एलुमिनियम", "लिथियम", "सोना"], "answer": "लिथियम"}
    ],
    "level9": [
        {"question": "कौन सा जानवर सबसे तेज़ दौड़ता है?", "options": ["कंगारू", "चीता", "घोड़ा", "शेर"], "answer": "चीता"},
        {"question": "किस देश ने ओलंपिक खेलों की शुरुआत की?", "options": ["रोम", "यूनान", "मिस्र", "चीन"], "answer": "यूनान"},
        {"question": "कौन सा ग्रह सूर्य के चारों ओर सबसे तेज गति से घूमता है?", "options": ["बुध", "शनि", "मंगल", "बृहस्पति"], "answer": "बुध"},
        {"question": "कौन सा यंत्र तापमान मापने के लिए उपयोग किया जाता है?", "options": ["हाईग्रोमीटर", "बैरोमीटर", "थर्मामीटर", "एनिमोमीटर"], "answer": "थर्मामीटर"},
        {"question": "भारत में कितने राज्यों की सीमा नेपाल से मिलती है?", "options": ["3", "4", "5", "6"], "answer": "5"}
    ],
    "level10": [
        {"question": "कौन सा धातु पानी से तेजी से प्रतिक्रिया करता है?", "options": ["तांबा", "लोहा", "सोडियम", "चांदी"], "answer": "सोडियम"},
        {"question": "भारत में सबसे ऊँची चोटी कौन सी है?", "options": ["गॉडविन ऑस्टिन", "नंदा देवी", "कंचनजंगा", "धौलागिरी"], "answer": "कंचनजंगा"},
        {"question": "पृथ्वी की सतह पर सबसे गहरा महासागर कौन सा है?", "options": ["अटलांटिक महासागर", "प्रशांत महासागर", "हिंद महासागर", "आर्कटिक महासागर"], "answer": "प्रशांत महासागर"},
        {"question": "भारत के राष्ट्रीय झंडे में बीच में कौन सा चिह्न होता है?", "options": ["कमल", "अशोक चक्र", "गांधी जी के चश्मे", "शेर"], "answer": "अशोक चक्र"},
        {"question": "कौन सा तत्व हड्डियों को मजबूत करता है?", "options": ["लोहा", "कैल्शियम", "सोडियम", "पोटैशियम"], "answer": "कैल्शियम"}
    ],
    "level11": [
        {"question": "भारत का सबसे लंबा नदी कौन सा है?", "options": ["गंगा", "ब्रह्मपुत्र", "यमुना", "सिंधु"], "answer": "गंगा"},
        {"question": "कौन सा ग्रह अपने अक्ष पर सबसे धीमी गति से घूमता है?", "options": ["शुक्र", "मंगल", "बृहस्पति", "शनि"], "answer": "शुक्र"},
        {"question": "कौन सा धातु सबसे अधिक विद्युत चालकता रखता है?", "options": ["तांबा", "चांदी", "सोना", "लोहा"], "answer": "चांदी"},
        {"question": "कौन सा अम्ल हमारे पेट में पाया जाता है?", "options": ["सालिसिलिक अम्ल", "हाइड्रोक्लोरिक अम्ल", "नाइट्रिक अम्ल", "सल्फ्यूरिक अम्ल"], "answer": "हाइड्रोक्लोरिक अम्ल"},
        {"question": "किसने खोजा कि पृथ्वी सूर्य के चारों ओर घूमती है?", "options": ["गैलीलियो", "न्यूटन", "आइंस्टीन", "कोपरनिकस"], "answer": "कोपरनिकस"}
    ],
    "level12": [
        {"question": "भारत का सबसे बड़ा बांध कौन सा है?", "options": ["भाखड़ा नांगल", "हीराकुंड", "सरदार सरोवर", "टेहरी"], "answer": "हीराकुंड"},
        {"question": "कौन सा ग्रह अपनी कक्षा में उल्टी दिशा में घूमता है?", "options": ["बुध", "शुक्र", "मंगल", "शनि"], "answer": "शुक्र"},
        {"question": "किस देश को 'उगते सूरज की भूमि' कहा जाता है?", "options": ["चीन", "जापान", "कोरिया", "थाईलैंड"], "answer": "जापान"},
        {"question": "भारत में संसद भवन कहाँ स्थित है?", "options": ["मुंबई", "कोलकाता", "दिल्ली", "चेन्नई"], "answer": "दिल्ली"},
        {"question": "कौन सा खनिज दूध में प्रचुर मात्रा में पाया जाता है?", "options": ["लोहा", "कैल्शियम", "सोडियम", "पोटैशियम"], "answer": "कैल्शियम"}
    ],
    "level13": [
        {"question": "भारत में सबसे ऊँचा जलप्रपात कौन सा है?", "options": ["जोग फॉल्स", "केशरगढ़ फॉल्स", "दूधसागर फॉल्स", "शिवसामुद्रम फॉल्स"], "answer": "जोग फॉल्स"},
        {"question": "कौन सा विटामिन सूर्य के प्रकाश से प्राप्त होता है?", "options": ["विटामिन A", "विटामिन B", "विटामिन C", "विटामिन D"], "answer": "विटामिन D"},
        {"question": "भारत में पहला आम चुनाव कब हुआ था?", "options": ["1947", "1950", "1951", "1952"], "answer": "1951"},
        {"question": "किस गैस को 'हंसाने वाली गैस' कहा जाता है?", "options": ["ऑक्सीजन", "नाइट्रोजन", "नाइट्रस ऑक्साइड", "कार्बन मोनोऑक्साइड"], "answer": "नाइट्रस ऑक्साइड"},
        {"question": "कौन सा रक्त समूह 'यूनिवर्सल डोनर' कहलाता है?", "options": ["A", "B", "AB", "O"], "answer": "O"}
    ],
    "level14": [
        {"question": "भारत के संविधान की प्रस्तावना में कौन सा शब्द नहीं है?", "options": ["धर्मनिरपेक्ष", "समाजवादी", "सर्वोच्च", "संघीय"], "answer": "संघीय"},
        {"question": "कौन सा ग्रह सबसे अधिक उपग्रहों वाला है?", "options": ["बृहस्पति", "शनि", "मंगल", "यूरेनस"], "answer": "शनि"},
        {"question": "कौन सा समुद्र विश्व का सबसे बड़ा समुद्र है?", "options": ["अरब सागर", "केरिबियन सागर", "मेडिटेरेनियन सागर", "कोरल सागर"], "answer": "केरिबियन सागर"},
        {"question": "भारतीय राष्ट्रीय ध्वज को पहली बार कब फहराया गया था?", "options": ["1911", "1920", "1925", "1947"], "answer": "1920"},
        {"question": "प्लास्टिक किससे बनता है?", "options": ["कपास", "पेट्रोलियम", "लकड़ी", "रेशम"], "answer": "पेट्रोलियम"}
    ],
    "level15": [
        {"question": "भारत में सबसे पुराना पर्व कौन सा है?", "options": ["होली", "दीवाली", "ओणम", "मकर संक्रांति"], "answer": "मकर संक्रांति"},
        {"question": "कौन सा ग्रह अपनी धुरी पर 90 डिग्री झुका हुआ है?", "options": ["बुध", "शुक्र", "यूरेनस", "नेपच्यून"], "answer": "यूरेनस"},
        {"question": "भारत में प्रथम लोकसभा चुनाव किस वर्ष हुआ था?", "options": ["1947", "1952", "1955", "1960"], "answer": "1952"},
        {"question": "इलेक्ट्रॉन की खोज किसने की थी?", "options": ["रदरफोर्ड", "थॉमसन", "बोर", "मैक्सवेल"], "answer": "थॉमसन"},
        {"question": "शरीर में सबसे बड़ी ग्रंथि कौन सी है?", "options": ["अग्न्याशय", "यकृत", "थायरॉयड", "अधिवृक्क"], "answer": "यकृत"}
    ],
    "level16": [
        {"question": "भारत की सबसे लंबी सुरंग कौन सी है?", "options": ["रोहतांग टनल", "अटल टनल", "बनिहाल टनल", "श्योक टनल"], "answer": "अटल टनल"},
        {"question": "भारत में पहली मेट्रो ट्रेन कहाँ चली थी?", "options": ["दिल्ली", "मुंबई", "कोलकाता", "चेन्नई"], "answer": "कोलकाता"},
        {"question": "कौन सा यंत्र ध्वनि की तीव्रता मापने के लिए उपयोग किया जाता है?", "options": ["डेसिबल मीटर", "सोनोमीटर", "बैरोमीटर", "थर्मामीटर"], "answer": "डेसिबल मीटर"},
        {"question": "किस भारतीय राज्य में सबसे ज्यादा जनसंख्या है?", "options": ["बिहार", "महाराष्ट्र", "उत्तर प्रदेश", "राजस्थान"], "answer": "उत्तर प्रदेश"},
        {"question": "विश्व का सबसे बड़ा महासागर कौन सा है?", "options": ["अटलांटिक", "प्रशांत", "हिंद", "आर्कटिक"], "answer": "प्रशांत"}
    ],
    "level17": [
        {"question": "भारत में कुल कितने उच्च न्यायालय हैं?", "options": ["18", "20", "25", "30"], "answer": "25"},
        {"question": "कौन सा देश सबसे अधिक सोने का उत्पादन करता है?", "options": ["भारत", "अमेरिका", "ऑस्ट्रेलिया", "चीन"], "answer": "चीन"},
        {"question": "कौन सा पदार्थ सबसे कठोर होता है?", "options": ["हीरा", "ग्रेफाइट", "लोहा", "प्लैटिनम"], "answer": "हीरा"},
        {"question": "किस रक्त समूह को 'यूनिवर्सल रिसीवर' कहते हैं?", "options": ["A", "B", "AB", "O"], "answer": "AB"},
        {"question": "किस ग्रह को 'हरी ग्रह' कहा जाता है?", "options": ["पृथ्वी", "शनि", "नेपच्यून", "यूरेनस"], "answer": "यूरेनस"}
    ],
    "level18": [
        {"question": "भारत में सबसे लंबी नदी कौन सी है?", "options": ["गंगा", "यमुना", "सरस्वती", "नर्मदा"], "answer": "गंगा"},
        {"question": "मुगल वंश का संस्थापक कौन था?", "options": ["अकबर", "बाबर", "औरंगजेब", "हुमायूँ"], "answer": "बाबर"},
        {"question": "भारत का संविधान कब लागू हुआ?", "options": ["1947", "1950", "1952", "1960"], "answer": "1950"},
        {"question": "भारत में कुल कितने राज्य हैं?", "options": ["25", "28", "30", "29"], "answer": "28"},
        {"question": "भारतीय राष्ट्रीय ध्वज में कितने रंग होते हैं?", "options": ["2", "3", "4", "5"], "answer": "3"}
    ]
}

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Ensure 'level' is always set
    if 'level' not in session:
        session['level'] = "level1"  # Default starting level

    # Ensure 'current_level' is properly initialized
    if 'current_level' not in session:
        session['current_level'] = session['level']

    # Ensure questions exist for the current level
    if 'questions' not in session or session.get('level') != session.get('current_level', ''):
        session['question_num'] = 0
        session['score'] = 0
        session['current_level'] = session['level']

        # Debugging Output
        print(f"Current Level: {session['level']}")
        print(f"Available Levels: {quiz_levels.keys()}")

        # Double-check level validity
        if session['level'] not in quiz_levels:
            flash(f"Error: {session['level']} not found! Resetting.", "danger")
            session['level'] = "level1"

        session['questions'] = random.sample(quiz_levels[session['level']], 5)
        session['start_time'] = time()  # Start timer

    # Calculate remaining time
    elapsed_time = time() - session.get('start_time', time())
    if elapsed_time > 60:  # If more than 60 seconds have passed
        return redirect(url_for('level_failed'))

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        if selected_answer == session['questions'][session['question_num']]['answer']:
            session['score'] += 1
        session['question_num'] += 1

    if session['question_num'] >= len(session['questions']):
        return redirect(url_for('result'))

    return render_template('quiz.html', 
                           question_num=session['question_num'] + 1, 
                           question=session['questions'][session['question_num']], 
                           level=session['level'],   # Pass level to template
                           time_remaining=int(60 - elapsed_time))

@app.route('/result')
def result():
    score = session.get('score', 0)
    total = len(session.get('questions', []))
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO quiz_results (score, total) VALUES (%s, %s)", (score, total))
        conn.commit()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
    
    if score >= 4:
        current_level = session.get('level', 'level1')
        next_level = f"level{int(current_level[-1]) + 1}" if f"level{int(current_level[-1]) + 1}" in quiz_levels else None
        
        if next_level:
            session['level'] = next_level
            return redirect(url_for('level_completed'))

    return render_template('result.html', score=score, total=total)


@app.route('/level_completed')
def level_completed():
    return render_template('level_completed.html')

@app.route('/level_failed')
def level_failed():
    return render_template('level_failed.html')

@app.route('/retry')
def retry():
    session.pop('questions', None)
    session.pop('question_num', None)
    session.pop('score', None)
    session['start_time'] = time()
    return redirect(url_for('quiz'))


if __name__ == "__main__":
    app.run(debug=True, port=8500)

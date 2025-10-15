import streamlit as st
import wikipedia
import numpy as np
import sympy as sp
import datetime
import requests
import re
import random
import textwrap
import time 

# ------------------------------
# Streamlit Config
# ------------------------------
st.set_page_config(page_title="Study Buddy", layout="wide")

# ------------------------------
# CSS Effects
# ------------------------------
st.markdown("""
<style>
/* Targets the main title and the new sidebar title */
h1 {text-align:center;font-size:50px;animation: rainbow 5s infinite;} 
@keyframes rainbow {
0% {color: red;} 16% {color: orange;} 33% {color: yellow;} 50% {color: green;}
66% {color: blue;} 83% {color: indigo;} 100% {color: violet;}
}
/* New style for the tool headings (h2) - uses the same rainbow animation for consistency */
h2.tool-heading {
    text-align: center;
    font-size: 35px;
    animation: rainbow 5s infinite;
}
input, textarea, select {
border: 4px solid; border-radius: 10px; padding: 8px; font-weight: bold; font-size: 16px;
color: #111; box-shadow: 0 0 10px #ff00ff, 0 0 20px #00ffff, 0 0 30px #ffff00;
}
button {
border: none; border-radius: 10px; padding: 8px 15px; font-weight: bold; font-size: 16px;
cursor: pointer; box-shadow: 0 0 10px #ff00ff, 0 0 20px #00ffff, 0 0 30px #ffff00;
transition: transform 0.2s;
}
button:hover {transform: scale(1.05);}
.correct {background-color: #b6f0b6; padding: 5px; border-radius: 5px;}
.wrong {background-color: #f0b6b6; padding: 5px; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# Wolfram API Keys
# ------------------------------
wolfram_keys = ["8L5YE636JU", "3KRR2XR9J2", "3J875Y7PL7"]
wolfram_index = 0
def get_next_wolfram_key():
    global wolfram_index
    key = wolfram_keys[wolfram_index]
    wolfram_index = (wolfram_index + 1) % len(wolfram_keys)
    return key

# ------------------------------
# Session State Initialization
# ------------------------------
if "topics_today" not in st.session_state: st.session_state.topics_today = {}
if "last_reset" not in st.session_state: st.session_state.last_reset = datetime.date.today()
if st.session_state.last_reset != datetime.date.today():
    st.session_state.topics_today = {}
    st.session_state.last_reset = datetime.date.today()
if "quiz_questions" not in st.session_state: st.session_state.quiz_questions = []
if "quiz_index" not in st.session_state: st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state: st.session_state.quiz_score = 0
if "quiz_count" not in st.session_state: st.session_state.quiz_count = 0
if "meditation_minutes" not in st.session_state: st.session_state.meditation_minutes = 0
if "meditation_history" not in st.session_state: st.session_state.meditation_history = []
if "timer_running" not in st.session_state: st.session_state.timer_running = False
if "timer_end_time" not in st.session_state: st.session_state.timer_end_time = None

# ------------------------------
# Helper Functions
# ------------------------------
def fetch_wikipedia_long(topic, sentences=15):
    try: wikipedia.set_lang("en"); return wikipedia.summary(topic, sentences=sentences)
    except: return ""

def fetch_wolfram_long(topic):
    for _ in range(len(wolfram_keys)):
        key = get_next_wolfram_key()
        try:
            url = f"https://api.wolframalpha.com/v2/query?appid={key}&input={requests.utils.quote(topic)}&output=JSON"
            r = requests.get(url, timeout=8).json()
            pods = r.get("queryresult", {}).get("pods", [])
            text_results = []
            for pod in pods:
                for sub in pod.get("subpods", []):
                    if "plaintext" in sub and sub["plaintext"]: text_results.append(sub["plaintext"])
            if text_results: return "\n".join(text_results)
        except: continue
    return ""

def fetch_duckduckgo_long(topic):
    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(topic)}&format=json&no_redirect=1&skip_disambig=1"
        r = requests.get(url, timeout=8).json()
        abstract = r.get("AbstractText", "")
        related = r.get("RelatedTopics", [])
        extra_text = ""
        for item in related[:5]:
            if isinstance(item, dict):
                if "Text" in item: extra_text += " " + item["Text"]
                elif "Topics" in item:
                    for subitem in item["Topics"][:2]:
                        if "Text" in subitem: extra_text += " " + subitem["Text"]
        combined_text = abstract + " " + extra_text
        return combined_text.strip()
    except: return ""

def summarize_topic(topic):
    wiki_text = fetch_wikipedia_long(topic)
    wolfram_text = fetch_wolfram_long(topic)
    duck_text = fetch_duckduckgo_long(topic)
    combined = wiki_text + "\n\n" + wolfram_text
    if len(combined.strip()) < 200 and duck_text: combined += "\n\n" + duck_text
    combined = re.sub(r'\([^)]*\)', '', combined)
    combined = re.sub(r'\s+', ' ', combined)
    wrapped_text = textwrap.fill(combined, width=95)
    return f"### 🧠 Summary for **{topic.title()}**\n\n{wrapped_text}"

def generate_fill_in_blank(summary):
    sentences = [s.strip() for s in re.split(r'[.!?]', summary) if s.strip()]
    if not sentences: return None
    suitable_sentences = [s for s in sentences if len(s.split()) > 8]
    if not suitable_sentences: return None
    sentence = random.choice(suitable_sentences)
    
    words = [w.strip(".,;") for w in sentence.split() if w.strip(".,;")]
    if not words: return None 

    potential_answers = [w for w in words if w and w[0].isupper() and w not in ["A","The","An","In","On","Of","For","With","He","She","It"] and w != words[0]]
    
    if not potential_answers: 
        potential_answers = [w for w in words if len(w) > 5]
    
    if not potential_answers: return None
    
    answer = random.choice(potential_answers)
    
    blank_sentence = re.sub(r'\b' + re.escape(answer) + r'\b', '_____', sentence, flags=re.IGNORECASE)
    
    all_words = [w.strip(".,;").lower() for s in st.session_state.topics_today.values() for w in s.split() if w.strip(".,;")]
    unique_words = list(set(w for w in all_words if len(w)>3 and w.lower()!=answer.lower()))
    
    if not unique_words:
        distractors = []
    else:
        distractors = random.sample(unique_words, min(3,len(unique_words)))
        
    options = [answer] + [d.capitalize() for d in distractors]
    random.shuffle(options)
    
    return blank_sentence + "?", answer, options

def generate_quiz_questions(topics_dict, total_questions=10):
    questions=[]
    all_summaries=list(topics_dict.items())
    topic_idx=0
    while len(questions)<total_questions and all_summaries and topic_idx<100*len(all_summaries):
        topic, summary = all_summaries[topic_idx % len(all_summaries)]
        q = generate_fill_in_blank(summary)
        if q:
            blank_sentence, answer, options = q
            if not any(d["question"] == blank_sentence for d in questions):
                questions.append({"topic":topic,"question":blank_sentence,"answer":answer,"options":options})
        topic_idx += 1
    random.shuffle(questions)
    return questions[:total_questions]

def generate_flashcards_from_summary(summary, topic):
    lines = summary.split(".")
    cards=[]
    for line in lines[:5]:
        words = re.findall(r'\b[A-Za-z]{6,}\b', line)
        if len(words)>1: cards.append({"q":f"What is '{words[0]}' related to in {topic}?","a":line.strip()})
    return cards

def evaluate_expression(expr):
    try: result=sp.sympify(expr); return f"✅ Result: {result} = {float(result):.4f}"
    except: return "⚠️ Invalid expression."

# FIXED UNIT CONVERTER LOGIC
def convert_units(value, from_unit, to_unit):
    conversions = {("m","cm"):100,("cm","m"):0.01,("kg","g"):1000,("g","kg"):0.001,("hr","min"):60,("min","hr"):1/60,
                   ("m","km"):0.001,("km","m"):1000,("ft","m"):0.3048,("m","ft"):3.28084,("in","cm"):2.54,("cm","in"):0.393701}
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    
    if (from_unit,to_unit) in conversions: return f"{value} {from_unit} = {value*conversions[(from_unit,to_unit)]:.4f} {to_unit}"
    return f"⚠️ Conversion not supported between '{from_unit}' and '{to_unit}'."
# END FIXED UNIT CONVERTER LOGIC

def get_weather(city):
    try:
        geo=requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1").json()
        if not geo.get("results"): return "⚠️ City not found."
        lat, lon=geo["results"][0]["latitude"], geo["results"][0]["longitude"]
        weather=requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
        info=weather.get("current_weather",{})
        return f"🌤 Temp: {info.get('temperature')}°C, Windspeed: {info.get('windspeed')} km/h, Latitude: {lat}, Longitude: {lon}"
    except: return "⚠️ Unable to fetch weather."

# ------------------------------
# Function to generate rainbow tool heading
# ------------------------------
def display_tool_heading(title):
    # Use h2 and the custom class 'tool-heading' which has the rainbow effect
    st.markdown(f'<h2 class="tool-heading">{title}</h2>', unsafe_allow_html=True)
    st.markdown("---") # Separator after the tool heading

# ------------------------------
# Sidebar Navigation (with Rainbow Heading)
# ------------------------------
st.sidebar.markdown("<h1>📚 Navigate</h1>", unsafe_allow_html=True) 
page=st.sidebar.radio(
    "",
    ["🏠 Home","🧠 Explain Topic","🎯 Quiz Generator","🃏 Flashcards",
     "🧮 Calculator","🔄 Unit Converter","🌦 Weather","🧘 Meditation Timer","📊 Daily Dashboard","📝 Notes"]
)

st.markdown("<h1> Study Buddy</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center;'>Your smart academic assistant for learning made simple.</h3>", unsafe_allow_html=True)

# ------------------------------
# Pages Implementation
# ------------------------------
if page=="🏠 Home":
    st.write("Welcome! Use the sidebar to explore features.")

elif page=="🧠 Explain Topic":
    display_tool_heading("🧠 Topic Explainer")
    topic=st.text_input("Enter a topic to explain:")
    if topic:
        summary=summarize_topic(topic)
        st.markdown(summary)
        st.session_state.topics_today[topic]=summary

elif page == "🎯 Quiz Generator":
    display_tool_heading("🎯 Quiz Generator")
    if not st.session_state.topics_today:
        st.info("Explore topics first (on the 'Explain Topic' page) to generate quiz questions!")
    else:
        if not st.session_state.quiz_questions:
            st.session_state.quiz_questions = generate_quiz_questions(st.session_state.topics_today, total_questions=10)
            st.session_state.quiz_index = 0
            
        if not st.session_state.quiz_questions:
            st.warning("⚠️ Could not generate quiz questions from the topics covered. Try exploring more detailed topics.")
        else:
            current_q_index = st.session_state.quiz_index % len(st.session_state.quiz_questions)
            q = st.session_state.quiz_questions[current_q_index]
            
            st.markdown(f"**Question {current_q_index + 1} of {len(st.session_state.quiz_questions)}**")
            st.markdown(f"**Topic:** {q['topic']}")
            st.markdown(f"**Q:** {q['question']}")

            with st.form(key=f"quiz_form_{current_q_index}"):
                selected_option = st.radio("Select your answer:", q['options'], key=f"quiz_radio_{current_q_index}")
                attempt_key = f"q_attempt_{current_q_index}"
                
                if attempt_key not in st.session_state:
                    st.session_state[attempt_key] = {"attempted": False, "correct": False, "answer": q['answer']}
                
                submitted = st.form_submit_button("Submit Answer", disabled=st.session_state[attempt_key]["attempted"])
                
                if submitted and not st.session_state[attempt_key]["attempted"]:
                    st.session_state.quiz_count += 1
                    st.session_state[attempt_key]["attempted"] = True
                    if selected_option == q['answer']:
                        st.session_state.quiz_score += 1
                        st.session_state[attempt_key]["correct"] = True
                        st.success("🎉 Correct!")
                    else:
                        st.error(f"❌ Wrong! Correct answer: {q['answer']}")
                    st.rerun()

            if st.session_state[attempt_key]["attempted"]:
                if st.session_state[attempt_key]["correct"]:
                    st.success("🎉 Correct!")
                else:
                    st.error(f"❌ Wrong! Correct answer: {q['answer']}")
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Previous", key="prev_q"):
                    st.session_state.quiz_index = (st.session_state.quiz_index - 1) % len(st.session_state.quiz_questions)
                    st.rerun()
            with col2:
                if st.button("➡️ Next", key="next_q"):
                    st.session_state.quiz_index = (st.session_state.quiz_index + 1) % len(st.session_state.quiz_questions)
                    st.rerun()
            
            st.markdown("---")
            st.info(f"Overall Score: {st.session_state.quiz_score}/{st.session_state.quiz_count}")

            if st.button("Reset Quiz", key="reset_quiz_all"):
                st.session_state.quiz_questions = []
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_count = 0
                for key in list(st.session_state.keys()):
                    if key.startswith("q_attempt_"):
                        del st.session_state[key]
                st.rerun()


elif page=="🃏 Flashcards":
    display_tool_heading("🃏 Flashcard Generator")
    if not st.session_state.topics_today: st.info("⚠️ Explore topics first!")
    else:
        if "flashcards" not in st.session_state or not st.session_state.flashcards:
            cards=[]
            for topic, summary in st.session_state.topics_today.items():
                cards.extend(generate_flashcards_from_summary(summary, topic))
            st.session_state.flashcards=cards
        for idx, card in enumerate(st.session_state.flashcards):
            with st.expander(card["q"]): st.write(card["a"])

elif page=="🧮 Calculator":
    display_tool_heading("🧮 Math Calculator")
    expr=st.text_input("Enter mathematical expression: (e.g., 2*pi + sqrt(9))")
    if expr: st.write(evaluate_expression(expr))

# FIXED Unit Converter Page Logic (handles '10m to cm')
elif page=="🔄 Unit Converter":
    display_tool_heading("🔄 Unit Converter")
    st.markdown("Enter conversion in the format: `<value><from_unit> to <to_unit>`")
    st.markdown("Example: **10m to cm** (or: **5 kg to g**)")
    user_input=st.text_input("Try a conversion:")
    
    if user_input:
        try:
            # FIX: Use regex to handle '10m' without a space between value and unit.
            # Pattern: (number)(unit)\s*to\s*(unit)
            match = re.search(r'(\d*\.?\d+)\s*([a-zA-Z]+)\s*to\s*([a-zA-Z]+)', user_input.lower())
            
            if match:
                # Group 1 is the number (value)
                # Group 2 is the first unit
                # Group 3 is the second unit
                val = float(match.group(1))
                from_unit = match.group(2)
                to_unit = match.group(3)
                st.write(convert_units(val, from_unit, to_unit))
            else:
                st.write("⚠️ Invalid input format. Please use the format: `<value><from_unit> to <to_unit>` (e.g., **10m to cm** or **10 m to cm**).")

        except ValueError:
            st.write("⚠️ Invalid value entered. Ensure `<value>` is a number.")
        except Exception:
            st.write("⚠️ An unexpected error occurred. Check format and units.")

elif page=="🌦 Weather":
    display_tool_heading("🌦 Weather Look-up")
    city=st.text_input("Enter city name: (e.g., London)")
    if city: st.write(get_weather(city))

# ------------------------------
# Page 6: Meditation Timer
# ------------------------------
elif page == "🧘 Meditation Timer":
    display_tool_heading("🧘 Meditation Timer")
    
    minutes = st.number_input("Set Timer (minutes):", min_value=1, max_value=120, value=5)

    timer_placeholder = st.empty()

    if st.button("Start Timer", disabled=st.session_state.timer_running):
        st.session_state.timer_running = True
        st.info("Meditation in progress...")

        for i in range(minutes * 60, 0, -1):
            mins, secs = divmod(i, 60)
            timer_placeholder.markdown(f"## ⏰ {mins:02d}:{secs:02d}", unsafe_allow_html=True)
            time.sleep(1)

        st.balloons()
        st.success("✅ Time's up! Great job!")
        st.session_state.meditation_minutes += minutes
        st.session_state.timer_running = False


# ------------------------------
# Page 7: Daily Dashboard
# ------------------------------
elif page == "📊 Daily Dashboard":
    display_tool_heading("📊 Daily Dashboard")
    
    st.subheader("🗓️ Daily Progress Summary")
    
    col_t, col_q, col_m = st.columns(3)
    
    with col_t:
        st.subheader("📚 Topics")
        st.metric("Total Topics Covered", len(st.session_state.topics_today), delta="/10 target")

    with col_q:
        st.subheader("📝 Quiz")
        accuracy = (st.session_state.quiz_score / st.session_state.quiz_count * 100) if st.session_state.quiz_count > 0 else 0
        st.metric("Accuracy", f"{accuracy:.1f}%")

    with col_m:
        st.subheader("🧘 Meditation")
        st.metric("Minutes Meditated", st.session_state.meditation_minutes, delta="/30 min target")

    st.markdown("---")
    
    st.subheader("📝 Quiz Breakdown")
    st.metric("Questions Attempted", st.session_state.quiz_count)
    st.metric("Correct Answers", st.session_state.quiz_score)

    st.markdown("---")
    
    st.subheader("📚 Topics Covered")
    if st.session_state.topics_today:
        topic_list = "\n".join([f"- **{t}**" for t in st.session_state.topics_today.keys()])
        st.markdown(topic_list)
    else:
        st.info("No topics covered yet today.")

    st.markdown("---")
    
    st.subheader("🧘 Meditation Goal Status")
    if st.session_state.meditation_minutes >= 30:
        st.success(f"🎯 Daily meditation goal reached! Total minutes: {st.session_state.meditation_minutes}")
    else:
        remaining = 30 - st.session_state.meditation_minutes
        st.info(f"🕒 You need {remaining} more minutes to reach your daily meditation goal.")

elif page=="📝 Notes":
    display_tool_heading("📝 Study Notes")
    note=st.text_area("Write your study notes here:")
    if st.button("Save Note"): st.success("📝 Note saved!")

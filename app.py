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
st.set_page_config(page_title="AI-Powered Study Buddy", layout="wide")

# ------------------------------
# CSS Effects
# ------------------------------
st.markdown("""
<style>
h1 {text-align:center;font-size:50px;animation: rainbow 5s infinite;}
@keyframes rainbow {
0% {color: red;} 16% {color: orange;} 33% {color: yellow;} 50% {color: green;}
66% {color: blue;} 83% {color: indigo;} 100% {color: violet;}
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

def generate_quiz_from_summary(summary, topic):
    words = [w for w in re.findall(r'\b[A-Za-z]{6,}\b', summary)]
    random.shuffle(words)
    selected = words[:4] if len(words)>=4 else words
    quiz=[]
    for i, w in enumerate(selected):
        question = f"Q{i+1}. What is related to '{w}' in {topic}?"
        options = random.sample(selected, len(selected))
        quiz.append({"q":question,"opts":options,"ans":w})
    return quiz

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

def convert_units(value, from_unit, to_unit):
    conversions = {
        ("m","cm"):100,("cm","m"):0.01,("kg","g"):1000,("g","kg"):0.001,
        ("hr","min"):60,("min","hr"):1/60,("m","km"):0.001,("km","m"):1000,
        ("ft","m"):0.3048,("m","ft"):3.28084,("in","cm"):2.54,("cm","in"):0.393701
    }
    if (from_unit,to_unit) in conversions: return f"{value} {from_unit} = {value*conversions[(from_unit,to_unit)]:.4f} {to_unit}"
    return "⚠️ Conversion not supported."

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
# Sidebar Navigation
# ------------------------------
page=st.sidebar.radio(
    "📚 Navigate",
    ["🏠 Home","🧠 Explain Topic","🎯 Quiz Generator","🃏 Flashcards",
     "🧮 Calculator","🔄 Unit Converter","🌦 Weather","🧘 Meditation Timer","📊 Daily Dashboard","📝 Notes"]
)

st.markdown("<h1> Study Buddy", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center;'>Your smart academic assistant for learning made simple.</h3>", unsafe_allow_html=True)

# ------------------------------
# Pages Implementation
# ------------------------------
if page=="🏠 Home": st.write("Welcome! Use the sidebar to explore features.")
elif page=="🧠 Explain Topic":
    topic=st.text_input("Enter a topic to explain:")
    if topic:
        summary=summarize_topic(topic)
        st.markdown(summary)
        st.session_state.topics_today[topic]=summary
elif page=="🎯 Quiz Generator":
    if not st.session_state.topics_today: st.info("⚠️ Explore topics first!")
    else:
        if "dynamic_quiz" not in st.session_state: st.session_state.dynamic_quiz=[]
        if not st.session_state.dynamic_quiz:
            questions=[]
            for topic, summary in st.session_state.topics_today.items():
                questions.extend(generate_quiz_from_summary(summary, topic))
            random.shuffle(questions)
            st.session_state.dynamic_quiz=questions
        q_idx=st.session_state.get("quiz_idx",0)%len(st.session_state.dynamic_quiz)
        q_data=st.session_state.dynamic_quiz[q_idx]
        st.markdown(f"**Question {q_idx+1}/{len(st.session_state.dynamic_quiz)}**")
        st.markdown(f"**{q_data['q']}**")
        choice_selected=st.radio("Select your answer:", q_data["opts"], key=f"quiz_{q_idx}")
        attempt_key=f"attempt_{q_idx}"
        if attempt_key not in st.session_state: st.session_state[attempt_key]={"done":False,"correct":False}
        if st.button("Submit Answer", key=f"submit_{q_idx}", disabled=st.session_state[attempt_key]["done"]):
            st.session_state[attempt_key]["done"]=True
            st.session_state["quiz_count"]+=1
            if choice_selected==q_data["ans"]:
                st.session_state["quiz_score"]+=1
                st.session_state[attempt_key]["correct"]=True
                st.success("✅ Correct!")
            else: st.error(f"❌ Wrong! Correct answer: {q_data['ans']}")
            st.rerun()
        col1,col2=st.columns(2)
        with col1:
            if st.button("⬅️ Previous", key="prev_q"): st.session_state["quiz_idx"]=(q_idx-1)%len(st.session_state.dynamic_quiz); st.rerun()
        with col2:
            if st.button("➡️ Next", key="next_q"): st.session_state["quiz_idx"]=(q_idx+1)%len(st.session_state.dynamic_quiz); st.rerun()
        st.markdown(f"**Overall Score:** {st.session_state['quiz_score']}/{st.session_state['quiz_count']}")
elif page=="🃏 Flashcards":
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
    expr=st.text_input("Enter mathematical expression:")
    if expr: st.write(evaluate_expression(expr))
elif page=="🔄 Unit Converter":
    user_input=st.text_input("Format: <value> <from_unit> to <to_unit>")
    if user_input:
        try:
            val, from_unit, _, to_unit=user_input.split()
            val=float(val)
            st.write(convert_units(val, from_unit, to_unit))
        except: st.write("⚠️ Invalid input format.")
elif page=="🌦 Weather":
    city=st.text_input("Enter city name:")
    if city: st.write(get_weather(city))
elif page=="🧘 Meditation Timer":
    minutes=st.number_input("Set Timer (minutes):", min_value=1,max_value=120,value=5)
    if st.button("Start Timer", disabled=st.session_state.timer_running):
        st.session_state.timer_running=True
        placeholder=st.empty()
        for i in range(minutes*60,0,-1):
            m,s=divmod(i,60)
            placeholder.markdown(f"## ⏰ {m:02d}:{s:02d}")
            time.sleep(1)
        st.balloons()
        st.success(f"✅ You meditated for {minutes} minutes!")
        st.session_state.meditation_minutes+=minutes
        today=str(datetime.date.today())
        found=False
        for entry in st.session_state.meditation_history:
            if entry["date"]==today:
                entry["minutes"]+=minutes; found=True
        if not found: st.session_state.meditation_history.append({"date":today,"minutes":minutes})
        st.session_state.timer_running=False
        st.rerun()
elif page=="📊 Daily Dashboard":
    st.subheader("📊 Daily Dashboard")
    st.metric("Topics Covered Today", len(st.session_state.topics_today))
    st.metric("Meditation Minutes Today", st.session_state.meditation_minutes)
    st.metric("Quiz Score", f"{st.session_state.quiz_score}/{st.session_state.quiz_count}")
    st.write("📚 Topics:", list(st.session_state.topics_today.keys()))
    st.write("🕰 Meditation History:", st.session_state.meditation_history)
elif page=="📝 Notes":
    note=st.text_area("Write your study notes here:")
    if st.button("Save Note"): st.success("📝 Note saved!")

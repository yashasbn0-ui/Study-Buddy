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
st.set_page_config(page_title="AI-Powered Study Buddy 💡", page_icon="💡", layout="wide")

# ------------------------------
# CSS Effects
# ------------------------------
st.markdown("""
<style>
h1 {
    text-align:center;
    font-size:50px;
    animation: rainbow 5s infinite;
}
@keyframes rainbow {
    0% {color: red;}
    16% {color: orange;}
    33% {color: yellow;}
    50% {color: green;}
    66% {color: blue;}
    83% {color: indigo;}
    100% {color: violet;}
}
input, textarea, select {
    border: 4px solid;
    border-radius: 10px;
    padding: 8px;
    font-weight: bold;
    font-size: 16px;
    color: #111;
    box-shadow: 0 0 10px #ff00ff, 0 0 20px #00ffff, 0 0 30px #ffff00;
}
button {
    border: none;
    border-radius: 10px;
    padding: 8px 15px;
    font-weight: bold;
    font-size: 16px;
    cursor: pointer;
    box-shadow: 0 0 10px #ff00ff, 0 0 20px #00ffff, 0 0 30px #ffff00;
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
# Session State
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
def fetch_wikipedia(topic):
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(topic, sentences=6)
    except:
        return None

def fetch_wolfram(topic):
    for _ in range(len(wolfram_keys)):
        key = get_next_wolfram_key()
        try:
            url = f"https://api.wolframalpha.com/v1/result?appid={key}&i={requests.utils.quote(topic)}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200 and "no result found" not in r.text.lower():
                return r.text.strip()
        except:
            continue
    return None

def explain_topic(topic):
    wiki = fetch_wikipedia(topic)
    wolfram = fetch_wolfram(topic)
    if wiki and wolfram:
        return f"**📘 Wikipedia:**\n{wiki}\n\n**🔹 Wolfram:** {wolfram}"
    elif wiki: return f"**📘 Wikipedia:**\n{wiki}"
    elif wolfram: return f"**🔹 Wolfram:** {wolfram}"
    return "⚠️ No explanation found."

def subject_summary(topic, subject):
    wiki = fetch_wikipedia(topic)
    wolfram = fetch_wolfram(topic)
    text = (wiki or "") + "\n" + (wolfram or "")
    text = re.sub(r'\([^)]*\)', '', text)
    text = ' '.join(text.split()[:120])
    return f"### 🧠 {subject} Summary for **{topic.title()}**\n\n{textwrap.fill(text,95)}"

def generate_quiz(topic):
    summary = fetch_wikipedia(topic)
    if not summary: return ["⚠️ Not enough data for quiz."]
    words = [w for w in re.findall(r'\b[A-Za-z]{6,}\b', summary)]
    random.shuffle(words)
    selected = words[:4]
    quiz = []
    for i, w in enumerate(selected):
        question = f"Q{i+1}. What does '{w}' relate to in {topic}?"
        options = random.sample(selected, len(selected))
        quiz.append((question, options, w))
    return quiz

def generate_flashcards(topic):
    summary = fetch_wikipedia(topic)
    if not summary: return []
    lines = summary.split(".")
    cards = []
    for line in lines[:5]:
        words = re.findall(r'\b[A-Za-z]{6,}\b', line)
        if len(words)>1:
            cards.append((f"What is '{words[0]}' related to?", line.strip()))
    return cards

def evaluate_expression(expr):
    try:
        result = sp.sympify(expr)
        return f"✅ Result: {result} = {float(result):.4f}"
    except:
        return "⚠️ Invalid expression."

def convert_units(value, from_unit, to_unit):
    conversions = {("m","cm"):100,("cm","m"):0.01,("kg","g"):1000,("g","kg"):0.001,("hr","min"):60,("min","hr"):1/60}
    if (from_unit,to_unit) in conversions:
        return f"{value} {from_unit} = {value*conversions[(from_unit,to_unit)]} {to_unit}"
    return "⚠️ Conversion not supported."

def get_weather(city):
    try:
        geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1").json()
        if not geo.get("results"): return "⚠️ City not found."
        lat, lon = geo["results"][0]["latitude"], geo["results"][0]["longitude"]
        weather = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
        info = weather.get("current_weather", {})
        return f"🌤 Temperature: {info.get('temperature')}°C, Windspeed: {info.get('windspeed')} km/h"
    except:
        return "⚠️ Unable to fetch weather."

# ------------------------------
# Sidebar Navigation
# ------------------------------
page = st.sidebar.radio(
    "📚 Navigate",
    ["🏠 Home","🧠 Explain Topic","📘 Subject Summarizer","🎯 Quiz Generator","🃏 Flashcards",
     "🧮 Calculator","🔄 Unit Converter","🌦 Weather","🧘 Meditation Timer","📊 Daily Dashboard","📝 Notes"]
)

# ------------------------------
# Header
# ------------------------------
st.markdown("<h1>AI-Powered Study Buddy 💡</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center;'>Your smart academic assistant for learning made simple.</h3>", unsafe_allow_html=True)

# ------------------------------
# Pages Implementation
# ------------------------------

# Home Page
if page=="🏠 Home":
    st.write("Welcome! Use the sidebar to explore features: Explain Topic, Summarizer, Quiz, Flashcards, Calculator, Converter, Weather, Meditation, Dashboard, Notes.")

# Explain Topic
elif page=="🧠 Explain Topic":
    topic = st.text_input("Enter a topic to explain:")
    if topic:
        result = explain_topic(topic)
        st.markdown(result)
        st.session_state.topics_today[topic] = result

# Subject Summarizer
elif page=="📘 Subject Summarizer":
    subject = st.selectbox("Select Subject:", ["Chemistry","Biology","Physics","History","Math"])
    topic = st.text_input(f"Enter {subject} topic:")
    if topic:
        summary = subject_summary(topic, subject)
        st.markdown(summary)
        st.session_state.topics_today[topic] = summary

# ------------------------------
# Quiz Generator (Dynamic)
# ------------------------------
elif page=="🎯 Quiz Generator":
    if not st.session_state.topics_today:
        st.info("⚠️ Explore some topics first to generate a quiz!")
    else:
        if "dynamic_quiz" not in st.session_state:
            st.session_state.dynamic_quiz = []

        # Generate quiz if empty
        if not st.session_state.dynamic_quiz:
            questions = []
            for topic, summary in st.session_state.topics_today.items():
                # Extract words >5 chars for blanks
                words = [w for w in re.findall(r'\b[A-Za-z]{6,}\b', summary)]
                random.shuffle(words)
                selected = words[:4] if len(words)>=4 else words
                for i, w in enumerate(selected):
                    question_text = f"Q{i+1}. What is related to '{w}' in {topic}?"
                    options = random.sample(selected, len(selected))
                    questions.append({"q": question_text, "opts": options, "ans": w})
            random.shuffle(questions)
            st.session_state.dynamic_quiz = questions

        # Show current question
        q_idx = st.session_state.get("quiz_idx", 0) % len(st.session_state.dynamic_quiz)
        q_data = st.session_state.dynamic_quiz[q_idx]

        st.markdown(f"**Question {q_idx+1}/{len(st.session_state.dynamic_quiz)}**")
        st.markdown(f"**{q_data['q']}**")

        choice_selected = st.radio("Select your answer:", q_data["opts"], key=f"quiz_{q_idx}")

        attempt_key = f"attempt_{q_idx}"
        if attempt_key not in st.session_state:
            st.session_state[attempt_key] = {"done": False, "correct": False}

        if st.button("Submit Answer", key=f"submit_{q_idx}", disabled=st.session_state[attempt_key]["done"]):
            st.session_state[attempt_key]["done"] = True
            st.session_state["quiz_count"] += 1
            if choice_selected == q_data["ans"]:
                st.session_state["quiz_score"] += 1
                st.session_state[attempt_key]["correct"] = True
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q_data['ans']}")
            st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Previous", key="prev_q"):
                st.session_state["quiz_idx"] = (q_idx - 1) % len(st.session_state.dynamic_quiz)
                st.rerun()
        with col2:
            if st.button("➡️ Next", key="next_q"):
                st.session_state["quiz_idx"] = (q_idx + 1) % len(st.session_state.dynamic_quiz)
                st.rerun()

        st.markdown(f"**Overall Score:** {st.session_state['quiz_score']}/{st.session_state['quiz_count']}")


# ------------------------------
# Flashcards (Dynamic)
# ------------------------------
elif page=="🃏 Flashcards":
    if not st.session_state.topics_today:
        st.info("⚠️ Explore some topics first to generate flashcards!")
    else:
        if "flashcards" not in st.session_state or not st.session_state.flashcards:
            cards = []
            for topic, summary in st.session_state.topics_today.items():
                lines = summary.split(".")
                for line in lines[:5]:
                    words = re.findall(r'\b[A-Za-z]{6,}\b', line)
                    if len(words) > 1:
                        cards.append({"q": f"What is '{words[0]}' related to in {topic}?", "a": line.strip()})
            st.session_state.flashcards = cards

        for idx, card in enumerate(st.session_state.flashcards):
            with st.expander(card["q"]):
                st.write(card["a"])


# Calculator
elif page=="🧮 Calculator":
    expr = st.text_input("Enter mathematical expression:")
    if expr:
        st.write(evaluate_expression(expr))

# Unit Converter
elif page=="🔄 Unit Converter":
    user_input = st.text_input("Format: <value> <from_unit> to <to_unit>")
    if user_input:
        try:
            val, from_unit, _, to_unit = user_input.split()
            val = float(val)
            st.write(convert_units(val, from_unit, to_unit))
        except:
            st.write("⚠️ Invalid input format.")

# Weather
elif page=="🌦 Weather":
    city = st.text_input("Enter city name:")
    if city:
        st.write(get_weather(city))

# Meditation Timer
elif page=="🧘 Meditation Timer":
    minutes = st.number_input("Set Timer (minutes):", min_value=1, max_value=120, value=5)
    if st.button("Start Timer", disabled=st.session_state.timer_running):
        st.session_state.timer_running=True
        placeholder = st.empty()
        for i in range(minutes*60,0,-1):
            m,s = divmod(i,60)
            placeholder.markdown(f"## ⏰ {m:02d}:{s:02d}")
            time.sleep(1)
        st.balloons()
        st.success(f"✅ You meditated for {minutes} minutes!")
        st.session_state.meditation_minutes += minutes
        today = str(datetime.date.today())
        found=False
        for entry in st.session_state.meditation_history:
            if entry["date"]==today:
                entry["minutes"]+=minutes
                found=True
        if not found:
            st.session_state.meditation_history.append({"date":today,"minutes":minutes})
        st.session_state.timer_running=False
        st.rerun()

# Daily Dashboard
elif page=="📊 Daily Dashboard":
    st.subheader("📊 Daily Dashboard")
    st.metric("Topics Covered Today", len(st.session_state.topics_today))
    st.metric("Meditation Minutes Today", st.session_state.meditation_minutes)
    st.metric("Quiz Score", f"{st.session_state.quiz_score}/{st.session_state.quiz_count}")
    st.write("📚 Topics:", list(st.session_state.topics_today.keys()))
    st.write("🕰 Meditation History:", st.session_state.meditation_history)

# Notes
elif page=="📝 Notes":
    note = st.text_area("Write your study notes here:")
    if st.button("Save Note"):
        st.success("📝 Note saved!")

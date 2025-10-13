import streamlit as st
import wikipedia
import numpy as np
import sympy as sp
import datetime
import re
import requests
import json
from random import choice, sample, shuffle
import time


st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")


WOLFRAM_APP_ID = "8L5YE636JU" 

APP_ID_2="3KRR2XR9J2"

if "topics_today" not in st.session_state:
    st.session_state.topics_today = {}
if "last_reset" not in st.session_state:
    st.session_state.last_reset = datetime.date.today()
# Daily reset of topics
if st.session_state.last_reset != datetime.date.today():
    st.session_state.topics_today = {}
    st.session_state.last_reset = datetime.date.today()
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_count" not in st.session_state:
    st.session_state.quiz_count = 0
if "meditation_minutes" not in st.session_state:
    st.session_state.meditation_minutes = 0
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False


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
button:hover {
    transform: scale(1.05);
}
.correct {background-color: #b6f0b6; padding: 5px; border-radius: 5px;}
.wrong {background-color: #f0b6b6; padding: 5px; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)


def get_wikipedia_summary(topic):
    try:
        
        if topic in ["Greetings", "History of greetings", "Hello", "Farewell", "Goodbye", "Saying goodbye", "Parting words"]:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(topic, sentences=5) # Use fewer sentences for conversational
            return summary
        
        
        if topic in st.session_state.topics_today:
            return st.session_state.topics_today[topic]

        wikipedia.set_lang("en")
        summary = wikipedia.summary(topic, sentences=10)
        st.session_state.topics_today[topic] = summary
        return summary
    except wikipedia.exceptions.PageError:
        return None
    except wikipedia.exceptions.DisambiguationError:
        
        try:
            suggested_topic = wikipedia.search(topic)[0]
            summary = wikipedia.summary(suggested_topic, sentences=10)
            st.session_state.topics_today[topic] = summary
            return summary
        except:
            return None
    except Exception:
        return None

def get_wolfram_result(topic):
    if not WOLFRAM_APP_ID or WOLFRAM_APP_ID == "3KRR2XR9J2":
        return None
    try:
        # 
        url = f"http://api.wolframalpha.com/v1/result?appid={WOLFRAM_APP_ID}&i={topic}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.text.strip().lower() != "no result found":
            return r.text.strip()
    except:
        return None
    return None

def fetch_summary(topic):
    # Try Wikipedia first
    summary = get_wikipedia_summary(topic)
    if summary:
        return f"**Source: Wikipedia**\n\n{summary}"
    
    wolfram = get_wolfram_result(topic)
    if wolfram:
        return f"**Source: WolframAlpha**\n\n{wolfram}"
        
    return "⚠️ Sorry, no relevant data found on Wikipedia or WolframAlpha."

def get_open_meteo_weather(city_name):
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    
    try:
        r_geo = requests.get(geocode_url, timeout=10)
        r_geo.raise_for_status() # Raise exception for bad status codes
        
        geo_data = r_geo.json()
        if not geo_data.get('results'):
            return "⚠️ City not found in geocoding service."

        result = geo_data['results'][0]
        latitude = result['latitude']
        longitude = result['longitude']
        display_name = f"{result.get('name', city_name)}, {result.get('country', '')}"

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&"
            f"current=temperature_2m,weather_code,wind_speed_10m&"
            f"temperature_unit=celsius&wind_speed_unit=kmh&"
            f"forecast_days=1"
        )
        
        r_weather = requests.get(weather_url, timeout=10)
        r_weather.raise_for_status()
        weather_data = r_weather.json()
        
        current = weather_data['current']
        
        weather_code = current['weather_code']
        weather_description = "Clear Sky ☀️"
        if 1 <= weather_code <= 3:
            weather_description = "Partly Cloudy 🌥️"
        elif 51 <= weather_code <= 65:
            weather_description = "Rain 🌧️"
        elif 71 <= weather_code <= 75:
            weather_description = "Snow ❄️"
        elif 95 == weather_code:
            weather_description = "Thunderstorm ⛈️"
            
        
        return (
            f"📍 **Location:** {display_name} (Lat: {latitude:.2f}, Lon: {longitude:.2f})\n\n"
            f"**Current Weather:**\n"
            f"- **Temperature:** {current['temperature_2m']} °C\n"
            f"- **Condition:** {weather_description}\n"
            f"- **Wind Speed:** {current['wind_speed_10m']} km/h"
        )

    except requests.exceptions.RequestException as e:
        return f"⚠️ Error fetching weather data: {e}"
    except Exception as e:
        return f"⚠️ An unexpected error occurred: {e}"



def get_conversational_response(user_input):
    user_input_lower = user_input.lower().strip()
    if not user_input_lower:
        return None

    farewells = ["bye", "goodbye", "see you", "farewell", "good night", "take care"]
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    
    farewell_regex = r"\b(" + "|".join(re.escape(f) for f in farewells) + r")\b"
    greeting_regex = r"\b(" + "|".join(re.escape(g) for g in greetings) + r")\b"

    if re.search(farewell_regex, user_input_lower):
        topics = ["Farewell", "Goodbye", "Saying goodbye", "Parting words"]
        for topic in topics:
            summary = get_wikipedia_summary(topic)
            if summary:
                return f"**You said:** {user_input}\n\n**Here's something interesting about farewells:**\nFarewell rituals often symbolize closure and hope for future encounters. They can range from simple waves to elaborate ceremonies, reflecting cultural norms around separation and reunion. {summary.split('.')[0]}."
        return "👋 Goodbye! Take care!"
    
    elif re.search(greeting_regex, user_input_lower):
        topics = ["Greetings", "History of greetings", "Hello"]
        for topic in topics:
            summary = get_wikipedia_summary(topic)
            if summary:
                # Using the exact snippet from the image for consistency
                return f"**You said:** {user_input}\n\n**Did you know?** Greeting is an act of communication in which human beings intentionally make their presence known to each other, to show attention to, and to suggest a type of relationship (usually cordial) or social status (formal or informal) between individuals or groups of people coming in contact with each other. Greetings are sometimes just used prior to a conversation or to greet in passing, such as on a sidewalk or trail. While greeting customs are highly culture- and situation-specific and may change within a culture depending on social status and relationship, they exist in all known human cultures. Greetings can be expressed both audibly and physically, and often involve a combination of the two. This topic excludes military and ceremonial salutes but includes rituals other than gestures. A greeting, or salutation, can also be expressed in written communications, such as letters and emails. Some epochs and cultures have had very elaborate greeting rituals, e.g. greeting a sovereign. Conversely, secret societies have often furtive or arcane greeting gestures and rituals, such as a secret handshake, which allows members to recognize each other. In some languages and cultures, the word or gesture is used as both greeting and farewell."
                
        return f"Hello! How can I assist you today?"
    
    return None


def unit_converter(query):
    conversion_match = re.search(r"([-+]?\d*\.?\d+)\s*([a-z°]+)\s*to\s*([a-z°]+)", query.lower().replace(" ", ""))
    if not conversion_match:
        return None 

    value, from_unit, to_unit = conversion_match.groups()
    try:
        value = float(value)
    except:
        return "⚠️ Invalid numeric value."

    conversions = {
        # Length
        ("m", "km"): lambda x: x/1000, ("km", "m"): lambda x: x*1000,
        ("cm", "m"): lambda x: x/100, ("m", "cm"): lambda x: x*100,
        ("mm", "m"): lambda x: x/1000, ("m", "mm"): lambda x: x*1000,
        ("m", "ft"): lambda x: x*3.28084, ("ft", "m"): lambda x: x/3.28084,
        ("in", "cm"): lambda x: x*2.54, ("cm", "in"): lambda x: x/2.54,
        ("ft", "in"): lambda x: x*12, ("in", "ft"): lambda x: x/12,
        # Temperature
        ("°c", "°f"): lambda x: (x*9/5)+32, ("°f", "°c"): lambda x: (x-32)*5/9,
        # Weight
        ("kg", "g"): lambda x: x*1000, ("g", "kg"): lambda x: x/1000,
        ("kg", "lb"): lambda x: x*2.20462, ("lb", "kg"): lambda x: x/2.20462,
        ("oz", "g"): lambda x: x*28.3495, ("g", "oz"): lambda x: x/28.3495,
        ("lb", "oz"): lambda x: x*16, ("oz", "lb"): lambda x: x/16,
        # Time
        ("hours", "minutes"): lambda x: x*60, ("minutes", "hours"): lambda x: x/60,
    }

    func = conversions.get((from_unit, to_unit))
    if func:
        result = func(value)
        return f"{value} {from_unit} = {result:.4f} {to_unit}"
    else:
        return f"⚠️ Conversion from '{from_unit}' to '{to_unit}' not supported."


def generate_fill_in_blank(summary):
    sentences = [s.strip() for s in re.split(r'[.!?]', summary) if s.strip()]
    if not sentences:
        return None
    
    suitable_sentences = [s for s in sentences if len(s.split()) > 8]
    if not suitable_sentences:
        return None
        
    sentence = choice(suitable_sentences)
    
    words = [w.strip(".,;") for w in sentence.split()]
    potential_answers = [
        w.strip(".,;") for w in words
        if w and w[0].isupper() and w not in ["A", "The", "An", "In", "On", "Of", "For", "With", "He", "She", "It"]
        and w != words[0].strip(".,;") 
    ]
    
    if not potential_answers:
          potential_answers = [w.strip(".,;") for w in words if len(w) > 5]

    if not potential_answers:
        return None

    answer = choice(potential_answers)
    
    blank_sentence = re.sub(r'\b' + re.escape(answer) + r'\b', '_____', sentence, flags=re.IGNORECASE)
    
    all_words = [w.strip(".,;").lower() for s in st.session_state.topics_today.values() for w in s.split()]
    unique_words = list(set(w for w in all_words if len(w) > 3 and w.lower() != answer.lower()))
    
    distractors = sample(unique_words, min(3, len(unique_words)))
    
    distractor_options = [d.capitalize() for d in distractors]
    
    options = [answer] + distractor_options
    shuffle(options)
    
    return blank_sentence + "?", answer, options

def generate_quiz_questions(topics_dict, total_questions=10):
    questions = []
    all_summaries = list(topics_dict.items())
    topic_idx = 0

    while len(questions) < total_questions and all_summaries and topic_idx < 100 * len(all_summaries):
        topic, summary = all_summaries[topic_idx % len(all_summaries)]
        q = generate_fill_in_blank(summary)
        if q:
            blank_sentence, answer, options = q
            if not any(d["question"] == blank_sentence for d in questions):
                questions.append({"topic": topic, "question": blank_sentence, "answer": answer, "options": options})
        topic_idx += 1
        
    shuffle(questions)
    return questions[:total_questions]

# ------------------------------
# Sidebar Navigation (Updated)
# ------------------------------
st.sidebar.title("🧭 Study Buddy Menu")
page = st.sidebar.radio("Choose a page:", [
    "📚 Topic Summary", 
    "🌍 Weather & Location",
    "🧮 Scientific Calculator + Unit Converter", 
    "📝 Quiz", 
    "🧘 Meditation Timer", 
    "📊 Daily Dashboard"
])

# ------------------------------
# Page 1: Topic Summary + Conversational (Now includes all general topics/chemistry)
# ------------------------------
if page == "📚 Topic Summary":
    st.markdown("<h1>📚 Study Buddy: Topic Summary</h1>", unsafe_allow_html=True)
    st.markdown("Enter any topic, including **Chemistry concepts** (e.g., 'Methane', 'Balance $\text{H}_2 + \text{O}_2$', 'Quantum Physics') or conversation starters ('hello', 'bye').")
    
    topic_input = st.text_input("Enter a topic or query:", key="topic_input_text")
    
    if topic_input:
        with st.spinner("🔍 Gathering data..."):
            conv_response = get_conversational_response(topic_input)
            
            if conv_response:
                st.markdown(conv_response)
            else:
                summary = fetch_summary(topic_input)
                st.markdown("### 🧾 Summary")
                st.write(summary)

        st.markdown("---")
        st.subheader("📈 Progress Tracker")
        st.metric("Topics Covered Today", len(st.session_state.topics_today), delta="/ 10 target")
        if len(st.session_state.topics_today) >= 10:
            st.success("🎯 Daily goal reached!")

# ------------------------------
# Page 2: Weather & Location
# ------------------------------
elif page == "🌍 Weather & Location":
    st.markdown("<h1>🌍 Weather & Location</h1>", unsafe_allow_html=True)
    st.markdown("Get the current weather for any major city using the **Open-Meteo API**.")

    city_input = st.text_input("Enter a City Name (e.g., 'London', 'Tokyo', 'New York'):", key="city_input_text")
    
    if city_input:
        with st.spinner("☁️ Fetching weather data..."):
            weather_report = get_open_meteo_weather(city_input)
            
            st.markdown("### ☀️ Weather Report")
            st.markdown(weather_report)
            
            # Add the location as a topic covered
            st.session_state.topics_today[f"Weather in {city_input}"] = weather_report

# ------------------------------
# Page 3: Calculator + Unit Converter
# ------------------------------
elif page == "🧮 Scientific Calculator + Unit Converter":
    st.markdown("<h1>🧮 Calculator + Unit Converter</h1>", unsafe_allow_html=True)
    st.markdown("You can perform scientific calculations (e.g., `np.sin(np.pi/2)`, `sp.integrate(x**2, x)`) or quick unit conversions (e.g., '5 km to m', '10 ft to m', '70 kg to lb', '100 °C to °F').")

    calc_input = st.text_area("Enter expression or conversion:", height=150)
    
    if calc_input:
        conversion_result = unit_converter(calc_input)
        
        if conversion_result and not conversion_result.startswith("⚠️"):
            st.success("✅ Conversion Successful")
            st.code(conversion_result)
        elif conversion_result and conversion_result.startswith("⚠️"):
              st.error(conversion_result)
        else:
            # Try scientific calculation as fallback
            try:
                # Define symbols for symbolic math (SymPy)
                x, y, z = sp.symbols("x y z")
                local_env = {
                    "np": np, "sp": sp, "sin": np.sin, "cos": np.cos, "tan": np.tan,
                    "pi": np.pi, "sqrt": np.sqrt, "log": np.log, "log10": np.log10, 
                    "diff": sp.diff, "integrate": sp.integrate, "simplify": sp.simplify,
                    "limit": sp.limit, "symbols": sp.symbols, "ln": sp.ln, "exp": sp.exp,
                    "x": x, "y": y, "z": z # Inject symbols directly
                }
                
                # Use a safe environment for eval
                result = eval(calc_input, {"__builtins__": {}}, local_env)
                
                # Pretty print SymPy results
                if isinstance(result, sp.Expr) or isinstance(result, sp.matrices.common.MatrixCommon):
                    st.success("✅ Symbolic Calculation Successful (using SymPy)")
                    st.latex(sp.latex(result))
                else:
                    st.success("✅ Numeric Calculation Successful (using NumPy)")
                    st.code(f"Result: {result}", language="python")
                    
            except Exception as e:
                st.error(f"❌ Calculation Error: {e}")

# ------------------------------
# Page 4: Quiz
# ------------------------------
elif page == "📝 Quiz":
    st.markdown("<h1>📝 Dynamic Quiz!</h1>", unsafe_allow_html=True)
    if not st.session_state.topics_today:
        st.info("Explore topics first (on the 'Topic Summary' page) to generate quiz questions!")
    else:
        # Generate questions if the list is empty
        if not st.session_state.quiz_questions:
            st.session_state.quiz_questions = generate_quiz_questions(st.session_state.topics_today, total_questions=10)
            st.session_state.quiz_index = 0
            
        if not st.session_state.quiz_questions:
              st.warning("⚠️ Could not generate quiz questions from the topics covered. Try exploring more detailed topics.")
        else:
            current_q_index = st.session_state.quiz_index % len(st.session_state.quiz_questions)
            q = st.session_state.quiz_questions[current_q_index]
            
            # Use unique key for question text to prevent stale display on navigation
            st.markdown(f"**Question {current_q_index + 1} of {len(st.session_state.quiz_questions)}**")
            st.markdown(f"**Topic:** {q['topic']}")
            st.markdown(f"**Q:** {q['question']}")

            # Use a unique key for the radio button
            selected_option = st.radio("Select your answer:", q['options'], key=f"quiz_radio_{current_q_index}")
            
            # Store the state of the current question attempt
            attempt_key = f"q_attempt_{current_q_index}"
            if attempt_key not in st.session_state:
                st.session_state[attempt_key] = {"attempted": False, "correct": False, "answer": q['answer']}
            
            # Display result if already attempted
            if st.session_state[attempt_key]["attempted"]:
                if st.session_state[attempt_key]["correct"]:
                    st.success("🎉 Correct!")
                else:
                    st.error(f"❌ Wrong! Correct answer: {q['answer']}")
            
            # Submit button logic
            if st.button("Submit Answer", key=f"submit_{current_q_index}", disabled=st.session_state[attempt_key]["attempted"]):
                if selected_option:
                    # Only count the score if it's the first attempt for this question
                    if not st.session_state[attempt_key]["attempted"]:
                        st.session_state.quiz_count += 1
                        st.session_state[attempt_key]["attempted"] = True
                        
                        if selected_option == q['answer']:
                            st.session_state.quiz_score += 1
                            st.session_state[attempt_key]["correct"] = True
                            st.success("🎉 Correct!")
                        else:
                            st.error(f"❌ Wrong! Correct answer: {q['answer']}")
                        
                        # --- FIX: Use st.rerun() ---
                        st.rerun()
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                # Previous button
                if st.button("⬅️ Previous", key="prev_q"):
                    st.session_state.quiz_index = (st.session_state.quiz_index - 1) % len(st.session_state.quiz_questions)
                    # --- FIX: Use st.rerun() ---
                    st.rerun()
            with col2:
                # Next button
                if st.button("➡️ Next", key="next_q"):
                    st.session_state.quiz_index = (st.session_state.quiz_index + 1) % len(st.session_state.quiz_questions)
                    # --- FIX: Use st.rerun() ---
                    st.rerun()
            
            st.markdown("---")
            st.info(f"Overall Score: {st.session_state.quiz_score}/{st.session_state.quiz_count}")

            # Reset Quiz button (separate from the rest)
            if st.button("Reset Quiz", key="reset_quiz_all"):
                st.session_state.quiz_questions = []
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_count = 0
                # Clear all question attempt states
                for key in list(st.session_state.keys()):
                    if key.startswith("q_attempt_"):
                        del st.session_state[key]
                # --- FIX: Use st.rerun() ---
                st.rerun()


# ------------------------------
# Page 5: Meditation Timer
# ------------------------------
elif page == "🧘 Meditation Timer":
    st.markdown("<h1>🧘 Meditation Timer</h1>", unsafe_allow_html=True)
    minutes = st.number_input("Set Timer (minutes):", min_value=1, max_value=120, value=5)
    
    if st.button("Start Timer", disabled=st.session_state.timer_running):
        st.session_state.timer_running = True
        st.info("Meditation in progress...")
        timer_placeholder = st.empty()
        
        # Streamlit's simple sleep implementation for a timer
        for i in range(minutes * 60, 0, -1):
            mins, secs = divmod(i, 60)
            timer_placeholder.markdown(f"## ⏰ {mins:02d}:{secs:02d}", unsafe_allow_html=True)
            time.sleep(1)
        
        # Timer finished
        st.balloons()
        st.success("✅ Time's up! Great job!")
        st.session_state.meditation_minutes += minutes
        st.session_state.timer_running = False
        # --- FIX: Use st.rerun() ---
        st.rerun()

# ------------------------------
# Page 6: Daily Dashboard
# ------------------------------
elif page == "📊 Daily Dashboard":
    st.markdown("<h1>📊 Daily Dashboard</h1>", unsafe_allow_html=True)
    
    st.subheader("🗓️ Daily Progress Summary")
    
    col_t, col_q, col_m = st.columns(3)
    
    with col_t:
        st.subheader("📚 Topics")
        st.metric("Total Topics", len(st.session_state.topics_today), delta="/10 target")

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

    if st.session_state.meditation_minutes >= 30:
        st.success("🎯 Daily meditation goal reached!")

# ------------------------------
# Footer
# ------------------------------
st.markdown("---")
st.caption("Made with ❤️ using Streamlit + Wikipedia + WolframAlpha (optional) + Built-in Converter + Conversational Responses")

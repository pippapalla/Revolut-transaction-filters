import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime
from dotenv import load_dotenv

import requests

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://openrouter.ai/api/v1/chat/completions"  # Using DeepSeek via OpenRouter

def get_ai_response(prompt, transactions, user_query):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",  # Can also try "deepseek-coder" if you'd like
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Query: {user_query}\nTransactions:\n{transactions}"}
        ],
        "temperature": 0.2
    }

    res = requests.post(DEEPSEEK_URL, headers=headers, json=data)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError(f"DeepSeek API failed: {res.status_code} - {res.text}")


# Load environment
load_dotenv()

st.set_page_config(page_title="Smart Transaction Viewer", layout="wide")

# Load CSS
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        st.warning("⚠️ style.css not found.")

# Load logo
def get_logo_base64():
    try:
        with open("assets/revolut-logo.svg", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

# Category emoji
def get_category_emoji(category):
    icons = {
        "Groceries": "🛍️", "Subscription": "📆", "Transport": "🚇", "Bar": "🍺",
        "Restaurant": "🍽️", "Entertainment": "🎮", "Online Purchase": "💻",
        "Utilities": "💡", "Income": "💰"
    }
    return icons.get(category, "💳")

# Load transactions
@st.cache_data
def load_data():
    df = pd.read_csv("fake_transactions_student_barcelona.csv")
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Amount"] = df["Amount"].astype(float)
    return df

# Load data and styles
load_css()
df = load_data()

# --- AI Assistant Section ---
ai_mode = False  # Whether AI handled the filtering
ai_text = None   # Output from AI to show

st.subheader("🤖 AI Assistant Search")
ai_query = st.text_input("Ask me to find transactions...", placeholder="e.g., Show me my biggest expenses in April")

if ai_query:
    try:
        sample = df[["Date", "Description", "Category", "Type", "Amount"]].to_dict(orient="records")
        prompt = (
            "You are a financial assistant. The user will ask you about specific bank transactions. "
            "Each transaction has: Date, Description, Category, Type (Income/Expense), and Amount. "
            "Respond by listing only matching transactions in a markdown bullet list like:\n"
            "- 2025-03-04 | 💰 Income | Transfer from Dad: +783.33€"
        )
        ai_text = get_ai_response(prompt, sample, ai_query)
        ai_mode = True

        st.markdown("### 🔍 AI Search Result")
        st.markdown(ai_text)
    except Exception as e:
        st.error(f"AI failed: {e}")

logo = get_logo_base64()

# Top banner
st.markdown(
    f'''<div class="top-banner">
        <div class="logo-box"><img src="data:image/svg+xml;base64,{logo}" class="logo" /></div>
        <h1 class="title">Transactions</h1>
    </div>''',
    unsafe_allow_html=True
)

# Sidebar filters
st.sidebar.header("Filters")
types = st.sidebar.multiselect("Transaction Type", df["Type"].unique(), default=list(df["Type"].unique()))
categories = st.sidebar.multiselect("Category", df["Category"].unique(), default=list(df["Category"].unique()))
min_date = pd.to_datetime(df["Date"].min())
max_date = pd.to_datetime(df["Date"].max())
date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# Handle one-date or two-date cases
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date = end_date = pd.to_datetime(date_range)

min_amt, max_amt = float(df["Amount"].min()), float(df["Amount"].max())
amount_min, amount_max = st.sidebar.slider("Amount (€)", round(min_amt), round(max_amt), (round(min_amt), round(max_amt)))

# Apply filters
filtered_df = df[
    (df["Type"].isin(types)) &
    (df["Category"].isin(categories)) &
    (df["Date"] >= start_date) &
    (df["Date"] <= end_date) &
    (df["Amount"].abs() >= amount_min) &
    (df["Amount"].abs() <= amount_max)
]
   # Show filtered results
if not filtered_df.empty:
    # Group by date (most recent first)
    filtered_df = filtered_df.sort_values("Date", ascending=False)
    grouped = filtered_df.groupby(filtered_df["Date"].dt.date, sort=False)

    for date, group in grouped:
        st.markdown(f"### {date.strftime('%A, %d %B %Y')}")
        for _, row in group.iterrows():
            emoji = get_category_emoji(row["Category"])
            color = "lightgreen" if row["Amount"] > 0 else "salmon"
            st.markdown(
                f"<div class='transaction-card'><div class='transaction-info'>"
                f"<div class='transaction-label'>{emoji} {row['Description']}</div>"
                f"<div class='transaction-amount' style='color:{color}; font-weight: bold;'>"
                f"{'+' if row['Amount'] > 0 else ''}{abs(round(row['Amount'], 2))}€</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
else:
    st.info("No transactions found.")
